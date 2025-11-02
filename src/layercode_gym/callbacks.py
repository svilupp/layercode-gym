from __future__ import annotations

"""Callback protocols and simple implementations."""

from dataclasses import dataclass
from typing import Protocol

from .models.conversation import ConversationLog, ConversationTurn


class TurnCallback(Protocol):
    async def __call__(
        self, turn: ConversationTurn, conversation: ConversationLog
    ) -> None: ...


class ConversationCallback(Protocol):
    async def __call__(self, conversation: ConversationLog) -> None: ...


class _LoggingLike(Protocol):
    def __call__(self, message: str, *args: object) -> object: ...


@dataclass(slots=True)
class LoggingTurnCallback:
    logger_call: _LoggingLike

    async def __call__(
        self, turn: ConversationTurn, conversation: ConversationLog
    ) -> None:
        self.logger_call(
            "Completed turn %s with conversation %s",
            len(conversation.turns),
            conversation.conversation_id,
        )


@dataclass(slots=True)
class NoOpCallback:
    async def __call__(self, *args: object, **_: object) -> None:
        return None
