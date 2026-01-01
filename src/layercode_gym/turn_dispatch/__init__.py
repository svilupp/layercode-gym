"""Smart turn-taking for voice conversations.

This package provides intelligent turn-taking decisions using AI classifiers
to determine when the user should respond vs. wait for the assistant.
"""

from .protocols import SmartTurnClassifier, TurnContext, TurnDecision
from .smart_turn import SmartTurnClassifier as DefaultSmartTurnClassifier

__all__ = [
    "SmartTurnClassifier",
    "TurnContext",
    "TurnDecision",
    "DefaultSmartTurnClassifier",
]
