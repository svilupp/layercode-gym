"""Unit tests for client race condition fixes and edge cases.

These tests verify the fixes for:
1. ACK race condition - turn_id captured before sleep
2. Final message recording - pending message appended before conclude
3. Empty turn handling - empty turns return None early
4. Queue signal handling - queue receives and processes signals
5. Consumer WS close - consumer doesn't call websocket.close()
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from layercode_gym import LayercodeClient
from layercode_gym.models.conversation import ConversationLog, Message
from layercode_gym.storage import ConversationStorage


class TestAcknowledgePlaybackCapturesTurnId:
    """Test that turn_id is captured before async sleep in _acknowledge_playback."""

    @pytest.mark.asyncio
    async def test_turn_id_captured_before_sleep(self):
        """Verify turn_id is captured before the sleep, not after."""
        client = LayercodeClient(simulator=MagicMock())
        mock_ws = AsyncMock()

        # Set initial turn_id
        client._assistant_state.turn_id = "turn_1"

        # Track what turn_id was used in the event
        sent_events = []

        async def capture_send(data):
            import json

            event = json.loads(data)
            sent_events.append(event)

        mock_ws.send = capture_send

        # Simulate a race: change turn_id during the sleep
        original_sleep = asyncio.sleep

        async def modified_sleep(seconds):
            # Simulate race: turn_id changes during sleep
            client._assistant_state.turn_id = "turn_2"
            await original_sleep(0.01)  # Use small sleep for test

        # Patch both sleep and playback_ack_delay for fast test
        client.playback_ack_delay = 0.01

        with patch("asyncio.sleep", modified_sleep):
            await client._acknowledge_playback(mock_ws)

        # The sent event should use the ORIGINAL turn_id, not the modified one
        assert len(sent_events) == 1
        assert sent_events[0]["turn_id"] == "turn_1"  # Original, not "turn_2"

    @pytest.mark.asyncio
    async def test_no_ack_when_turn_id_none(self):
        """Verify no ack is sent when turn_id is None."""
        client = LayercodeClient(simulator=MagicMock())
        mock_ws = AsyncMock()
        client._assistant_state.turn_id = None

        await client._acknowledge_playback(mock_ws)

        mock_ws.send.assert_not_called()


class TestConcludeRecordsPendingMessage:
    """Test that _conclude_conversation records pending assistant message."""

    @pytest.mark.asyncio
    async def test_pending_message_recorded_before_finalize(self):
        """Verify pending assistant message is appended to log before finalize."""
        client = LayercodeClient(simulator=MagicMock())
        mock_ws = AsyncMock()
        mock_storage = MagicMock(spec=ConversationStorage)
        mock_storage.write_transcript = MagicMock()
        mock_storage.export_combined_audio = MagicMock()
        log = ConversationLog(conversation_id="test_conv")

        # Set pending assistant message
        pending_msg = Message(
            role="assistant",
            content="Final response",
            audio_path=None,
            turn_id="turn_5",
            timestamp=datetime.now(timezone.utc),
            attachments=(),
        )
        client._pending_assistant_message = pending_msg

        # Mock the simulator to avoid cleanup issues
        client.simulator = MagicMock()

        await client._conclude_conversation(mock_ws, mock_storage, log)

        # Verify the final turn was appended
        assert len(log.turns) == 1
        final_turn = log.turns[0]
        assert final_turn.user_message is None
        assert final_turn.assistant_message is not None
        assert final_turn.assistant_message.content == "Final response"

        # Verify pending message was cleared
        assert client._pending_assistant_message is None

    @pytest.mark.asyncio
    async def test_no_pending_message_no_extra_turn(self):
        """Verify no extra turn is added when no pending message."""
        client = LayercodeClient(simulator=MagicMock())
        mock_ws = AsyncMock()
        mock_storage = MagicMock(spec=ConversationStorage)
        mock_storage.write_transcript = MagicMock()
        mock_storage.export_combined_audio = MagicMock()
        log = ConversationLog(conversation_id="test_conv")

        # No pending message
        client._pending_assistant_message = None

        await client._conclude_conversation(mock_ws, mock_storage, log)

        # No turns should be added
        assert len(log.turns) == 0


class TestFinaliseSkipsEmptyTurns:
    """Test that _finalise_assistant_message skips empty turns."""

    def test_empty_turn_returns_none(self):
        """Verify empty turns (no audio, no text) return None early."""
        client = LayercodeClient(simulator=MagicMock())
        mock_storage = MagicMock(spec=ConversationStorage)
        log = ConversationLog(conversation_id="test_conv")

        # Set turn_id but no content
        client._assistant_state.turn_id = "turn_empty"
        client._assistant_state.audio_chunks = []
        client._assistant_state.text_fragments = []

        result = client._finalise_assistant_message(mock_storage, log)

        # Should return None for empty turns
        assert result == (None, None)
        # turn_id should be reset
        assert client._assistant_state.turn_id is None

    def test_turn_with_text_not_skipped(self):
        """Verify turns with text are not skipped."""
        client = LayercodeClient(simulator=MagicMock())
        mock_storage = MagicMock(spec=ConversationStorage)
        mock_storage.store_text = MagicMock(return_value=Path("/tmp/text.txt"))
        log = ConversationLog(conversation_id="test_conv")

        # Set turn_id with text content
        client._assistant_state.turn_id = "turn_with_text"
        client._assistant_state.audio_chunks = []
        client._assistant_state.text_fragments = ["Hello", " world"]
        client._assistant_state.turn_started_at = datetime.now(timezone.utc)

        message, segment = client._finalise_assistant_message(mock_storage, log)

        # Should return a valid message
        assert message is not None
        assert message.content == "Hello world"
        assert segment is None

    def test_early_guard_does_not_trigger_for_audio(self):
        """Verify the early empty-turn guard passes for turns with audio.

        The has_audio check looks at audio_chunks presence, preventing the
        "idle timeout before content arrived" warning from logging.
        """
        client = LayercodeClient(simulator=MagicMock())
        mock_storage = MagicMock(spec=ConversationStorage)
        log = ConversationLog(conversation_id="test_conv")

        # Set turn_id with audio content only
        client._assistant_state.turn_id = "turn_with_audio"
        client._assistant_state.audio_chunks = ["base64audiodata"]
        client._assistant_state.text_fragments = []
        client._assistant_state.turn_started_at = datetime.now(timezone.utc)

        # With store_audio=False, audio isn't processed, so we can check
        # that the early guard doesn't skip this turn
        client.settings = MagicMock()
        client.settings.store_audio = False

        # Capture any warnings logged
        with patch("layercode_gym.client.logger") as mock_logger:
            message, segment = client._finalise_assistant_message(mock_storage, log)

            # The early guard should NOT have logged its warning
            # (warning is only for turns with no content at all)
            for call in mock_logger.warning.call_args_list:
                assert "idle timeout before content arrived" not in str(call)


class TestTurnQueueReceivesSignals:
    """Test that the queue receives and processes turn signals."""

    def test_queue_field_exists(self):
        """Verify _user_turn_queue field exists with correct type."""
        client = LayercodeClient(simulator=MagicMock())

        # Should have queue, not event
        assert hasattr(client, "_user_turn_queue")
        assert isinstance(client._user_turn_queue, asyncio.Queue)

    def test_no_event_field(self):
        """Verify _user_turn_event field no longer exists."""
        client = LayercodeClient(simulator=MagicMock())

        # Event field should not exist
        assert not hasattr(client, "_user_turn_event")

    @pytest.mark.asyncio
    async def test_queue_put_nowait(self):
        """Verify signals can be put on queue without blocking."""
        client = LayercodeClient(simulator=MagicMock())

        # Put signals on queue
        client._user_turn_queue.put_nowait("idle_timeout")
        client._user_turn_queue.put_nowait("wait_timeout")
        client._user_turn_queue.put_nowait("idle_timeout")

        # All 3 signals should be queued
        assert client._user_turn_queue.qsize() == 3

        # Retrieve them
        assert await client._user_turn_queue.get() == "idle_timeout"
        assert await client._user_turn_queue.get() == "wait_timeout"
        assert await client._user_turn_queue.get() == "idle_timeout"

    @pytest.mark.asyncio
    async def test_idle_timer_uses_queue(self):
        """Verify idle timer puts signal on queue, not sets event."""
        client = LayercodeClient(simulator=MagicMock())
        client.assistant_idle_timeout = 0.01  # Fast timeout for test

        # Schedule idle timer
        client._schedule_assistant_idle_check()

        # Wait for timer to fire
        await asyncio.sleep(0.05)

        # Signal should be on queue
        assert client._user_turn_queue.qsize() >= 1
        signal = await asyncio.wait_for(client._user_turn_queue.get(), timeout=1.0)
        assert signal == "idle_timeout"


class TestConsumerDoesNotCloseWs:
    """Test that _consume_events does not close the websocket."""

    @pytest.mark.asyncio
    async def test_consumer_does_not_call_close(self):
        """Verify consumer doesn't call websocket.close() at the end."""
        client = LayercodeClient(simulator=MagicMock())
        mock_ws = AsyncMock()
        mock_storage = MagicMock(spec=ConversationStorage)
        mock_storage.store_data_payload = MagicMock()
        log = ConversationLog(conversation_id="test_conv")

        # Create an async iterator that yields no events
        async def empty_iterator():
            return
            yield  # Make it a generator

        mock_ws.__aiter__ = lambda self: empty_iterator()

        await client._consume_events(mock_ws, mock_storage, log)

        # websocket.close should NOT have been called
        mock_ws.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_exits_on_stop_requested(self):
        """Verify consumer exits when stop_requested is set."""
        client = LayercodeClient(simulator=MagicMock())
        mock_ws = AsyncMock()
        mock_storage = MagicMock(spec=ConversationStorage)
        log = ConversationLog(conversation_id="test_conv")

        # Create an async iterator that yields one event then blocks
        events_yielded = []

        async def event_iterator():
            import json

            events_yielded.append("first")
            yield json.dumps({"type": "unknown.event"})
            # Set stop after first event
            client._stop_requested = True
            events_yielded.append("second")
            yield json.dumps({"type": "unknown.event"})

        mock_ws.__aiter__ = lambda self: event_iterator()

        await client._consume_events(mock_ws, mock_storage, log)

        # Should have processed first event then stopped
        assert "first" in events_yielded
        # websocket.close should NOT have been called
        mock_ws.close.assert_not_called()
