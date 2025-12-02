"""Layercode Gym – utilities for simulating LayerCode voice conversations."""

from .agents.judge import CriteriaJudge, CriterionResult, JudgeOutput
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
from .simulator.data_processor import default_data_processor, XMLDataProcessor
from .simulator.protocols import ResponseDataProcessor
from .simulator.tts import OpenAITTSEngine

__all__ = [
    # Core client and config
    "LayercodeClient",
    "Settings",
    # Runners
    "ConversationRunner",
    "ConversationBatch",
    # User simulation
    "UserSimulator",
    "Persona",
    "OpenAITTSEngine",
    # Response data processing
    "ResponseDataProcessor",
    "default_data_processor",
    "XMLDataProcessor",
    # Evaluation / Judging
    "CriteriaJudge",
    "CriterionResult",
    "JudgeOutput",
    # For power users who want to extend the basic agent
    "create_basic_agent",
    "create_default_deps",
    "BasicAgentDeps",
]
