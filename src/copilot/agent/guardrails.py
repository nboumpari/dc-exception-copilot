"""Deterministic guardrails around the agent - plain code, no LLM.

Input (before the agent runs):
  - requests for credentials or for the system prompt are BLOCKED with a fixed reply;
    the LLM never sees them, so it cannot be talked into answering.
  - likely prompt-injection phrasing ("ignore your rules") is FLAGGED and logged but still
    answered: the agent's own rules and the code-based compliance tools still apply, and
    blocking would also refuse legitimate questions that merely quote such text.
Tool results: injection phrasing inside data or documents (indirect injection) is flagged.
Actions: `propose_action` refuses personal free-mail recipients (gmail.com, ...) before a
  human is even asked - company data only goes to business partners' own addresses.
Output (after the agent answers):
  - claiming an email/ticket was sent when no approval happened -> one forced rewrite.
  - granting a hazmat/safety exception (only the EHS coordinator may) -> one forced rewrite.
  - anything that looks like an API key is redacted before the answer leaves.

Patterns are intentionally narrow: a false alarm on a real warehouse question is costly,
and the red-team evaluation (data/eval/redteam.yaml) measures what still gets through.
"""

import re
from dataclasses import dataclass, field

BLOCKED_REPLY = {
    "secrets": ("I can't help with credentials, API keys or configuration secrets. If you "
                "need access to a system, ask your IT administrator."),
    "system_prompt": ("I can't share my internal instructions or configuration. I can help "
                      "with shipments, receipts, hazmat compliance, procedures and "
                      "regulations at the DC - what do you need?"),
}

# "credentials"/"password" alone are too broad (a driver's hazmat credentials are a real
# topic), so they only count next to a system word
_SECRETS_REQUEST = re.compile(
    r"\b(api[ _-]?keys?|secret keys?|access tokens?)\b|\.env\b"
    r"|\b(your|admin|login|database|server|openai|langsmith|gemini)\s+(passwords?|credentials?)\b",
    re.IGNORECASE)
_SYSTEM_PROMPT_REQUEST = re.compile(
    r"\b(system|initial|hidden|developer)\s+(prompt|instructions|message)"
    r"|\b(repeat|print|show|reveal|output|display)\b[^.?!]{0,40}\byour\s+(instructions|prompt|rules)\b"
    r"|\btool\s+definitions\b", re.IGNORECASE)
_INJECTION = re.compile(
    r"\b(ignore|disregard|forget|override|bypass)\b[^.?!\n]{0,40}"
    r"\b(rules|instructions|guidelines|policies|policy|prompt|safety)\b"
    r"|\b(system override|maintenance mode|developer mode|jailbreak|you are now)\b"
    r"|\bpretend (you are|to be)\b", re.IGNORECASE)

# "the email was sent" - unless negated or conditional ("not sent", "will be sent once ...")
_SENT_CLAIM = re.compile(
    r"\b(email|e-mail|message|ticket|notice|notification)\b[^.\n]{0,40}\b(has been|was|been|is)\s+sent\b"
    r"|\bI(?:'ve| have)?\s+(sent|emailed|notified)\b", re.IGNORECASE)
_NOT_SENT = re.compile(r"\b(not|n't|never|once|after|until|when|if|will|would|pending|awaiting|draft)\b", re.IGNORECASE)
_EXCEPTION_GRANT = re.compile(
    r"\b(exception|waiver|deviation)\b[^.\n]{0,30}\b(is|has been|was)\s+(approved|granted)\b"
    r"|\bI\s+(hereby\s+)?(approve|grant|authori[sz]e)\b", re.IGNORECASE)
_KEY = re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|lsv2_[A-Za-z0-9_]{16,}|AIza[0-9A-Za-z_-]{30,})")


@dataclass
class InputCheck:
    blocked: str | None = None  # key of BLOCKED_REPLY, or None
    flags: list[str] = field(default_factory=list)

    @property
    def reply(self) -> str | None:
        return BLOCKED_REPLY[self.blocked] if self.blocked else None


def check_input(question: str) -> InputCheck:
    if _SECRETS_REQUEST.search(question):
        return InputCheck("secrets", ["blocked:secrets"])
    if _SYSTEM_PROMPT_REQUEST.search(question):
        return InputCheck("system_prompt", ["blocked:system_prompt"])
    return InputCheck(flags=["injection_suspected"] if _INJECTION.search(question) else [])


# consumer mailbox providers: never a business partner's official address
FREE_MAIL_DOMAINS = frozenset([
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com",
    "msn.com", "icloud.com", "me.com", "aol.com", "proton.me", "protonmail.com", "gmx.com",
    "gmx.net", "mail.com", "yandex.com", "zoho.com"])
_EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")


def blocked_recipient(recipient: str) -> str | None:
    """The personal email address in `recipient`, if any (such recipients are refused)."""
    for m in _EMAIL.finditer(recipient):
        if m.group(1).lower() in FREE_MAIL_DOMAINS:
            return m.group(0)
    return None


def injection_in_tool_output(tool_texts: list[str]) -> bool:
    return any(_INJECTION.search(t) for t in tool_texts)


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+|\n+", text)


def claims_sent(answer: str) -> bool:
    return any(_SENT_CLAIM.search(s) and not _NOT_SENT.search(s) for s in _sentences(answer))


def grants_exception(answer: str) -> bool:
    return any(_EXCEPTION_GRANT.search(s) and not re.search(r"\b(not|n't|cannot|only)\b", s, re.IGNORECASE)
               for s in _sentences(answer))


def output_problems(answer: str, action_sent: bool) -> tuple[list[str], list[str]]:
    """(flags, rewrite instructions) for an answer. `action_sent` = a propose_action call
    in this turn returned status 'sent' (a human approved it)."""
    flags, notes = [], []
    if claims_sent(answer) and not action_sent:
        flags.append("claimed_sent")
        notes.append("Your answer says a message was sent, but nothing was approved or sent. "
                     "Say it was NOT sent; to send something, call propose_action.")
    if grants_exception(answer):
        flags.append("granted_exception")
        notes.append("Your answer grants or approves an exception. You cannot: only the EHS "
                     "coordinator can approve hazmat or safety exceptions. Say so instead.")
    return flags, notes


def redact_secrets(text: str) -> tuple[str, bool]:
    redacted = _KEY.sub("[redacted]", text)
    return redacted, redacted != text
