from __future__ import annotations

"""Protocols shared by simulator components."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence


@dataclass(slots=True)
class UserRequest:
    """Request passed to the user simulator for generating a response.

    Attributes:
        conversation_id: Unique conversation identifier
        turn_id: Current turn identifier
        text: Transcribed text from assistant's last response
        data: Raw response.data payloads from the current turn
        data_text: Processed data as human-readable text for AI context
    """

    conversation_id: str
    turn_id: str | None
    text: str | None
    data: Sequence[dict[str, Any]]
    data_text: str | None = field(default=None)


@dataclass(slots=True)
class UserResponse:
    text: str | None
    audio_path: Path | None
    data: Sequence[dict[str, Any]]

    @property
    def has_payload(self) -> bool:
        return self.text is not None or self.audio_path is not None or bool(self.data)


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
