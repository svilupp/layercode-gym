from __future__ import annotations

"""Agent-driven simulator strategy leveraging PydanticAI and TextPrompts."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..config import DEFAULT_SETTINGS, Settings
from .protocols import TTSEngineProtocol, UserRequest, UserResponse
from .tts import OpenAITTSEngine


@dataclass(slots=True)
class Persona:
    background_context: str
    intent: str


class AgentRunResultProtocol(Protocol):
    """Protocol for PydanticAI agent run results."""

    output: str  # For PydanticAI < 0.1, use .output; for >= 0.1, use .data

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
    ) -> AgentRunResultProtocol | str:
        """Run the agent with a prompt and optional history."""
        ...


@dataclass(slots=True)
class AgentTurnStrategy:
    """Strategy for agent-driven user responses.

    Manages conversation turns using a PydanticAI agent and maintains
    message history for multi-turn coherence.

    Attributes:
        agent: PydanticAI-compatible agent
        deps: Dependencies passed to agent.run() (contains persona, template, etc.)
        max_turns: Maximum number of turns before returning None
        send_as_text: If True, return text responses; if False, use TTS
        tts_engine: TTS engine for audio generation (required if send_as_text=False)
        tts_kwargs: Optional TTS configuration (voice, instructions)
        settings: Settings instance for TTS configuration (uses DEFAULT_SETTINGS if None)
    """

    agent: AgentProtocol
    deps: Any
    max_turns: int
    send_as_text: bool
    tts_engine: TTSEngineProtocol | None
    tts_kwargs: Mapping[str, str | None] | None
    settings: Settings | None = None
    _message_history: list[Any] = field(default_factory=list)
    _turns_completed: int = 0

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
            UserResponse with text and/or audio, or None if max_turns reached
        """
        if self._turns_completed >= self.max_turns:
            return None

        # Build prompt from request
        prompt = request.text or "Continue the conversation."

        # Append processed data context if available (what the user "sees" on screen)
        if request.data_text:
            prompt = f"{prompt}\n\n[DATA RECEIVED]\n{request.data_text}"

        # Run agent with conversation history
        result = await self.agent.run(
            prompt,
            deps=self.deps,
            message_history=self._message_history if self._message_history else None,
        )

        # Extract output text
        output_text = self._extract_output(result)

        # Update history with ALL messages from this run
        # PydanticAI's result.all_messages() includes both user and assistant messages
        if not isinstance(result, str):
            self._message_history = result.all_messages()

        self._turns_completed += 1

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

    @staticmethod
    def _extract_output(result: AgentRunResultProtocol | str) -> str:
        """Extract string output from agent result.

        Args:
            result: Agent result or string

        Returns:
            Output text

        Raises:
            TypeError: If output is not a string
        """
        if isinstance(result, str):
            return result
        output = result.output
        if not isinstance(output, str):  # pragma: no cover - defensive
            msg = "Agent output must be a string"
            raise TypeError(msg)
        return output
