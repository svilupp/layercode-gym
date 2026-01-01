"""Unit tests for wait tool and smart turn-taking features.

These tests focus on the deterministic logic without making real LLM calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from layercode_gym.simulator.protocols import (
    MIN_WAIT_SECONDS,
    MAX_WAIT_SECONDS,
    RespondToAssistant,
    UserRequest,
    UserResponse,
    WaitContext,
    WaitForAssistant,
)
from layercode_gym.turn_dispatch.protocols import TurnContext, TurnDecision


# =============================================================================
# UserResponse Tests
# =============================================================================


class TestUserResponseIsWait:
    """Test the is_wait property on UserResponse."""

    @pytest.mark.parametrize(
        "wait_seconds,expected",
        [
            (None, False),
            (0, False),
            (-5, False),
            (MIN_WAIT_SECONDS, True),
            (60, True),
            (MAX_WAIT_SECONDS, True),
        ],
    )
    def test_is_wait(self, wait_seconds, expected):
        """is_wait should be True only for positive wait_seconds."""
        response = UserResponse(
            text=None, audio_path=None, data=(), wait_seconds=wait_seconds
        )
        assert response.is_wait is expected

    def test_wait_response_has_no_payload(self):
        """A wait-only response should have has_payload=False."""
        response = UserResponse(text=None, audio_path=None, data=(), wait_seconds=60)
        assert response.has_payload is False
        assert response.is_wait is True


# =============================================================================
# WaitForAssistant / RespondToAssistant Model Tests
# =============================================================================


class TestOutputModels:
    """Test the structured output models."""

    def test_wait_for_assistant(self):
        """WaitForAssistant creation with optional reason."""
        wait = WaitForAssistant(wait_seconds=30.0)
        assert wait.wait_seconds == 30.0
        assert wait.reason is None

        wait_with_reason = WaitForAssistant(wait_seconds=60.0, reason="Processing")
        assert wait_with_reason.reason == "Processing"

    def test_respond_to_assistant(self):
        """RespondToAssistant creation."""
        response = RespondToAssistant(message="Hello")
        assert response.message == "Hello"

    def test_wait_constants(self):
        """Wait time bounds are correctly defined."""
        assert MIN_WAIT_SECONDS == 2
        assert MAX_WAIT_SECONDS == 300


# =============================================================================
# WaitContext Tests
# =============================================================================


class TestWaitContext:
    """Test WaitContext dataclass behavior."""

    def test_initial_state(self):
        """WaitContext starts with zeros."""
        ctx = WaitContext()
        assert ctx.wait_count == 0
        assert ctx.total_wait_seconds == 0.0
        assert ctx.last_text_len == 0

    def test_record_wait(self):
        """record_wait increments count, accumulates time, updates text len."""
        ctx = WaitContext()

        ctx.record_wait(10.0, 50)
        assert ctx.wait_count == 1
        assert ctx.total_wait_seconds == 10.0
        assert ctx.last_text_len == 50

        ctx.record_wait(5.5, 100)
        assert ctx.wait_count == 2
        assert ctx.total_wait_seconds == 15.5
        assert ctx.last_text_len == 100

    def test_has_new_content(self):
        """has_new_content detects text growth since last wait."""
        ctx = WaitContext()
        # Initially, any text > 0 is "new"
        assert ctx.has_new_content(0) is False
        assert ctx.has_new_content(100) is True

        ctx.record_wait(10.0, 50)
        assert ctx.has_new_content(50) is False  # Same length
        assert ctx.has_new_content(51) is True  # Grew
        assert ctx.has_new_content(49) is False  # Shorter (edge case)

    def test_reset(self):
        """reset clears all fields."""
        ctx = WaitContext()
        ctx.record_wait(10.0, 50)
        ctx.record_wait(20.0, 100)

        ctx.reset()

        assert ctx.wait_count == 0
        assert ctx.total_wait_seconds == 0.0
        assert ctx.last_text_len == 0


# =============================================================================
# AgentTurnStrategy Tests
# =============================================================================


class TestAgentTurnStrategyWaitHandling:
    """Test AgentTurnStrategy wait detection and handling."""

    @pytest.fixture
    def strategy(self):
        """Create a strategy with mocked agent."""
        from layercode_gym.simulator.agent import AgentTurnStrategy

        mock_agent = AsyncMock()
        return AgentTurnStrategy(
            agent=mock_agent,
            deps=None,
            max_turns=10,
            send_as_text=True,
            tts_engine=None,
            tts_kwargs=None,
        )

    @pytest.mark.asyncio
    async def test_wait_response(self, strategy):
        """WaitForAssistant output produces wait response, doesn't count as turn."""
        mock_result = MagicMock()
        mock_result.output = WaitForAssistant(wait_seconds=30.0, reason="Processing")
        mock_result.all_messages = MagicMock(return_value=[])
        strategy.agent.run = AsyncMock(return_value=mock_result)

        request = UserRequest(
            conversation_id="test", turn_id="turn1", text="Please wait", data=()
        )

        response = await strategy.next_response(request)

        assert response.is_wait is True
        assert response.wait_seconds == 30.0
        assert response.text is None
        assert strategy._turns_completed == 0
        assert strategy._consecutive_waits == 1

    @pytest.mark.asyncio
    async def test_respond_response(self, strategy):
        """RespondToAssistant output produces normal response, counts as turn."""
        mock_result = MagicMock()
        mock_result.output = RespondToAssistant(message="Hello!")
        mock_result.all_messages = MagicMock(return_value=["msg"])
        strategy.agent.run = AsyncMock(return_value=mock_result)
        strategy._consecutive_waits = 5  # Simulate previous waits

        request = UserRequest(
            conversation_id="test", turn_id="turn1", text="Hi", data=()
        )

        response = await strategy.next_response(request)

        assert response.is_wait is False
        assert response.text == "Hello!"
        assert strategy._turns_completed == 1
        assert strategy._consecutive_waits == 0

    @pytest.mark.asyncio
    async def test_history_not_updated_on_wait(self, strategy):
        """Message history should NOT be updated after WaitForAssistant."""
        mock_result = MagicMock()
        mock_result.output = WaitForAssistant(wait_seconds=10.0)
        mock_result.all_messages = MagicMock(return_value=["new"])
        strategy.agent.run = AsyncMock(return_value=mock_result)

        initial_history = ["initial"]
        strategy._message_history = initial_history.copy()

        request = UserRequest(
            conversation_id="test", turn_id="turn1", text="Wait", data=()
        )
        await strategy.next_response(request)

        assert strategy._message_history == initial_history
        mock_result.all_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_history_updated_on_respond(self, strategy):
        """Message history should be updated after RespondToAssistant."""
        new_messages = ["user: hi", "assistant: hello"]
        mock_result = MagicMock()
        mock_result.output = RespondToAssistant(message="Hello!")
        mock_result.all_messages = MagicMock(return_value=new_messages)
        strategy.agent.run = AsyncMock(return_value=mock_result)

        strategy._message_history = ["old"]

        request = UserRequest(
            conversation_id="test", turn_id="turn1", text="Hi", data=()
        )
        await strategy.next_response(request)

        assert strategy._message_history == new_messages

    @pytest.mark.asyncio
    async def test_max_consecutive_waits_resets(self, strategy):
        """After max_consecutive_waits, counter resets before next call."""
        mock_result = MagicMock()
        mock_result.output = WaitForAssistant(wait_seconds=30.0)
        mock_result.all_messages = MagicMock(return_value=[])
        strategy.agent.run = AsyncMock(return_value=mock_result)

        strategy._consecutive_waits = strategy.max_consecutive_waits

        request = UserRequest(
            conversation_id="test", turn_id="turn1", text="Wait", data=()
        )
        await strategy.next_response(request)

        # After reset, incremented to 1
        assert strategy._consecutive_waits == 1


