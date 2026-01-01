from __future__ import annotations

"""Agent-driven simulator strategy leveraging PydanticAI and TextPrompts."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..config import DEFAULT_SETTINGS, Settings
from .protocols import (
    AgentOutput,
    RespondToAssistant,
    TTSEngineProtocol,
    UserRequest,
    UserResponse,
    WaitContext,
    WaitForAssistant,
)
from .tts import OpenAITTSEngine


@dataclass(slots=True)
class Persona:
    background_context: str
    intent: str


class AgentRunResultProtocol(Protocol):
    """Protocol for PydanticAI agent run results."""

    output: AgentOutput  # RespondToAssistant or WaitForAssistant

    def all_messages(self) -> list[Any]:
        """Return all messages from this run (for conversation history)."""
        ...


class AgentProtocol(Protocol):
    """Protocol for PydanticAI-compatible agents."""

    async def run(
        self,
        prompt: str,
        *,
        deps: Any | None = None,
        message_history: Sequence[Any] | None = None,
        **kwargs: Any,
    ) -> AgentRunResultProtocol:
        """Run the agent with a prompt and optional history."""
        ...


import logging

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentTurnStrategy:
    """Strategy for agent-driven user responses.

    Manages conversation turns using a PydanticAI agent and maintains
    message history for multi-turn coherence. Supports wait tool responses
    that don't count as conversation turns.

    Attributes:
        agent: PydanticAI-compatible agent
        deps: Dependencies passed to agent.run() (contains persona, template, etc.)
        max_turns: Maximum number of turns before returning None
        send_as_text: If True, return text responses; if False, use TTS
        tts_engine: TTS engine for audio generation (required if send_as_text=False)
        tts_kwargs: Optional TTS configuration (voice, instructions)
        settings: Settings instance for TTS configuration (uses DEFAULT_SETTINGS if None)
        max_consecutive_waits: Maximum consecutive waits before forcing response
    """

    agent: AgentProtocol
    deps: Any
    max_turns: int
    send_as_text: bool
    tts_engine: TTSEngineProtocol | None
    tts_kwargs: Mapping[str, str | None] | None
    settings: Settings | None = None
    max_consecutive_waits: int = 10
    _message_history: list[Any] = field(default_factory=list)
    _turns_completed: int = 0
    _consecutive_waits: int = 0

    def __post_init__(self) -> None:
        """Validate configuration and auto-create TTS if needed."""
        if self.max_turns <= 0:
            msg = "max_turns must be positive"
            raise ValueError(msg)

        # Auto-create TTS engine if needed
        if not self.send_as_text and self.tts_engine is None:
            # Use TTS settings from config (defaults from simple_ai_client.py)
            resolved_settings = self.settings or DEFAULT_SETTINGS

            # Create the engine - use object.__setattr__ for slots=True dataclass
            object.__setattr__(
                self,
                "tts_engine",
                OpenAITTSEngine(
                    model=resolved_settings.tts_model,
                    default_voice=resolved_settings.tts_voice,
                    default_instructions=resolved_settings.tts_instructions,
                ),
            )

    async def next_response(self, request: UserRequest) -> UserResponse | None:
        """Generate next user response using the agent.

        Args:
            request: User request containing conversation context and assistant text

        Returns:
            UserResponse with text and/or audio, or None if max_turns reached.
            May return a wait response (is_wait=True) if agent uses wait tool.
        """
        if self._turns_completed >= self.max_turns:
            return None

        # Safety: limit consecutive waits to prevent infinite loops
        if self._consecutive_waits >= self.max_consecutive_waits:
            logger.warning(
                "Max consecutive waits (%d) reached, forcing response",
                self.max_consecutive_waits,
            )
            self._consecutive_waits = 0

        # Build prompt with wait context and data
        prompt = self._build_prompt(request)

        # Run agent with conversation history
        result = await self.agent.run(
            prompt,
            deps=self.deps,
            message_history=self._message_history if self._message_history else None,
        )

        # Get output - guaranteed to be RespondToAssistant or WaitForAssistant by PydanticAI
        output = result.output

        # Handle WaitForAssistant - yield turn
        if isinstance(output, WaitForAssistant):
            self._consecutive_waits += 1
            # Don't increment turns_completed - waits don't count as turns
            # Don't update message_history - this isn't a real turn
            # The wait context in the prompt tells the LLM that time has passed

            logger.info(
                "Agent requested wait of %.1fs (consecutive: %d, reason: %s)",
                output.wait_seconds,
                self._consecutive_waits,
                output.reason or "none",
            )
            return UserResponse(
                text=None,
                audio_path=None,
                data=(),
                wait_seconds=output.wait_seconds,
            )

        # Handle RespondToAssistant - send message
        assert isinstance(output, RespondToAssistant)
        output_text = output.message

        # Normal response - reset consecutive waits counter
        self._consecutive_waits = 0
        self._turns_completed += 1

        # Update history ONLY for actual responses
        self._message_history = result.all_messages()

        # Return text or audio response
        if self.send_as_text:
            return UserResponse(text=output_text, audio_path=None, data=())

        if self.tts_engine is None:
            msg = "TTS engine required when send_as_text is False"
            raise RuntimeError(msg)

        tts_kwargs = self.tts_kwargs or {}
        audio_path = await self.tts_engine.synthesize(
            output_text,
            voice=tts_kwargs.get("voice"),
            instructions=tts_kwargs.get("instructions"),
            conversation_id=request.conversation_id,
            turn_id=request.turn_id,
        )
        return UserResponse(text=output_text, audio_path=audio_path, data=())

    def _build_prompt(self, request: UserRequest) -> str:
        """Build prompt with full assistant message and wait context.

        The prompt includes:
        1. Wait context (if we've waited) - tells LLM time has passed
        2. Data from response.data events (if any)
        3. Full accumulated assistant text

        Args:
            request: User request with assistant text, data, and wait context

        Returns:
            Formatted prompt string for the agent
        """
        parts: list[str] = []

        # Add wait context if we've waited during this turn
        if request.wait_context and request.wait_context.wait_count > 0:
            parts.extend(self._format_wait_context(request.wait_context, request.text))
            parts.append("")

        # Add processed data if present (tool outputs, displays, etc.)
        if request.data_text:
            parts.append("<assistant_data>")
            parts.append(request.data_text)
            parts.append("</assistant_data>")
            parts.append("")

        # Add FULL assistant text
        if request.text:
            parts.append(request.text)
        elif not request.data_text:
            # No content at all - shouldn't happen but handle gracefully
            parts.append("(No assistant message)")

        return "\n".join(parts)

    def _format_wait_context(
        self, ctx: WaitContext, current_text: str | None
    ) -> list[str]:
        """Format wait context for inclusion in prompt.

        Args:
            ctx: Wait context with count and timing info
            current_text: Current accumulated text (to check for new content)

        Returns:
            List of lines for the wait context block
        """
        lines: list[str] = []
        lines.append("<wait_context>")
        lines.append(f"You have waited {ctx.wait_count} time(s) during this turn.")
        lines.append(f"Total wait time: ~{ctx.total_wait_seconds:.0f} seconds.")

        # Check if new content arrived since last wait
        current_len = len(current_text) if current_text else 0
        if ctx.has_new_content(current_len):
            lines.append("New content has arrived since your last wait.")
        else:
            lines.append("No new content has arrived since your last wait.")

        lines.append("")
        lines.append(
            "IMPORTANT: The assistant message below may contain earlier 'please wait'"
        )
        lines.append(
            "requests that have ALREADY been fulfilled. Focus on the END of the message"
        )
        lines.append("to determine the current state.")
        lines.append("</wait_context>")
        return lines
