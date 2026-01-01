"""Protocols for smart turn-taking decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class TurnContext:
    """Context for turn decision.

    Attributes:
        assistant_messages: Last 2-3 messages from the assistant
        last_user_text: Most recent user message text
        seconds_since_last_audio: Time since last audio from assistant
        conversation_turn_count: Number of turns completed so far
        consecutive_wait_count: Number of consecutive waits in this turn
        total_wait_seconds: Total seconds waited in this turn
    """

    assistant_messages: tuple[str, ...]
    last_user_text: str | None
    seconds_since_last_audio: float
    conversation_turn_count: int
    consecutive_wait_count: int = 0
    total_wait_seconds: float = 0.0


@dataclass(slots=True, frozen=True)
class TurnDecision:
    """Decision from smart turn-taking classifier.

    Attributes:
        should_respond: If True, user should respond now. If False, wait and recheck.
        recheck_in_seconds: How long to wait before re-checking (default: 5 seconds)
        reason: Optional explanation for the decision (for logging)
    """

    should_respond: bool
    recheck_in_seconds: float = 5.0
    reason: str | None = None


class SmartTurnClassifier(Protocol):
    """Protocol for smart turn-taking classifier.

    Implementations decide whether the user should respond now or wait
    for the assistant to complete a long-running task.
    """

    async def should_respond(self, context: TurnContext) -> TurnDecision:
        """Decide whether to respond now or wait and re-check later.

        Args:
            context: Current conversation context including recent messages
                and timing information

        Returns:
            TurnDecision with should_respond flag and recheck timing
        """
        ...