# =============================================================================
# AgentTurnStrategy Prompt Building Tests
# =============================================================================


class TestAgentTurnStrategyPromptBuilding:
    """Test _build_prompt with wait context."""

    @pytest.fixture
    def strategy(self):
        """Create a strategy for testing _build_prompt."""
        from layercode_gym.simulator.agent import AgentTurnStrategy

        return AgentTurnStrategy(
            agent=AsyncMock(),
            deps=None,
            max_turns=10,
            send_as_text=True,
            tts_engine=None,
            tts_kwargs=None,
        )

    def test_no_wait_context(self, strategy):
        """No <wait_context> block when no waits occurred."""
        request = UserRequest(
            conversation_id="test",
            turn_id="turn1",
            text="Hello",
            data=(),
            wait_context=None,
        )

        prompt = strategy._build_prompt(request)

        assert "<wait_context>" not in prompt
        assert "Hello" in prompt

    def test_wait_context_included(self, strategy):
        """<wait_context> block included after waits."""
        ctx = WaitContext()
        ctx.record_wait(10.0, 20)

        request = UserRequest(
            conversation_id="test",
            turn_id="turn1",
            text="Processing... Done!",
            data=(),
            wait_context=ctx,
        )

        prompt = strategy._build_prompt(request)

        assert "<wait_context>" in prompt
        assert "waited 1 time" in prompt
        assert "~10 seconds" in prompt
        assert "Processing... Done!" in prompt

    def test_new_content_detection(self, strategy):
        """Prompt correctly indicates whether new content arrived."""
        ctx = WaitContext()
        ctx.record_wait(10.0, 10)

        # New content (text > 10 chars)
        request = UserRequest(
            conversation_id="test",
            turn_id="turn1",
            text="Short text that grew!",
            data=(),
            wait_context=ctx,
        )
        prompt = strategy._build_prompt(request)
        assert "New content has arrived" in prompt

        # No new content (text <= 10 chars)
        ctx.last_text_len = 100
        request.wait_context = ctx
        prompt = strategy._build_prompt(request)
        assert "No new content" in prompt

    def test_data_text_included(self, strategy):
        """data_text appears in <assistant_data> block."""
        request = UserRequest(
            conversation_id="test",
            turn_id="turn1",
            text="Products shown",
            data=(),
            data_text="[5 products displayed]",
        )

        prompt = strategy._build_prompt(request)

        assert "<assistant_data>" in prompt
        assert "[5 products displayed]" in prompt
        assert "Products shown" in prompt

    def test_no_text_fallback(self, strategy):
        """Fallback message when no text or data."""
        request = UserRequest(
            conversation_id="test",
            turn_id="turn1",
            text=None,
            data=(),
        )

        prompt = strategy._build_prompt(request)
        assert "(No assistant message)" in prompt


