"""Smart turn-taking using gpt-4.1-nano for lightweight classification."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal, cast

import textprompts
from pydantic import BaseModel
from pydantic_ai import Agent

from .protocols import TurnContext, TurnDecision


logger = logging.getLogger(__name__)

# Defaults
DEFAULT_MODEL = "gpt-4.1-nano"
DEFAULT_RECHECK_SECONDS = 5.0
DEFAULT_MAX_WAIT_TURNS = 3  # Force respond after 3 consecutive waits


class Decision(str, Enum):
    """Turn decision enum."""

    RESPOND = "RESPOND"
    WAIT = "WAIT"


class ClassifierOutput(BaseModel):
    """Structured output from the classifier."""

    decision: Literal["RESPOND", "WAIT"]
    reason: str


def _load_prompt() -> str:
    """Load the smart turn classifier prompt content."""
    prompt_path = Path(__file__).parent / "prompts" / "smart_turn_classifier.txt"
    prompt = textprompts.load_prompt(prompt_path, meta="strict")
    return prompt.prompt


@dataclass(slots=True)
class SmartTurnClassifier:
    """Smart turn-taking classifier using gpt-4.1-nano.

    Checks every few seconds. Forces RESPOND after max_wait_turns.

    Args:
        model: OpenAI model to use (default: gpt-4.1-nano)
        recheck_seconds: Seconds between rechecks (default: 5.0)
        max_wait_turns: Force respond after this many consecutive waits (default: 3)
    """

    model: str = DEFAULT_MODEL
    recheck_seconds: float = DEFAULT_RECHECK_SECONDS
    max_wait_turns: int = DEFAULT_MAX_WAIT_TURNS

    _agent: Agent[None, ClassifierOutput] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Initialize the classifier agent."""
        prompt_content = _load_prompt()
        self._agent = cast(
            Agent[None, ClassifierOutput],
            Agent(
                f"openai:{self.model}",
                output_type=ClassifierOutput,
                system_prompt=prompt_content,
            ),
        )

    async def should_respond(self, context: TurnContext) -> TurnDecision:
        """Decide whether to respond now or wait.

        Forces RESPOND after max_wait_turns to prevent infinite loops.
        """
        # Safety: force respond after max wait turns
        if context.consecutive_wait_count >= self.max_wait_turns:
            logger.info(
                "Max wait turns (%d) reached, forcing respond",
                self.max_wait_turns,
            )
            return TurnDecision(
                should_respond=True,
                reason=f"Max wait turns ({self.max_wait_turns}) reached",
            )

        if self._agent is None:
            return TurnDecision(should_respond=True, reason="No classifier available")

        prompt = self._build_prompt(context)

        try:
            result = await self._agent.run(prompt)
            output = result.output if hasattr(result, "output") else result.data

            should_respond = output.decision == "RESPOND"

            logger.debug(
                "Smart turn classifier: decision=%s, reason=%s",
                output.decision,
                output.reason,
            )

            return TurnDecision(
                should_respond=should_respond,
                recheck_in_seconds=self.recheck_seconds,
                reason=output.reason,
            )
        except Exception as e:
            logger.warning("Smart turn classifier error: %s", e)
            return TurnDecision(should_respond=True, reason=f"Classifier error: {e}")

    def _build_prompt(self, context: TurnContext) -> str:
        """Build prompt - focus on the assistant message ending."""
        parts: list[str] = []

        # The assistant message - this is what matters
        parts.append("Assistant message:")
        if context.assistant_messages:
            msg = context.assistant_messages[-1]
            parts.append(f'"{msg}"')
        else:
            parts.append('"(no message yet)"')
        parts.append("")

        # Wait context
        if context.consecutive_wait_count > 0:
            parts.append(
                f"(Already waited {context.consecutive_wait_count}x, "
                f"max {self.max_wait_turns}x)"
            )
            parts.append("")

        parts.append("Does this END with a wait request? Output RESPOND or WAIT.")

        return "\n".join(parts)
