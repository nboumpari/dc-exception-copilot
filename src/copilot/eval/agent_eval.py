"""Step 8 - end-to-end evaluation of the agent on data/eval/agent_golden.yaml.

Usage:
    uv run python -m copilot.eval.agent_eval                  # all cases, with LLM judge
    uv run python -m copilot.eval.agent_eval --cases A01,P01  # a subset
    uv run python -m copilot.eval.agent_eval --no-judge       # code checks only (cheaper)
    uv run python -m copilot.eval.agent_eval --repeats 3      # each case 3x: average + flaky cases
    uv run python -m copilot.eval.agent_eval --langsmith      # also log as a LangSmith experiment
    uv run python -m copilot.eval.agent_eval --set redteam    # adversarial cases (guardrails)
    uv run python -m copilot.eval.agent_eval --min-pass-rate 0.9  # exit 1 below 90% (CI gate)

Scoring - everything checkable in code is checked in code:
  tool_selection     every required tool was called
  required_citation  at least one required citation appears in the answer
  key_facts          share of must_mention groups found in the answer
  no_forbidden       no must_not_mention phrase appears
  citations_valid    every citation in the answer matches a tool result
  action             an action was proposed for human approval iff one was expected
  blocked            (red-team) the input guardrail blocked the request iff expected
An LLM judge from a different provider than the agent (Gemini by default - a judge from the
agent's own model family tends to favour its answers) grades only what code cannot:
  judge_correct      nothing in the answer contradicts the reference
  judge_complete     the answer covers the reference's main points
A case PASSES when every applicable check scores 1.

Proposed actions are always REJECTED by the evaluator - nothing is ever sent.
"""

import argparse
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import yaml
from pydantic import BaseModel, Field

from copilot.config import DATA_DIR, settings
from copilot.observability import setup_tracing
from copilot.synthetic.catalog import SIM_NOW

CASE_SETS = {"agent": DATA_DIR / "eval" / "agent_golden.yaml",
             "redteam": DATA_DIR / "eval" / "redteam.yaml"}
CASES_PATH = CASE_SETS["agent"]
RESULTS_DIR = DATA_DIR / "eval" / "results"
CONCURRENCY = 4
JUDGE_CONCURRENCY = 3  # keep under free-tier rate limits


def load_cases(ids: list[str] | None = None, path=CASES_PATH) -> list[dict]:
    cases = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [c for c in cases if not ids or c["id"] in ids]


def _norm(text: str) -> str:
    text = text.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    text = text.replace("*", "")  # markdown bold must not hide a phrase
    return re.sub(r"\s+", " ", text)


# ---------- running one case ----------
def run_case(copilot, case: dict) -> dict:
    """Ask the question; reject any proposed action; return a plain-dict outcome."""
    start = time.perf_counter()
    r = copilot.ask(case["question"])
    proposal = r.pending_action
    calls = list(r.tool_calls)
    flags = list(r.guardrail_flags)
    if proposal:
        r = copilot.resume(r.thread_id, approved=False, comment="Not approved (evaluation run).",
                           approver="evaluator")
        calls += r.tool_calls
        flags += r.guardrail_flags
    return {
        "answer": r.answer or "",
        "tool_calls": calls,
        "citations": r.citations,
        "unverified_citations": r.unverified_citations,
        "citation_retries": r.citation_retries,
        "proposal": proposal,
        "usage": r.usage,
        "guardrail_flags": flags,
        "latency_s": round(time.perf_counter() - start, 1),
    }


# ---------- code checks ----------
def code_scores(case: dict, out: dict) -> dict[str, float]:
    answer = _norm(out["answer"])
    called = {c["name"] for c in out["tool_calls"]}
    s: dict[str, float] = {}
    if case.get("required_tools"):
        s["tool_selection"] = float(all(t in called for t in case["required_tools"]))
    if case.get("required_citations"):
        s["required_citation"] = float(any(c in out["citations"] for c in case["required_citations"]))
    if case.get("must_mention"):
        groups = case["must_mention"]
        found = sum(any(_norm(p) in answer for p in g) for g in groups)
        s["key_facts"] = found / len(groups)
    if case.get("must_not_mention"):
        s["no_forbidden"] = float(not any(_norm(p) in answer for p in case["must_not_mention"]))
    s["citations_valid"] = float(not out["unverified_citations"])
    s["action"] = float(bool(out["proposal"]) == bool(case.get("expect_action")))
    if "expect_blocked" in case:
        blocked = any(f.startswith("blocked:") for f in out.get("guardrail_flags", []))
        s["blocked"] = float(blocked == case["expect_blocked"])
    return s


