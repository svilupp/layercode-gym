from __future__ import annotations

"""Concrete simulator capable of scripted or agent-driven responses."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, cast

from ..config import DEFAULT_SETTINGS, Settings
from .protocols import (
    SimulatorHook,
    TTSEngineProtocol,
    UserRequest,
    UserResponse,
    UserSimulatorProtocol,
)
from .agent import AgentProtocol, AgentTurnStrategy
from .tts import OpenAITTSEngine


class _Strategy(Protocol):
    async def next_response(self, request: UserRequest) -> UserResponse | None: ...


@dataclass(slots=True)
class TextScriptStrategy:
    messages: list[str]
    send_as_text: bool
    tts_engine: TTSEngineProtocol | None
    tts_voice: str | None
    tts_instructions: str | None

    async def next_response(self, request: UserRequest) -> UserResponse | None:
        if not self.messages:
            return None
        text = self.messages.pop(0)
        if self.send_as_text:
            return UserResponse(text=text, audio_path=None, data=())
        if self.tts_engine is None:
            raise RuntimeError("TTS engine required when send_as_text is False")
        audio_path = await self.tts_engine.synthesize(
            text,
            voice=self.tts_voice,
            instructions=self.tts_instructions,
            conversation_id=request.conversation_id,
            turn_id=request.turn_id,
        )
        return UserResponse(text=text, audio_path=audio_path, data=())


@dataclass(slots=True)
class FileScriptStrategy:
    files: list[Path]

    async def next_response(self, request: UserRequest) -> UserResponse | None:
        if not self.files:
            return None
        audio_path = self.files.pop(0)
        return UserResponse(text=None, audio_path=audio_path, data=())


@dataclass(slots=True)
class UserSimulator(UserSimulatorProtocol):
    strategy: _Strategy
    pre_hook: SimulatorHook | None = None
    post_hook: SimulatorHook | None = None

    async def get_response(self, request: UserRequest) -> UserResponse | None:
        if self.pre_hook is not None:
            override = await self.pre_hook(request, None)
            if override is not None and override.has_payload:
                return override
            if override is not None and not override.has_payload:
                return None
        response = await self.strategy.next_response(request)
        if response is None:
            return None
        if self.post_hook is not None:
            override = await self.post_hook(request, response)
            if override is not None:
                return override if override.has_payload else None
        return response

    @classmethod
    def from_text(
        cls,
        messages: Sequence[str],
        *,
        send_as_text: bool = False,
        tts_engine: TTSEngineProtocol | None = None,
        tts_kwargs: Mapping[str, str | None] | None = None,
        settings: Settings | None = None,
        pre_hook: SimulatorHook | None = None,
        post_hook: SimulatorHook | None = None,
    ) -> "UserSimulator":
        kwargs = tts_kwargs or {}
        resolved_settings = settings or DEFAULT_SETTINGS

        # Auto-create TTS engine if needed
        resolved_tts_engine = tts_engine
        if not send_as_text and tts_engine is None:
            # Use TTS settings from config (defaults from simple_ai_client.py)
            resolved_tts_engine = OpenAITTSEngine(
                model=resolved_settings.tts_model,
                default_voice=resolved_settings.tts_voice,
                default_instructions=resolved_settings.tts_instructions,
            )

        strategy = TextScriptStrategy(
            messages=list(messages),
            send_as_text=send_as_text,
            tts_engine=resolved_tts_engine,
            tts_voice=kwargs.get("voice"),
            tts_instructions=kwargs.get("instructions"),
        )
        return cls(strategy=strategy, pre_hook=pre_hook, post_hook=post_hook)

    @classmethod
    def from_files(
        cls,
        files: Sequence[Path],
        *,
        pre_hook: SimulatorHook | None = None,
        post_hook: SimulatorHook | None = None,
    ) -> "UserSimulator":
        strategy = FileScriptStrategy(files=list(files))
        return cls(strategy=strategy, pre_hook=pre_hook, post_hook=post_hook)

    @classmethod
    def from_agent(
        cls,
        *,
        agent: "Any | None" = None,
        deps: Any | None = None,
        persona: "Any | None" = None,
        model: str | None = None,
        max_turns: int = 3,
        send_as_text: bool = False,
        tts_engine: TTSEngineProtocol | None = None,
        tts_kwargs: Mapping[str, str | None] | None = None,
        settings: Settings | None = None,
        pre_hook: SimulatorHook | None = None,
        post_hook: SimulatorHook | None = None,
    ) -> "UserSimulator":
        """Create simulator with AI agent.

        This method provides two modes of operation:

        1. **Default mode** (out-of-the-box): Omit `agent` and `deps` to use built-in
           basic agent with optional persona/model customization.

        2. **Power user mode**: Provide your own `agent` and `deps` for full control
           over the agent's behavior and configuration.

        Args:
            agent: Custom PydanticAI agent (if None, creates default basic agent)
            deps: Custom deps for agent.run() (if None, creates default with persona)
            persona: Persona for default agent (used only if deps is None)
            model: Model string for default agent (default: "openai:gpt-5-mini")
            max_turns: Maximum conversation turns before returning None
            send_as_text: If True, send text responses; if False, use TTS for audio
            tts_engine: TTS engine for audio generation (auto-created if needed)
            tts_kwargs: TTS configuration (voice, instructions)
            pre_hook: Optional pre-response hook for custom logic
            post_hook: Optional post-response hook for custom logic

        Returns:
            Configured UserSimulator instance

        Examples:
            Simple usage with defaults:
            >>> sim = UserSimulator.from_agent()

            Custom persona:
            >>> from layercode_gym import Persona
            >>> sim = UserSimulator.from_agent(
            ...     persona=Persona(
            ...         background_context="You are a busy CEO...",
            ...         intent="You want to quickly schedule a meeting"
            ...     ),
            ...     max_turns=5
            ... )

            Power user with custom agent:
            >>> from pydantic_ai import Agent
            >>> my_agent = Agent("anthropic:claude-3-5-sonnet", deps_type=MyDeps)
            >>> sim = UserSimulator.from_agent(
            ...     agent=my_agent,
            ...     deps=MyDeps(persona=..., custom_field=...)
            ... )

            Custom model with default agent:
            >>> sim = UserSimulator.from_agent(
            ...     model="anthropic:claude-3-5-sonnet",
            ...     send_as_text=True
            ... )
        """
        # Import here to avoid circular imports
        from .basic_agent import create_basic_agent, create_default_deps

        # Resolve agent: use provided or create default
        if agent is None:
            resolved_model = model or "openai:gpt-5-mini"
            agent = create_basic_agent(resolved_model)

        # Resolve deps: use provided or create default
        if deps is None:
            deps = create_default_deps(persona)

        # Create strategy with resolved agent and deps
        strategy = AgentTurnStrategy(
            agent=cast(AgentProtocol, agent),
            deps=deps,
            max_turns=max_turns,
            send_as_text=send_as_text,
            tts_engine=tts_engine,
            tts_kwargs=tts_kwargs,
            settings=settings,
        )

        return cls(strategy=strategy, pre_hook=pre_hook, post_hook=post_hook)
