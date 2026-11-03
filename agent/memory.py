"""Conversation memory with a token budget.

The context window is the agent's working memory, and we saw in class that stuffing it
does not work: things in the middle get lost. ``ConversationMemory`` keeps the message
list, counts tokens, and when the budget is exceeded it asks you (``summarize``) to
compress the oldest turns into a summary that stays at the top of the conversation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    system_prompt: str
    count_tokens: Callable[[str], int]
    token_budget: int = 6000
    keep_last: int = 6  # most recent messages that are never summarised
    pin_first: bool = False  # keep the first message (the task) verbatim, never summarise it
    obs_chars: int = 1500  # tool results are cut to this length before they are summarised
    messages: list[dict] = field(default_factory=list)
    summary: str = ""

    def add(self, role: str, content: str, **extra) -> None:
        self.messages.append({"role": role, "content": content, **extra})

    def tokens(self) -> int:
        text = self.system_prompt + self.summary + "".join(m["content"] for m in self.messages)
        return self.count_tokens(text)

    def over_budget(self) -> bool:
        return self.tokens() > self.token_budget

    def render(self) -> list[dict]:
        """Messages to send to the model: system (+ summary) followed by the live messages."""
        system = self.system_prompt
        if self.summary:
            system += f"\n\nSummary of the conversation so far:\n{self.summary}"
        return [{"role": "system", "content": system}, *self.messages]

    def _shorten(self, message: dict) -> dict:
        """A copy of ``message`` that is safe to summarise: long tool results are cut."""
        content = message["content"]
        if message["role"] == "tool" and len(content) > self.obs_chars:
            return {**message, "content": content[: self.obs_chars] + " [...]"}
        return message

    def compress(self, summarize: Callable[[list[dict]], str]) -> bool:
        """Summarise the oldest messages when the conversation is over budget.

        The policy (what is summarised, when, and what is always kept):

        * **When:** only if ``over_budget()``, and only if there is something older than the
          ``keep_last`` most recent messages.
        * **Always kept:** the last ``keep_last`` messages and, if ``pin_first`` is set, the first
          message, which is the task: a summary must never be the only place where the question
          lives. The agent turns ``pin_first`` on.
        * **Cut point:** a cut never leaves a ``tool`` message at the start of what is kept,
          because a tool result without the assistant message that asked for it makes no sense.
          If the cut falls there, it moves back so the pair stays together.
        * **What the summarizer sees:** the old messages with every tool result cut to
          ``obs_chars`` characters (retrieved passages are long and they are what fills the
          budget). The live messages are not touched.
        * **Result:** the new summary is appended to the existing one, which stays in the system
          message (``render``).

        Returns True if a compression happened.
        """
        if not self.over_budget():
            return False
        head = self.messages[:1] if self.pin_first else []
        rest = self.messages[len(head) :]
        cut = len(rest) - self.keep_last
        while cut > 0 and rest[cut]["role"] == "tool":
            cut -= 1
        if cut <= 0:
            return False
        old, recent = rest[:cut], rest[cut:]
        new_summary = summarize([self._shorten(m) for m in old])
        self.summary = f"{self.summary}\n{new_summary}".strip()
        self.messages = head + recent
        return True