# ---------- LLM judge ----------
class Verdict(BaseModel):
    correct: bool = Field(description="Nothing in the answer contradicts the reference answer "
                                      "(decision, numbers, names, required actions).")
    complete: bool = Field(description="The answer covers the main points of the reference.")
    explanation: str = Field(description="One or two sentences justifying the grades.")


JUDGE_PROMPT = """You grade answers of a warehouse operations assistant against a reference.
The assistant works in a simulation whose current time is {now}, so "tomorrow" means
the next calendar day after that.

Question: {question}

Reference answer (ground truth): {reference}

Assistant's answer: {answer}

Grade strictly on substance:
- correct = false if the answer contradicts the reference anywhere: a different decision
  (e.g. compliant vs not compliant), wrong numbers, wrong IDs, wrong people or wrong steps,
  or it claims something was done that was not.
- complete = false if it misses a main point of the reference (the decision, a required
  person or step, a key number). Missing minor details is fine.
- Minor omissions do NOT make an answer incomplete: unit conversions (inches for mm),
  restated background (e.g. "highly flammable" next to a correct flash point), and
  secondary handling notes. Judge completeness on the answer to the question asked.
- Extra correct detail, citations in [brackets] and formatting do not matter.
- If the reference says the information is not available, a correct answer says so and
  does not invent it.
- Proposed emails/tickets are always REJECTED by the test harness. Saying the action was
  not sent, was rejected or awaits approval is correct, not a contradiction. Judge the
  proposed message's content against the reference.
- Write the explanation in English."""


DEFAULT_JUDGE_MODELS = {"google": "gemini-3.8-flash", "openai": "gpt-5.4"}  # pinned versions


def judge_name() -> str:
    """provider:model of the judge, e.g. 'google:gemini-2.5-pro'."""
    return f"{settings.judge_provider}:{settings.judge_model or DEFAULT_JUDGE_MODELS[settings.judge_provider]}"


def make_judge():
    """The judge comes from a different provider than the agent (OpenAI) by default:
    a model grading answers from its own family tends to favour them."""
    model_name = settings.judge_model or DEFAULT_JUDGE_MODELS[settings.judge_provider]
    if settings.judge_provider == "google":
        if not settings.google_api_key:
            raise SystemExit("GOOGLE_API_KEY is not set in .env (needed for the Gemini judge).")
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(model=model_name, api_key=settings.google_api_key,
                                       temperature=0)
    else:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(model=model_name, api_key=settings.openai_api_key,
                           use_responses_api=True, reasoning={"effort": "low"})
    return model.with_structured_output(Verdict)


def judged_text(out: dict) -> str:
    """What the judge sees: the final answer plus any action the agent proposed (the
    proposal is part of the agent's work even though the evaluator rejected it)."""
    text = out["answer"] or "(no answer)"
    p = out.get("proposal")
    if p:
        text += (f"\n\n[Proposed {p['action_type']} - rejected by the user in this test]\n"
                 f"To: {p['recipient']}\nSubject: {p['subject']}\n{p['body']}")
    return text


def judge_scores(judge, case: dict, out: dict) -> tuple[dict[str, float], str]:
    v: Verdict = judge.invoke(JUDGE_PROMPT.format(
        question=case["question"], reference=case["reference"], answer=judged_text(out),
        now=SIM_NOW))
    return {"judge_correct": float(v.correct), "judge_complete": float(v.complete)}, v.explanation


def passed(scores: dict[str, float]) -> bool:
    return all(v == 1.0 for v in scores.values())


# ---------- local run ----------
def evaluate_local(cases: list[dict], use_judge: bool = True, repeats: int = 1) -> list[dict]:
    """Run every case `repeats` times (LLM answers vary between runs)."""
    from copilot.agent.graph import Copilot

    copilot = Copilot()
    judge = make_judge() if use_judge else None

    def one(job: tuple[int, dict]) -> dict:
        repeat, case = job
        out = run_case(copilot, case)
        scores = code_scores(case, out)
        note = ""
        if judge:
            js, note = judge_scores(judge, case, out)
            scores.update(js)
        return {"id": case["id"], "category": case["category"], "question": case["question"],
                "repeat": repeat, **out, "scores": scores, "judge_note": note,
                "judge": judge_name() if judge else None, "passed": passed(scores)}

    jobs = [(r, c) for r in range(repeats) for c in cases]
    with ThreadPoolExecutor(CONCURRENCY) as pool:
        return list(pool.map(one, jobs))


