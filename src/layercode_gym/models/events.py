from __future__ import annotations

"""Typed representations of LayerCode WebSocket events."""

from dataclasses import dataclass
from typing import Literal, TypedDict, Any, NotRequired

# ---- Client -> Server messages -------------------------------------------------

ClientReadyType = Literal["client.ready"]
ClientAudioType = Literal["client.audio"]
ClientResponseTextType = Literal["client.response.text"]
TriggerResponseAudioFinishedType = Literal["trigger.response.audio.replay_finished"]
TriggerTurnStartType = Literal["trigger.turn.start"]
TriggerTurnEndType = Literal["trigger.turn.end"]
VADType = Literal["vad_events"]


class ClientReadyEvent(TypedDict):
    type: ClientReadyType


class ClientAudioEvent(TypedDict):
    type: ClientAudioType
    content: str


class ClientResponseTextEvent(TypedDict):
    type: ClientResponseTextType
    content: str


class TriggerResponseAudioFinishedEvent(TypedDict):
    type: TriggerResponseAudioFinishedType
    reason: Literal["completed", "interrupted"]
    turn_id: str


class TriggerTurnEvent(TypedDict):
    type: TriggerTurnStartType | TriggerTurnEndType
    role: Literal["user", "assistant"]


class VoiceActivityEvent(TypedDict):
    type: VADType
    event: Literal["vad_start", "vad_end", "vad_model_failed"]


ClientEvent = (
    ClientReadyEvent
    | ClientAudioEvent
    | ClientResponseTextEvent
    | TriggerResponseAudioFinishedEvent
    | TriggerTurnEvent
    | VoiceActivityEvent
)


# ---- Server -> Client messages -------------------------------------------------

TurnStartType = Literal["turn.start"]
ResponseAudioType = Literal["response.audio"]
ResponseTextType = Literal["response.text"]
UserTranscriptInterimType = Literal["user.transcript.interim_delta"]
UserTranscriptDeltaType = Literal["user.transcript.delta"]
UserTranscriptType = Literal["user.transcript"]
ResponseDataType = Literal["response.data"]


class TurnStartEvent(TypedDict):
    type: TurnStartType
    role: Literal["user", "assistant"]
    # Note: turn_id is NOT present in turn.start events
    # It comes later in response.audio/response.text events


class ResponseAudioEvent(TypedDict):
    type: ResponseAudioType
    content: str
    delta_id: NotRequired[str]  # Optional - not all backends include delta_id
    turn_id: NotRequired[str]  # Optional - not all backends include turn_id


class ResponseTextEvent(TypedDict):
    type: ResponseTextType
    content: str
    turn_id: NotRequired[str]  # Optional - not all backends include turn_id


class UserTranscriptInterimEvent(TypedDict):
    type: UserTranscriptInterimType
    content: str
    turn_id: str
    delta_counter: int


class UserTranscriptDeltaEvent(TypedDict):
    type: UserTranscriptDeltaType
    content: str
    turn_id: str
    delta_counter: int


class UserTranscriptEvent(TypedDict):
    type: UserTranscriptType
    content: str
    turn_id: str


class ResponseDataEvent(TypedDict):
    type: ResponseDataType
    content: dict[str, Any]
    turn_id: NotRequired[str]  # Optional - not all backends include turn_id


ServerEvent = (
    TurnStartEvent
    | ResponseAudioEvent
    | ResponseTextEvent
    | UserTranscriptInterimEvent
    | UserTranscriptDeltaEvent
    | UserTranscriptEvent
    | ResponseDataEvent
)


# ---- Conversation logging ------------------------------------------------------


@dataclass(slots=True)
class AudioChunk:
    """Assistant audio chunk captured during a turn."""

    turn_id: str
    delta_id: str
    base64_content: str