# =============================================================================
# TurnDecision and TurnContext Tests
# =============================================================================


class TestTurnDecision:
    """Test TurnDecision dataclass."""

    def test_defaults(self):
        """Default values are correct."""
        decision = TurnDecision(should_respond=False)
        assert decision.recheck_in_seconds == 5.0
        assert decision.reason is None

    def test_frozen(self):
        """TurnDecision is immutable."""
        decision = TurnDecision(should_respond=True)
        with pytest.raises(AttributeError):
            decision.should_respond = False  # type: ignore[misc]


class TestTurnContext:
    """Test TurnContext dataclass."""

    def test_creation(self):
        """TurnContext accepts all fields."""
        context = TurnContext(
            assistant_messages=("Hello", "Wait 60 seconds"),
            last_user_text="Start",
            seconds_since_last_audio=5.5,
            conversation_turn_count=3,
        )
        assert len(context.assistant_messages) == 2
        assert context.seconds_since_last_audio == 5.5


# =============================================================================
# SmartTurnClassifier Tests
# =============================================================================


class TestSmartTurnClassifier:
    """Test SmartTurnClassifier with mocked agent."""

    @pytest.mark.asyncio
    async def test_returns_respond_on_error(self):
        """On error, defaults to should_respond=True."""
        from layercode_gym.turn_dispatch.smart_turn import SmartTurnClassifier

        classifier = SmartTurnClassifier()
        classifier._agent = None  # Force error

        context = TurnContext(
            assistant_messages=("Wait",),
            last_user_text=None,
            seconds_since_last_audio=5.0,
            conversation_turn_count=1,
        )

        decision = await classifier.should_respond(context)
        assert decision.should_respond is True

    @pytest.mark.asyncio
    async def test_parses_classifier_output(self):
        """Correctly parses ClassifierOutput."""
        from layercode_gym.turn_dispatch.smart_turn import (
            ClassifierOutput,
            SmartTurnClassifier,
        )

        classifier = SmartTurnClassifier()
        mock_result = MagicMock()
        mock_result.output = ClassifierOutput(decision="WAIT", reason="Processing")
        classifier._agent = AsyncMock()
        classifier._agent.run = AsyncMock(return_value=mock_result)

        context = TurnContext(
            assistant_messages=("Please wait",),
            last_user_text=None,
            seconds_since_last_audio=2.0,
            conversation_turn_count=1,
        )

        decision = await classifier.should_respond(context)
        assert decision.should_respond is False
        assert decision.reason == "Processing"


