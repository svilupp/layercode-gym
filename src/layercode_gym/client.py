from __future__ import annotations

"""Async LayerCode client orchestrating voice conversations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import asyncio
import base64
import json
from collections.abc import AsyncIterator
from typing import Any, Protocol, cast

import httpx
from websockets.asyncio.client import connect

from pydub import AudioSegment

from .callbacks import ConversationCallback, NoOpCallback, TurnCallback
from .config import DEFAULT_SETTINGS, Settings
from .logging_utils import configure_logging
from .models.conversation import (
    Attachment,
    ConversationLog,
    ConversationTurn,
    Message,
    TurnTiming,
)
from .models.events import (
    ClientAudioEvent,
    ClientReadyEvent,
    ClientResponseTextEvent,
    ResponseAudioEvent,
    ResponseDataEvent,
    ResponseTextEvent,
    TurnStartEvent,
    TriggerResponseAudioFinishedEvent,
    UserTranscriptDeltaEvent,
    UserTranscriptEvent,
    UserTranscriptInterimEvent,
)
from .simulator.protocols import (
    ResponseDataProcessor,
    UserRequest,
    UserResponse,
    UserSimulatorProtocol,
)
from .storage import ConversationStorage
from .utils.audio import (
    base64_to_segment,
    ensure_mono_pcm16,
    load_audio,
)


class WebSocketConnection(Protocol):
    async def send(self, data: str) -> None: ...

    async def close(self) -> None: ...

    def __aiter__(self) -> AsyncIterator[str]: ...


logger = configure_logging()


@dataclass(slots=True)
class AuthorizationResult:
    conversation_id: str
    client_session_key: str


@dataclass(slots=True)
class AssistantState:
    turn_id: str | None = None
    audio_chunks: list[str] = field(default_factory=list)
    text_fragments: list[str] = field(default_factory=list)
    turn_started_at: datetime | None = None
    first_audio_received_at: datetime | None = None

    def reset(self, turn_id: str) -> None:
        self.turn_id = turn_id
        self.audio_chunks.clear()
        self.text_fragments.clear()
        self.turn_started_at = datetime.now(timezone.utc)
        self.first_audio_received_at = None

    def append_audio(self, content: str) -> None:
        if self.first_audio_received_at is None:
            self.first_audio_received_at = datetime.now(timezone.utc)
        self.audio_chunks.append(content)

    def append_text(self, content: str) -> None:
        self.text_fragments.append(content)


@dataclass(slots=True)
class LayercodeClient:
    """Async client for orchestrating voice conversations with LayerCode agents.

    Attributes:
        simulator: User simulator for generating responses
        settings: Configuration settings
        turn_callback: Callback invoked after each turn completes
        conversation_callback: Callback invoked when conversation ends
        data_processor: Processor for response.data events (converts to text for AI context)
        playback_ack_delay: Delay before acknowledging playback completion
        assistant_idle_timeout: Seconds of silence before triggering user turn
    """

    simulator: UserSimulatorProtocol
    settings: Settings = DEFAULT_SETTINGS
    turn_callback: TurnCallback | None = None
    conversation_callback: ConversationCallback | None = None
    data_processor: ResponseDataProcessor | None = None
    playback_ack_delay: float = 0.4
    assistant_idle_timeout: float = (
        3.0  # Seconds of silence before triggering user turn
    )

    _assistant_state: AssistantState = field(default_factory=AssistantState)
    _latest_user_text: str = ""
    _stop_requested: bool = False
    _finalised: bool = False
    _pending_assistant_message: Message | None = None
    _mix_segments: list[AudioSegment] = field(default_factory=list)
    _turn_timings: list[TurnTiming] = field(default_factory=list)
    _user_turn_started_at: datetime | None = None
    _assistant_idle_task: asyncio.Task[None] | None = None
    _user_turn_event: asyncio.Event = field(default_factory=asyncio.Event)
    _user_turn_in_progress: bool = False
    _accumulated_data: list[dict[str, Any]] = field(default_factory=list)

    async def run(
        self,
        *,
        conversation_id: str | None = None,
        session_key: str | None = None,
        request_timeout: float = 10.0,
    ) -> str:
        logger.info("Starting client.run()")
        authorization = await self._authorize(
            conversation_id, session_key, request_timeout
        )
        logger.info(
            "Authorization successful: conversation_id=%s",
            authorization.conversation_id,
        )
        storage = ConversationStorage(
            self.settings.output_root,
            authorization.conversation_id,
            store_audio=self.settings.store_audio,
        )
        conversation_log = ConversationLog(
            conversation_id=authorization.conversation_id
        )
        ws_url = f"{self.settings.websocket_url}?client_session_key={authorization.client_session_key}"
        logger.info("Connecting to WebSocket: %s", ws_url)

        async with connect(ws_url) as websocket:
            logger.info("WebSocket connected")
            ws = cast(WebSocketConnection, websocket)
            await self._send_ready(ws)
            logger.info("Sent client.ready, starting event loop")

            # Run event consumer and turn coordinator concurrently
            consumer_task = asyncio.create_task(
                self._consume_events(ws, storage, conversation_log)
            )
            coordinator_task = asyncio.create_task(
                self._turn_coordinator(ws, storage, conversation_log)
            )

            # Wait for either task to complete
            done, pending = await asyncio.wait(
                {consumer_task, coordinator_task}, return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        logger.info("WebSocket closed")
        if not self._finalised:
            await self._finalize(storage, conversation_log)
        return authorization.conversation_id

    async def _authorize(
        self,
        conversation_id: str | None,
        session_key: str | None,
        timeout: float,
    ) -> AuthorizationResult:
        if session_key and conversation_id:
            return AuthorizationResult(
                conversation_id=conversation_id, client_session_key=session_key
            )
        if session_key and not conversation_id:
            return AuthorizationResult(
                conversation_id="conversation", client_session_key=session_key
            )

        agent_id = self.settings.agent_id
        if agent_id is None and session_key is None:
            msg = "agent_id required to request authorization"
            raise ValueError(msg)

        # Build authorization URL: user's backend server + authorize path
        base_url = self.settings.server_url.rstrip("/")
        auth_path = self.settings.authorize_path.lstrip("/")
        authorize_url = f"{base_url}/{auth_path}"
        logger.info("Authorizing with backend: %s", authorize_url)

        # Build headers (include any custom authorization headers)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.settings.authorization_headers:
            headers.update(self.settings.authorization_headers)

        # Build payload
        payload: dict[str, Any] = {"agent_id": agent_id}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if self.settings.custom_metadata:
            payload["custom_metadata"] = self.settings.custom_metadata
        if self.settings.custom_headers:
            payload["custom_headers"] = self.settings.custom_headers
        logger.debug("Authorization payload: %s", payload)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(authorize_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            logger.debug("Authorization response: %s", data)

        # Support both snake_case and camelCase response keys for compatibility
        session = data.get("client_session_key") or data.get("clientSessionKey")
        conv_id = (
            data.get("conversation_id") or data.get("conversationId")
            if conversation_id is None
            else conversation_id
        )
        if not isinstance(session, str) or not session:
            msg = (
                "Authorization response missing client_session_key or clientSessionKey"
            )
            raise RuntimeError(msg)
        if not isinstance(conv_id, str) or not conv_id:
            msg = "Authorization response missing conversation_id or conversationId"
            raise RuntimeError(msg)
        return AuthorizationResult(conversation_id=conv_id, client_session_key=session)

    async def _send_ready(self, websocket: WebSocketConnection) -> None:
        event: ClientReadyEvent = {"type": "client.ready"}
        await websocket.send(json.dumps(event))

    async def _turn_coordinator(
        self,
        websocket: WebSocketConnection,
        storage: ConversationStorage,
        log: ConversationLog,
    ) -> None:
        """Wait for user turn events and handle them."""
        logger.info("Starting turn coordinator")
        while not self._stop_requested:
            try:
                await self._user_turn_event.wait()
            except asyncio.CancelledError:
                break
            self._user_turn_event.clear()
            logger.info("User turn event received, handling turn")
            self._user_turn_in_progress = True
            await self._handle_user_turn("user_turn", websocket, storage, log)
            self._user_turn_in_progress = False

    async def _consume_events(
        self,
        websocket: WebSocketConnection,
        storage: ConversationStorage,
        log: ConversationLog,
    ) -> None:
        logger.info("Starting event consumption loop")
        async for raw in websocket:
            if self._stop_requested:
                logger.info("Stop requested, breaking event loop")
                break
            payload = json.loads(raw)
            event_type = payload.get("type")
            logger.debug("Received event: %s", event_type)
            match event_type:
                case "turn.start":
                    turn_event = cast(TurnStartEvent, payload)
                    await self._on_turn_start(turn_event, websocket, storage, log)
                case "response.audio":
                    audio_event = cast(ResponseAudioEvent, payload)
                    if self._assistant_state.turn_id is None:
                        # turn_id is optional - generate fallback if not present
                        turn_id = (
                            audio_event.get("turn_id") or f"turn_{id(audio_event)}"
                        )
                        self._assistant_state.reset(turn_id)
                    self._assistant_state.append_audio(audio_event["content"])
                    # Reset idle timer every time we receive audio
                    self._schedule_assistant_idle_check()
                case "response.text":
                    text_event = cast(ResponseTextEvent, payload)
                    if self._assistant_state.turn_id is None:
                        # turn_id is optional - generate fallback if not present
                        turn_id = text_event.get("turn_id") or f"turn_{id(text_event)}"
                        self._assistant_state.reset(turn_id)
                    self._assistant_state.append_text(text_event["content"])
                case "user.transcript.interim_delta":
                    interim_event = cast(UserTranscriptInterimEvent, payload)
                    self._latest_user_text = interim_event["content"]
                case "user.transcript.delta":
                    delta_event = cast(UserTranscriptDeltaEvent, payload)
                    self._latest_user_text = delta_event["content"]
                case "user.transcript":
                    transcript_event = cast(UserTranscriptEvent, payload)
                    self._latest_user_text = transcript_event["content"]
                case "response.data":
                    data_event = cast(ResponseDataEvent, payload)
                    # turn_id is optional - use current turn_id from state, or fallback
                    turn_id = data_event.get(
                        "turn_id", self._assistant_state.turn_id or "data"
                    )
                    storage.store_data_payload(data_event["content"], name=turn_id)
                    # Accumulate data for processing by data_processor
                    self._accumulated_data.append(data_event["content"])
                case _:
                    logger.error("Unhandled event: %s", event_type)
        await websocket.close()

    async def _on_turn_start(
        self,
        event: TurnStartEvent,
        websocket: WebSocketConnection,
        storage: ConversationStorage,
        log: ConversationLog,
    ) -> None:
        role = event["role"]
        logger.info("Turn start: role=%s", role)
        if role == "assistant":
            # Don't reset state here - turn_id will come in response.audio/response.text
            # Schedule idle timer in case no content arrives (e.g., resumed conversation
            # where agent doesn't send a welcome message)
            self._schedule_assistant_idle_check()
            return

        # User turn starting - this is triggered by the server
        # We don't actually handle it here since LayerCode doesn't send turn.start for user
        # User turns are triggered by the idle timeout after assistant finishes
        logger.info("User turn.start received (unexpected from LayerCode)")

    async def _acknowledge_playback(self, websocket: WebSocketConnection) -> None:
        if self._assistant_state.turn_id is None:
            return
        await asyncio.sleep(self.playback_ack_delay)
        event: TriggerResponseAudioFinishedEvent = {
            "type": "trigger.response.audio.replay_finished",
            "turn_id": self._assistant_state.turn_id,
            "reason": "completed",
        }
        await websocket.send(json.dumps(event))

    def _finalise_assistant_message(
        self,
        storage: ConversationStorage,
        log: ConversationLog,
    ) -> tuple[Message | None, AudioSegment | None]:
        if self._assistant_state.turn_id is None:
            return None, None

        # Record timing for this assistant turn
        ended_at = datetime.now(timezone.utc)
        if self._assistant_state.turn_started_at is not None:
            ttfab_ms = None
            if self._assistant_state.first_audio_received_at is not None:
                delta = (
                    self._assistant_state.first_audio_received_at
                    - self._assistant_state.turn_started_at
                )
                ttfab_ms = delta.total_seconds() * 1000

            timing = TurnTiming(
                turn_number=len(log.turns),
                role="assistant",
                started_at=self._assistant_state.turn_started_at,
                ended_at=ended_at,
                time_to_first_audio_ms=ttfab_ms,
            )
            self._turn_timings.append(timing)

        text = (
            "".join(self._assistant_state.text_fragments)
            if self._assistant_state.text_fragments
            else None
        )
        segment: AudioSegment | None = None
        attachments: list[Attachment] = []
        audio_path_stored: Path | None = None
        timestamp = datetime.now(timezone.utc)
        # Only process audio if store_audio is enabled
        if self._assistant_state.audio_chunks and self.settings.store_audio:
            segment = ensure_mono_pcm16(
                self._combine_chunks(self._assistant_state.audio_chunks)
            )
            stored_path = storage.store_audio_segment(
                segment,
                role="assistant",
                turn_index=len(log.turns),
                timestamp=timestamp,
            )
            if stored_path is not None:
                audio_path_stored = stored_path
                attachments.append(Attachment(path=stored_path, kind="audio"))
        if text:
            text_path = storage.store_text(
                text, role="assistant", turn_index=len(log.turns), timestamp=timestamp
            )
            attachments.append(Attachment(path=text_path, kind="text"))
        if not attachments and text is None:
            return None, None
        message = Message(
            role="assistant",
            content=text,
            audio_path=audio_path_stored,
            turn_id=self._assistant_state.turn_id,
            timestamp=datetime.now(timezone.utc),
            attachments=tuple(attachments),
        )
        self._assistant_state.turn_id = None
        self._assistant_state.audio_chunks.clear()
        self._assistant_state.text_fragments.clear()
        return message, segment

    def _combine_chunks(self, chunks: list[str]) -> AudioSegment:
        audio = base64_to_segment(chunks[0])
        for chunk in chunks[1:]:
            audio += base64_to_segment(chunk)
        return audio

    async def _handle_user_turn(
        self,
        turn_id: str,
        websocket: WebSocketConnection,
        storage: ConversationStorage,
        log: ConversationLog,
    ) -> None:
        # First, acknowledge playback and finalize assistant message
        await self._acknowledge_playback(websocket)
        assistant_message, assistant_segment = self._finalise_assistant_message(
            storage, log
        )
        self._pending_assistant_message = assistant_message
        if assistant_segment is not None and self.settings.store_audio:
            self._mix_segments.append(assistant_segment)

        # Track user turn start time
        self._user_turn_started_at = datetime.now(timezone.utc)
        logger.info("Handling user turn, requesting response from simulator")

        # Process accumulated response.data events into text for AI context
        data_text: str | None = None
        if self._accumulated_data and self.data_processor:
            processed_parts = [self.data_processor(d) for d in self._accumulated_data]
            # Filter out empty strings and join
            non_empty = [p for p in processed_parts if p]
            if non_empty:
                data_text = "\n".join(non_empty)

        request = UserRequest(
            conversation_id=log.conversation_id,
            turn_id=turn_id,
            text=self._latest_user_text or None,
            data=tuple(self._accumulated_data),
            data_text=data_text,
        )
        response = await self.simulator.get_response(request)
        logger.debug("Simulator response: %s", response)
        self._latest_user_text = ""
        self._accumulated_data.clear()  # Clear after processing
        if response is None or not response.has_payload:
            logger.info("No payload from simulator, concluding conversation")
            await self._conclude_conversation(websocket, storage, log)
            return
        logger.info("Sending user payload to WebSocket")
        await self._send_user_payload(websocket, response)

        # Record user turn timing
        user_turn_ended_at = datetime.now(timezone.utc)
        if self._user_turn_started_at is not None:
            user_timing = TurnTiming(
                turn_number=len(log.turns),
                role="user",
                started_at=self._user_turn_started_at,
                ended_at=user_turn_ended_at,
                time_to_first_audio_ms=None,  # Not applicable for user turns
            )
            self._turn_timings.append(user_timing)

        turn = await self._record_turn(response, storage, log, request)
        if turn is not None and self.turn_callback is not None:
            await self.turn_callback(turn, log)

    async def _send_user_payload(
        self, websocket: WebSocketConnection, response: UserResponse
    ) -> None:
        # Send ONLY audio OR text, never both (LayerCode treats them as separate inputs)
        if response.audio_path is not None:
            await self._send_user_audio_chunked(websocket, response.audio_path)
        elif response.text is not None:
            logger.info("Sending client.response.text: %s", response.text[:50])
            event_text: ClientResponseTextEvent = {
                "type": "client.response.text",
                "content": response.text,
            }
            await websocket.send(json.dumps(event_text))
            logger.info("Text sent successfully")

    async def _send_user_audio_chunked(
        self, websocket: WebSocketConnection, audio_path: Path
    ) -> None:
        """Stream user audio in chunks to avoid message size limits.

        Follows the pattern from simple_ai_client.py for reliable audio streaming.
        """
        logger.info("Loading and chunking user audio from: %s", audio_path)
        segment = ensure_mono_pcm16(load_audio(audio_path))

        # Get raw PCM bytes from AudioSegment
        pcm_data = segment.raw_data

        # Calculate chunk size based on settings
        frame_bytes = 2  # mono 16-bit PCM
        sample_rate = segment.frame_rate

        if self.settings.chunk_ms <= 0:
            # Send entire audio in one chunk
            frames_per_chunk = max(len(pcm_data) // frame_bytes, 1)
        else:
            # Calculate frames per chunk based on chunk_ms
            frames_per_chunk = max(
                int(sample_rate * (self.settings.chunk_ms / 1000.0)), 1
            )

        chunk_size = frames_per_chunk * frame_bytes

        logger.info(
            "Streaming user audio (%d Hz) in chunks of %d frame(s) (%d ms per chunk)",
            sample_rate,
            frames_per_chunk,
            self.settings.chunk_ms,
        )

        # Stream audio chunks sequentially
        offset = 0
        chunks_sent = 0
        while offset < len(pcm_data):
            chunk = pcm_data[offset : offset + chunk_size]
            offset += chunk_size
            if not chunk:
                break

            # Encode chunk to base64
            content = base64.b64encode(chunk).decode("ascii")

            # Send chunk
            event_audio: ClientAudioEvent = {"type": "client.audio", "content": content}
            await websocket.send(json.dumps(event_audio))
            chunks_sent += 1

            # Optional delay between chunks
            if self.settings.chunk_interval > 0:
                await asyncio.sleep(self.settings.chunk_interval)

        logger.info(
            "Finished streaming user audio (%d chunks sent, total %d bytes)",
            chunks_sent,
            len(pcm_data),
        )

    async def _record_turn(
        self,
        response: UserResponse,
        storage: ConversationStorage,
        log: ConversationLog,
        request: UserRequest,
    ) -> ConversationTurn | None:
        user_attachments: list[Attachment] = []
        user_audio_segment = None
        user_audio_path = None
        timestamp = datetime.now(timezone.utc)
        # Only process audio if store_audio is enabled
        if response.audio_path is not None and self.settings.store_audio:
            user_audio_segment = ensure_mono_pcm16(load_audio(response.audio_path))
            stored_path = storage.store_audio_segment(
                user_audio_segment,
                role="user",
                turn_index=len(log.turns),
                timestamp=timestamp,
            )
            if stored_path is not None:
                user_audio_path = stored_path
                user_attachments.append(Attachment(path=stored_path, kind="audio"))
        if response.text is not None:
            text_path = storage.store_text(
                response.text,
                role="user",
                turn_index=len(log.turns),
                timestamp=timestamp,
            )
            user_attachments.append(Attachment(path=text_path, kind="text"))
        if user_audio_segment is not None and self.settings.store_audio:
            self._mix_segments.append(user_audio_segment)

        user_message = Message(
            role="user",
            content=response.text,
            audio_path=user_audio_path,
            turn_id=request.turn_id,
            timestamp=datetime.now(timezone.utc),
            attachments=tuple(user_attachments),
        )
        assistant_message = self._pending_assistant_message
        self._pending_assistant_message = None
        turn = ConversationTurn(
            user_message=user_message, assistant_message=assistant_message
        )
        log.append_turn(turn)
        return turn

    async def _conclude_conversation(
        self,
        websocket: WebSocketConnection,
        storage: ConversationStorage,
        log: ConversationLog,
    ) -> None:
        self._stop_requested = True
        # Finalize stats and save transcript before callback
        await self._finalize(storage, log)
        # Run callback BEFORE closing websocket to prevent task cancellation
        callback = self.conversation_callback or NoOpCallback()
        await callback(log)
        self._finalised = True
        # Close websocket last (this will complete the consumer task)
        await websocket.close()

    async def _finalize(
        self, storage: ConversationStorage, log: ConversationLog
    ) -> None:
        # Cancel any pending idle timer
        self._cancel_assistant_idle_timer()

        # Compute final stats with all turn timings
        log.finalize_stats(tuple(self._turn_timings))

        # Write transcript (now includes stats)
        storage.write_transcript(log)

        # Export combined audio
        if self._mix_segments:
            storage.export_combined_audio(self._mix_segments)

        # Cleanup temporary TTS files for this conversation
        self._cleanup_tts_temp_files(log.conversation_id)

    def _cleanup_tts_temp_files(self, conversation_id: str) -> None:
        """Clean up temporary TTS files for this conversation."""
        from .simulator.base import UserSimulator
        from .simulator.tts import OpenAITTSEngine

        # Try to access TTS engine from simulator strategy
        if isinstance(self.simulator, UserSimulator):
            strategy = self.simulator.strategy
            tts_engine = getattr(strategy, "tts_engine", None)
            if isinstance(tts_engine, OpenAITTSEngine):
                deleted = tts_engine.cleanup_temp_files(conversation_id)
                if deleted > 0:
                    logger.debug("Cleaned up %d temporary TTS files", deleted)

    def _schedule_assistant_idle_check(self) -> None:
        """Schedule a timer to trigger user turn after assistant idle timeout."""
        self._cancel_assistant_idle_timer()
        if self.assistant_idle_timeout <= 0:
            logger.debug(
                "Idle timeout disabled (timeout=%s)", self.assistant_idle_timeout
            )
            return

        logger.info(
            "Scheduling assistant idle timer for %s seconds",
            self.assistant_idle_timeout,
        )

        async def idle_timer() -> None:
            try:
                await asyncio.sleep(self.assistant_idle_timeout)
                logger.info("Assistant idle timeout reached, triggering user turn")
                self._user_turn_event.set()
            except asyncio.CancelledError:
                logger.debug("Idle timer cancelled")
                return

        loop = asyncio.get_running_loop()
        self._assistant_idle_task = loop.create_task(
            idle_timer(), name="assistant_idle_timer"
        )

    def _cancel_assistant_idle_timer(self) -> None:
        """Cancel the assistant idle timer if it's running."""
        if self._assistant_idle_task and not self._assistant_idle_task.done():
            self._assistant_idle_task.cancel()
        self._assistant_idle_task = None
