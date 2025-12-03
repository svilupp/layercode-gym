from __future__ import annotations

"""Conversation-domain models for logging and callbacks."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

MessageRole = Literal["user", "assistant", "system"]


@dataclass(slots=True, frozen=True)
class TurnTiming:
    """Timing metrics for a single conversation turn."""

    turn_number: int
    role: Literal["user", "assistant"]

    # Start/end timestamps for this turn
    started_at: datetime
    ended_at: datetime

    # Time to first audio byte (TTFAB) - latency from turn start to first audio chunk
    # Only applicable for assistant turns
    time_to_first_audio_ms: float | None = None

    # Total duration of the turn
    @property
    def duration_ms(self) -> float:
        """Total duration of this turn in milliseconds."""
        delta = self.ended_at - self.started_at
        return delta.total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "turn_number": self.turn_number,
            "role": self.role,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "duration_ms": self.duration_ms,
            "time_to_first_audio_ms": self.time_to_first_audio_ms,
        }


@dataclass(slots=True, frozen=True)
class ConversationStats:
    """Comprehensive statistics about a completed conversation."""

    # Turn counts
    total_turns: int
    user_turns: int
    assistant_turns: int

    # Overall timing
    started_at: datetime
    ended_at: datetime

    # Per-turn timing details
    turn_timings: Sequence[TurnTiming] = field(default_factory=tuple)

    @property
    def duration_seconds(self) -> float:
        """Total conversation duration in seconds."""
        delta = self.ended_at - self.started_at
        return delta.total_seconds()

    @property
    def duration_ms(self) -> float:
        """Total conversation duration in milliseconds."""
        return self.duration_seconds * 1000

    @property
    def average_ttfab_ms(self) -> float | None:
        """Average time to first audio byte for assistant turns."""
        ttfab_values = [
            t.time_to_first_audio_ms
            for t in self.turn_timings
            if t.time_to_first_audio_ms is not None
        ]
        if not ttfab_values:
            return None
        return sum(ttfab_values) / len(ttfab_values)

    @property
    def median_ttfab_ms(self) -> float | None:
        """Median time to first audio byte for assistant turns."""
        ttfab_values = sorted(
            [
                t.time_to_first_audio_ms
                for t in self.turn_timings
                if t.time_to_first_audio_ms is not None
            ]
        )
        if not ttfab_values:
            return None
        mid = len(ttfab_values) // 2
        if len(ttfab_values) % 2 == 0:
            return (ttfab_values[mid - 1] + ttfab_values[mid]) / 2
        return ttfab_values[mid]

    @property
    def average_turn_duration_ms(self) -> float:
        """Average duration across all turns."""
        if not self.turn_timings:
            return 0.0
        return sum(t.duration_ms for t in self.turn_timings) / len(self.turn_timings)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "total_turns": self.total_turns,
            "user_turns": self.user_turns,
            "assistant_turns": self.assistant_turns,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "duration_ms": self.duration_ms,
            "average_ttfab_ms": self.average_ttfab_ms,
            "median_ttfab_ms": self.median_ttfab_ms,
            "average_turn_duration_ms": self.average_turn_duration_ms,
            "turn_timings": [t.to_dict() for t in self.turn_timings],
        }


@dataclass(slots=True)
class Attachment:
    path: Path
    kind: Literal["audio", "data", "text"]


@dataclass(slots=True)
class Message:
    role: MessageRole
    content: str | None
    audio_path: Path | None
    turn_id: str | None
    timestamp: datetime
    attachments: Sequence[Attachment] = field(default_factory=tuple)


@dataclass(slots=True)
class ConversationTurn:
    user_message: Message | None
    assistant_message: Message | None


@dataclass(slots=True)
class ConversationLog:
    conversation_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    turns: list[ConversationTurn] = field(default_factory=list)
    files: list[Attachment] = field(default_factory=list)
    stats: ConversationStats | None = None

    def append_turn(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)

    def add_file(self, attachment: Attachment) -> None:
        self.files.append(attachment)

    def finalize_stats(self, turn_timings: Sequence[TurnTiming]) -> None:
        """Compute final statistics when conversation ends."""
        user_count = sum(1 for t in self.turns if t.user_message is not None)
        assistant_count = sum(1 for t in self.turns if t.assistant_message is not None)

        # Use first turn's timestamp as start, or created_at if no turns
        started_at = self.created_at
        if turn_timings:
            started_at = turn_timings[0].started_at

        # Use last turn's timestamp as end
        ended_at = datetime.now(timezone.utc)
        if turn_timings:
            ended_at = turn_timings[-1].ended_at

        self.stats = ConversationStats(
            total_turns=len(self.turns),
            user_turns=user_count,
            assistant_turns=assistant_count,
            started_at=started_at,
            ended_at=ended_at,
            turn_timings=turn_timings,
        )

    def to_jsonable(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "turns": [
                {
                    "user": _message_to_dict(turn.user_message),
                    "assistant": _message_to_dict(turn.assistant_message),
                }
                for turn in self.turns
            ],
            "files": [
                {
                    "path": str(item.path),
                    "kind": item.kind,
                }
                for item in self.files
            ],
        }
        if self.stats is not None:
            result["stats"] = self.stats.to_dict()
        return result


def _message_to_dict(message: Message | None) -> dict[str, Any] | None:
    if message is None:
        return None
    return {
        "role": message.role,
        "content": message.content,
        "audio_path": str(message.audio_path) if message.audio_path else None,
        "turn_id": message.turn_id,
        "timestamp": message.timestamp.isoformat(),
        "attachments": [
            {"path": str(attachment.path), "kind": attachment.kind}
            for attachment in message.attachments
        ],
    }


def _message_from_dict(data: dict[str, Any] | None) -> Message | None:
    """Deserialize a dict back into a Message object."""
    if data is None:
        return None
    return Message(
        role=data["role"],
        content=data.get("content"),
        audio_path=Path(data["audio_path"]) if data.get("audio_path") else None,
        turn_id=data.get("turn_id"),
        timestamp=datetime.fromisoformat(data["timestamp"]),
        attachments=tuple(
            Attachment(path=Path(a["path"]), kind=a["kind"])
            for a in data.get("attachments", [])
        ),
    )


def conversation_log_from_dict(data: dict[str, Any]) -> ConversationLog:
    """Deserialize a dict (from JSON) back into a ConversationLog object."""
    turns = []
    for turn_data in data.get("turns", []):
        turn = ConversationTurn(
            user_message=_message_from_dict(turn_data.get("user")),
            assistant_message=_message_from_dict(turn_data.get("assistant")),
        )
        turns.append(turn)

    return ConversationLog(
        conversation_id=data["conversation_id"],
        created_at=datetime.fromisoformat(data["created_at"]),
        turns=turns,
        files=[
            Attachment(path=Path(f["path"]), kind=f["kind"])
            for f in data.get("files", [])
        ],
        # Stats are optional and computed, not loaded from JSON
        stats=None,
    )