# =============================================================================
# Client Tests
# =============================================================================


class TestClientWaitContext:
    """Test LayercodeClient WaitContext integration."""

    def test_has_wait_context(self):
        """Client has _wait_context field initialized."""
        from layercode_gym import LayercodeClient

        client = LayercodeClient(simulator=MagicMock())

        assert isinstance(client._wait_context, WaitContext)
        assert client._wait_context.wait_count == 0

    def test_no_legacy_delta_tracking(self):
        """Legacy delta tracking fields should not exist."""
        from layercode_gym import LayercodeClient

        client = LayercodeClient(simulator=MagicMock())

        assert not hasattr(client, "_last_simulator_call_text_len")
        assert not hasattr(client, "_last_simulator_call_data_count")


class TestClientSmartTurnTaking:
    """Test LayercodeClient smart turn-taking."""

    def test_disabled_by_default(self):
        """Smart turn-taking is disabled by default."""
        from layercode_gym import LayercodeClient

        client = LayercodeClient(simulator=MagicMock())

        assert client.enable_smart_turn_taking is False
        assert client.smart_turn_classifier is None

    def test_creates_classifier_when_enabled(self):
        """Enabling creates SmartTurnClassifier."""
        from layercode_gym import LayercodeClient
        from layercode_gym.turn_dispatch.smart_turn import SmartTurnClassifier

        client = LayercodeClient(simulator=MagicMock(), enable_smart_turn_taking=True)

        assert client.enable_smart_turn_taking is True
        assert isinstance(client.smart_turn_classifier, SmartTurnClassifier)


class TestClientWaitTimer:
    """Test client wait timer logic."""

    def test_seconds_since_last_audio(self):
        """Correctly calculates time since last audio."""
        from datetime import datetime, timedelta, timezone

        from layercode_gym import LayercodeClient

        client = LayercodeClient(simulator=MagicMock())

        # No audio yet
        client._last_audio_received_at = None
        assert client._seconds_since_last_audio() == 0.0

        # 10 seconds ago
        client._last_audio_received_at = datetime.now(timezone.utc) - timedelta(
            seconds=10
        )
        elapsed = client._seconds_since_last_audio()
        assert 9.5 <= elapsed <= 10.5


# =============================================================================
# Integration Tests
# =============================================================================


class TestFromAgentIntegration:
    """Test UserSimulator.from_agent() integration."""

    def test_wait_tool_param(self):
        """enable_wait_tool parameter works."""
        from layercode_gym import Persona, UserSimulator

        # Default (enabled)
        sim = UserSimulator.from_agent(
            persona=Persona(background_context="Test", intent="Test"),
            max_turns=3,
            send_as_text=True,
        )
        assert sim is not None

        # Disabled
        sim = UserSimulator.from_agent(
            persona=Persona(background_context="Test", intent="Test"),
            max_turns=3,
            send_as_text=True,
            enable_wait_tool=False,
        )
        assert sim is not None
