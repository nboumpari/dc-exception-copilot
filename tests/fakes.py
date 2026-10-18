"""Shared test doubles: a scripted chat model so agent and API tests never call an LLM."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class ScriptedModel(BaseChatModel):
    """Replays prepared AIMessages in order and records what it was sent."""

    script: list
    seen: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        item = self.script.pop(0)
        if isinstance(item, Exception):  # script an LLM failure
            raise item
        return ChatResult(generations=[ChatGeneration(message=item)])


def call(name: str, args: dict, cid: str = "c1") -> AIMessage:
    """An AI message that requests one tool call."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])
