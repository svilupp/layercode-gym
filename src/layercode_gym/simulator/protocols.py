from __future__ import annotations

"""Protocols shared by simulator components."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

from pydantic import BaseModel


# Wait validation constants
MIN_WAIT_SECONDS = 2
MAX_WAIT_SECONDS = 300


class RespondToAssistant(BaseModel):
    """Respond to the assistant with a message.

    Use this when you want to reply to the assistant - whether answering a question,
    providing information, making a request, or continuing the conversation.

    Example:
        RespondToAssistant(message="Yes, I'd like to proceed with the order.")
    """

    message: str
    """The message to send to the assistant."""


class WaitForAssistant(BaseModel):
    """Wait for the assistant to finish before responding.

    Use this when the assistant is not done answering - for example, when they say
    "please wait", "one moment", "processing...", or mention a time estimate.
    This yields control back to the system, which will call you again when the
    assistant sends more content.

    Example:
        WaitForAssistant(wait_seconds=10, reason="Assistant said processing takes ~8 seconds")
    """

    wait_seconds: float
    """How long to wait before checking again (2-300 seconds).
    If the assistant gives a time estimate, add ~20% buffer.
    If no estimate given, use 10-30 seconds."""

    reason: str | None = None
    """Optional reason for waiting (for debugging/logging)."""


# Type alias for agent outputs - all agents must return one of these
AgentOutput = RespondToAssistant | WaitForAssistant


@dataclass(slots=True)
class WaitContext:
    """Context about waiting during the current assistant turn.

    Tracks how many times we've waited and for how long, allowing the LLM
    to understand that time has passed and make decisions based on the
    full accumulated message rather than fragments.
    """

    wait_count: int = 0
    """Number of times we've waited during this turn."""

    total_wait_seconds: float = 0.0
    """Total seconds waited during this turn."""

    last_text_len: int = 0
    """Text length at last wait (to detect if new content arrived)."""

    def record_wait(self, wait_seconds: float, current_text_len: int) -> None:
        """Record a wait event."""
        self.wait_count += 1
        self.total_wait_seconds += wait_seconds
        self.last_text_len = current_text_len

    def has_new_content(self, current_text_len: int) -> bool:
        """Check if new content arrived since last wait."""
        return current_text_len > self.last_text_len

    def reset(self) -> None:
        """Reset context for new turn."""
        self.wait_count = 0
        self.total_wait_seconds = 0.0
        self.last_text_len = 0


@dataclass(slots=True)
class UserRequest:
    """Request passed to the user simulator for generating a response.

    Attributes:
        conversation_id: Unique conversation identifier
        turn_id: Current turn identifier
        text: Full accumulated text from assistant (all content since last user response)
        data: All accumulated response.data payloads
        data_text: Processed data as human-readable text for AI context
        wait_context: Context about waits during this turn (None if no waits yet)
    """

    conversation_id: str
    turn_id: str | None
    text: str | None
    data: Sequence[dict[str, Any]]
    data_text: str | None = field(default=None)
    wait_context: WaitContext | None = field(default=None)


@dataclass(slots=True)
class UserResponse:
    """Response from the user simulator.

    Attributes:
        text: Text response (mutually exclusive with audio_path for sending)
        audio_path: Path to audio file
        data: Data payloads to send
        wait_seconds: If set, skip this turn and wait for specified duration.
                     Used when assistant needs time for long-running tasks.
                     Valid range: 2-300 seconds.
    """

    text: str | None
    audio_path: Path | None
    data: Sequence[dict[str, Any]]
    wait_seconds: float | None = None

    @property
    def has_payload(self) -> bool:
        """True if this response has content to send."""
        return self.text is not None or self.audio_path is not None or bool(self.data)

    @property
    def is_wait(self) -> bool:
        """True if this is a wait response (skip turn and wait)."""
        return self.wait_seconds is not None and self.wait_seconds > 0


class SimulatorHook(Protocol):
    async def __call__(
        self, request: UserRequest, proposed: UserResponse | None
    ) -> UserResponse | None:  # noqa: D401
        """Inspect and optionally override the user response."""


class UserSimulatorProtocol(Protocol):
    async def get_response(self, request: UserRequest) -> UserResponse | None: ...


class TTSEngineProtocol(Protocol):
    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        instructions: str | None = None,
        conversation_id: str | None = None,
        turn_id: str | None = None,
    ) -> Path: ...


class ResponseDataProcessor(Protocol):
    """Protocol for processing response.data events into text for AI context.

    When the voice agent emits response.data events (e.g., tool calls displaying
    products, orders, confirmations), this processor converts the raw data into
    human-readable text that the AI user simulator can "see" and react to.

    Example:
        def my_processor(data: dict[str, Any]) -> str:
            if data.get("tool") == "show_products":
                products = data["products"]
                return f"[DISPLAYED: {len(products)} products shown]"
            return ""
    """

    def __call__(self, data: dict[str, Any]) -> str:
        """Convert a response.data payload to a text description.

        Args:
            data: The raw data dictionary from response.data event

        Returns:
            Human-readable text description of the data.
            Return empty string to skip/ignore this data event.
        """
        ...
