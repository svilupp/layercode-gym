"""Simulator components for generating user responses."""

from .agent import AgentProtocol, AgentTurnStrategy, Persona
from .base import UserSimulator
from .protocols import (
    AgentOutput,
    RespondToAssistant,
    ResponseDataProcessor,
    SimulatorHook,
    TTSEngineProtocol,
    UserRequest,
    UserResponse,
    UserSimulatorProtocol,
    WaitContext,
    WaitForAssistant,
)
from .tts import OpenAITTSEngine

__all__ = [
    # Simulator facade
    "UserSimulator",
    "Persona",
    # Protocols
    "UserSimulatorProtocol",
    "TTSEngineProtocol",
    "SimulatorHook",
    "ResponseDataProcessor",
    "AgentProtocol",
    # Data types
    "UserRequest",
    "UserResponse",
    "WaitContext",
    # Agent output types
    "AgentOutput",
    "RespondToAssistant",
    "WaitForAssistant",
    # Strategy (for power users)
    "AgentTurnStrategy",
    # TTS
    "OpenAITTSEngine",
]
