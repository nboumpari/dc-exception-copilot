"""Chat with the copilot in the terminal.

Usage:
    uv run python -m copilot.agent.cli                      # interactive session
    uv run python -m copilot.agent.cli "Is SHP-01209 OK?"   # one question

Follow-up questions keep the conversation context. When the agent proposes an email or
ticket, you are asked to approve, reject or edit it before anything is "sent".
"""

import argparse
import sys
import warnings

from copilot.agent.graph import AgentResult, Copilot

warnings.filterwarnings("ignore")


def _show(r: AgentResult, verbose: bool) -> None:
    if verbose and r.tool_calls:
        print("\n  tools: " + ", ".join(f"{c['name']}({_short(c['args'])})" for c in r.tool_calls))
    if r.answer:
        print(f"\n{r.answer}\n")
    if r.unverified_citations:
        print(f"  ! citations not found in tool results: {r.unverified_citations}\n")


def _short(args: dict) -> str:
    return ", ".join(f"{k}={str(v)[:40]!r}" for k, v in args.items())


def _approve(cp: Copilot, r: AgentResult, verbose: bool) -> AgentResult:
    while r.pending_action:
        p = r.pending_action
        print("\n=== APPROVAL NEEDED ===")
        print(f"{p['action_type'].upper()} to {p['recipient']}\nSubject: {p['subject']}\n")
        print(p["body"])
        print(f"\nReason: {p['reason']}")
        choice = input("\nApprove? [y]es / [n]o / [e]dit body: ").strip().lower()
        if choice.startswith("e"):
            print("Type the new body, then an empty line:")
            lines = iter(input, "")
            r = cp.resume(r.thread_id, approved=True, edited_body="\n".join(lines))
        elif choice.startswith("y"):
            r = cp.resume(r.thread_id, approved=True)
        else:
            r = cp.resume(r.thread_id, approved=False, comment=input("Reason (optional): "))
        _show(r, verbose)
    return r


def main() -> None:
    parser = argparse.ArgumentParser(description="DC Exception Copilot")
    parser.add_argument("question", nargs="*", help="ask one question and exit")
    parser.add_argument("-q", "--quiet", action="store_true", help="hide tool calls")
    args = parser.parse_args()
    verbose = not args.quiet
    # Windows consoles default to a legacy code page that cannot print "§" or "—"
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    cp = Copilot()
    if args.question:
        r = cp.ask(" ".join(args.question))
        _show(r, verbose)
        _approve(cp, r, verbose)
        return

    print("DC Exception Copilot - ask about shipments, hazmat, procedures. Ctrl+C or 'exit' to quit.")
    thread_id = None
    while True:
        try:
            question = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if question.lower() in {"exit", "quit"}:
            return
        if not question:
            continue
        r = cp.ask(question, thread_id=thread_id)
        thread_id = r.thread_id
        _show(r, verbose)
        _approve(cp, r, verbose)


if __name__ == "__main__":
    main()
