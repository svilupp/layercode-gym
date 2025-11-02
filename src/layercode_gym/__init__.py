"""Layercode Gym – utilities for simulating LayerCode voice conversations."""

from .client import LayercodeClient
from .config import Settings
from .runner import ConversationBatch, ConversationRunner
from .simulator.agent import Persona
from .simulator.base import UserSimulator
from .simulator.basic_agent import (
    BasicAgentDeps,
    create_basic_agent,
    create_default_deps,
)
from .simulator.tts import OpenAITTSEngine

__all__ = [
    "LayercodeClient",
    "Settings",
    "ConversationRunner",
    "ConversationBatch",
    "UserSimulator",
    "Persona",
    "OpenAITTSEngine",
    # For power users who want to extend the basic agent
    "create_basic_agent",
    "create_default_deps",
    "BasicAgentDeps",
]
