from __future__ import annotations

"""Protocols shared by simulator components."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence


@dataclass(slots=True)
class UserRequest:
    conversation_id: str
    turn_id: str | None
    text: str | None
    data: Sequence[dict[str, Any]]


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