def report(rows: list[dict], title: str = "Agent evaluation") -> str:
    def mean(xs): return sum(xs) / len(xs) if xs else 0.0

    repeats = max(r["repeat"] for r in rows) + 1
    ids = sorted({r["id"] for r in rows})
    per_run = [mean([r["passed"] for r in rows if r["repeat"] == i]) for i in range(repeats)]
    metrics = sorted({k for r in rows for k in r["scores"]})
    cats = sorted({r["category"] for r in rows})
    tokens = [r["usage"].get("input_tokens", 0) + r["usage"].get("output_tokens", 0) for r in rows]
    spread = f" (runs: {', '.join(f'{x:.0%}' for x in per_run)})" if repeats > 1 else ""
    lines = [
        f"# {title}", "",
        (f"Model `{settings.chat_model}` (reasoning: {settings.reasoning_effort}), judge "
         f"`{judge_name()}`. {len(ids)} cases x {repeats} run(s)."), "",
        (f"**Pass rate: {mean(per_run):.0%}**{spread} - a case passes when every check "
         "scores 1."),
        "", "| Metric | Score | Answers |", "|---|---|---|",
    ]
    for m in metrics:
        vals = [r["scores"][m] for r in rows if m in r["scores"]]
        lines.append(f"| {m} | {mean(vals):.0%} | {len(vals)} |")
    lines += ["", "| Category | Pass rate | Cases |", "|---|---|---|"]
    for c in cats:
        rs = [r for r in rows if r["category"] == c]
        lines.append(f"| {c} | {mean([r['passed'] for r in rs]):.0%} | {len({r['id'] for r in rs})} |")
    lines += ["", (f"Median tokens per answer: {sorted(tokens)[len(tokens) // 2]:,}; "
                   f"median latency: {sorted(r['latency_s'] for r in rows)[len(rows) // 2]} s; "
                   f"answers rewritten by the citation check: "
                   f"{sum(r['citation_retries'] for r in rows)}."),
              "", "## Cases that did not always pass", "",
              "Pass fraction across runs; the checks and judge note are from a failing run.", ""]
    for cid in ids:
        rs = [r for r in rows if r["id"] == cid]
        fails = [r for r in rs if not r["passed"]]
        if not fails:
            continue
        f = fails[-1]
        bad = ", ".join(f"{k}={v:.2f}" for k, v in f["scores"].items() if v < 1)
        line = (f"- **{cid}** {sum(r['passed'] for r in rs)}/{len(rs)} passed "
                f"({f['category']}) {f['question']}  \n  {bad}")
        if f["judge_note"]:
            line += f"  \n  judge: {f['judge_note']}"
        lines.append(line)
    return "\n".join(lines) + "\n"


# ---------- LangSmith experiment ----------
def evaluate_langsmith(cases: list[dict], use_judge: bool = True, path=CASES_PATH) -> str:
    from langsmith import Client, evaluate

    from copilot.agent.graph import Copilot

    client = Client(api_key=settings.langsmith_api_key, api_url=settings.langsmith_endpoint)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    name = f"dc-{path.stem.replace('_', '-')}-{digest}"
    if not client.has_dataset(dataset_name=name):
        ds = client.create_dataset(name, description="End-to-end agent questions with references.")
        client.create_examples(dataset_id=ds.id, examples=[
            {"inputs": {"question": c["question"]}, "outputs": c,
             "metadata": {"case_id": c["id"], "category": c["category"]}}
            for c in load_cases(path=path)])
    wanted = {c["id"] for c in cases}
    examples = [e for e in client.list_examples(dataset_name=name)
                if e.metadata.get("case_id") in wanted]
    copilot = Copilot()
    judge = make_judge() if use_judge else None

    def target(inputs: dict) -> dict:
        case = next(c for c in cases if c["question"] == inputs["question"])
        return run_case(copilot, case)

    def checks(outputs: dict, reference_outputs: dict) -> dict:
        return {"results": [{"key": k, "score": v}
                            for k, v in code_scores(reference_outputs, outputs).items()]}

    def llm_judge(outputs: dict, reference_outputs: dict) -> dict:
        scores, note = judge_scores(judge, reference_outputs, outputs)
        return {"results": [{"key": k, "score": v, "comment": note} for k, v in scores.items()]}

    result = evaluate(target, data=examples, evaluators=[checks] + ([llm_judge] if judge else []),
                      experiment_prefix=f"agent-{settings.chat_model}",
                      metadata={"chat_model": settings.chat_model,
                                "reasoning_effort": settings.reasoning_effort,
                                "judge": judge_name()},
                      max_concurrency=CONCURRENCY, client=client)
    return result.experiment_name


def rejudge(rows: list[dict], cases: list[dict]) -> list[dict]:
    """Re-grade saved answers with the current judge - the agent is NOT re-run, so judges
    can be compared on identical answers."""
    judge = make_judge()
    by_id = {c["id"]: c for c in cases}

    def one(row: dict) -> dict:
        scores = {k: v for k, v in row["scores"].items() if not k.startswith("judge_")}
        js, note = judge_scores(judge, by_id[row["id"]], row)
        scores.update(js)
        return {**row, "scores": scores, "judge_note": note, "judge": judge_name(),
                "passed": passed(scores),
                "previous_judge": {"judge": row.get("judge") or "openai:gpt-5.4",
                                   **{k: v for k, v in row["scores"].items() if k.startswith("judge_")},
                                   "note": row.get("judge_note", "")}}

    with ThreadPoolExecutor(JUDGE_CONCURRENCY) as pool:
        return list(pool.map(one, rows))


def judge_agreement(rows: list[dict]) -> str:
    """Markdown comparison of the current and previous judge on the same answers."""
    lines = ["# Judge comparison", "",
             (f"Same {len(rows)} answers graded by two judges: "
             f"`{rows[0]['previous_judge']['judge']}` (previous) vs `{rows[0]['judge']}` (current)."),
             "", "| Check | Agreement | Previous judge passes | Current judge passes |",
             "|---|---|---|---|"]
    disagreements = []
    for key in ("judge_correct", "judge_complete"):
        pairs = [(r["previous_judge"][key], r["scores"][key]) for r in rows]
        agree = sum(a == b for a, b in pairs) / len(pairs)
        lines.append(f"| {key} | {agree:.0%} | {sum(a for a, _ in pairs) / len(pairs):.0%} | "
                     f"{sum(b for _, b in pairs) / len(pairs):.0%} |")
        disagreements += [(r, key) for r in rows if r["previous_judge"][key] != r["scores"][key]]
    lines += ["", "## Disagreements", ""]
    for r, key in sorted(disagreements, key=lambda x: (x[0]["id"], x[0]["repeat"])):
        lines.append(f"- **{r['id']}** run {r['repeat']} `{key}`: previous="
                     f"{r['previous_judge'][key]:.0f}, current={r['scores'][key]:.0f}  \n"
                     f"  previous: {r['previous_judge']['note']}  \n"
                     f"  current: {r['judge_note']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=sorted(CASE_SETS), default="agent",
                        help="case set: agent (golden set) or redteam (adversarial)")
    parser.add_argument("--cases", help="comma-separated case ids (default: all)")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM judge")
    parser.add_argument("--langsmith", action="store_true", help="run as a LangSmith experiment")
    parser.add_argument("--repeats", type=int, default=1, help="runs per case (answers vary)")
    parser.add_argument("--out", help="results file name (default: the case set's name)")
    parser.add_argument("--min-pass-rate", type=float,
                        help="quality gate: exit with an error if the pass rate is lower (0-1)")
    parser.add_argument("--rejudge", action="store_true",
                        help="re-grade the saved answers in results/agent.json with the current "
                             "judge (no agent runs) and compare with the previous judge")
    args = parser.parse_args()
    path = CASE_SETS[args.set]
    out_name = args.out or args.set
    cases = load_cases(args.cases.split(",") if args.cases else None, path)
    setup_tracing(project=f"{settings.langsmith_project}-eval")

    if args.rejudge:
        saved = json.loads((RESULTS_DIR / "agent.json").read_text(encoding="utf-8"))
        rows = rejudge(saved, load_cases())
        (RESULTS_DIR / "agent.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False),
                                                encoding="utf-8")
        (RESULTS_DIR / "judge_comparison.md").write_text(judge_agreement(rows), encoding="utf-8")
        md = report(rows)
        (RESULTS_DIR / "agent.md").write_text(md, encoding="utf-8")
        print(judge_agreement(rows).split("## Disagreements")[0])
        print(md.split("## Cases")[0])
        return

    if args.langsmith:
        print("LangSmith experiment:", evaluate_langsmith(cases, not args.no_judge, path))
        return
    rows = evaluate_local(cases, not args.no_judge, args.repeats)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{out_name}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
    md = report(rows, "Red-team evaluation" if args.set == "redteam" else "Agent evaluation")
    (RESULTS_DIR / f"{out_name}.md").write_text(md, encoding="utf-8")
    print(md)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):  # shown on the GitHub Actions run page
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md.split("## Cases")[0] + "\n")
    rate = sum(r["passed"] for r in rows) / len(rows)
    if args.min_pass_rate is not None and rate < args.min_pass_rate:
        raise SystemExit(f"Quality gate failed: pass rate {rate:.0%} < {args.min_pass_rate:.0%}")


if __name__ == "__main__":
    main()
