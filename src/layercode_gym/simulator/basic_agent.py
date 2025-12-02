from __future__ import annotations

"""Default agent implementation for user simulation."""

from dataclasses import dataclass
from pathlib import Path

import textprompts
from pydantic_ai import Agent, RunContext

from .agent import Persona


@dataclass
class BasicAgentDeps:
    """Default dependencies for the basic agent.

    Attributes:
        persona: User persona with background context and intent
        template: Loaded prompt template for instructions
    """

    persona: Persona
    template: textprompts.Prompt


def create_basic_agent(model: str = "openai:gpt-5-mini") -> Agent[BasicAgentDeps, str]:
    """Factory function to create the default basic agent.

    Args:
        model: Model string (e.g., "openai:gpt-5-mini", "anthropic:claude-sonnet-4-5")

    Returns:
        Configured PydanticAI agent with system prompt injection
    """
    agent: Agent[BasicAgentDeps, str] = Agent(
        model,
        deps_type=BasicAgentDeps,
        output_type=str,
    )

    @agent.system_prompt
    def build_instructions(ctx: RunContext[BasicAgentDeps]) -> str:
        """Dynamically build instructions from template + persona."""
        template = ctx.deps.template
        persona = ctx.deps.persona

        # Format the template with persona fields
        return template.prompt.format(
            background_context=persona.background_context,
            intent=persona.intent,
        )

    return agent


def load_default_template() -> textprompts.Prompt:
    """Load the default prompt template.

    Returns:
        Loaded prompt template with strict metadata validation
    """
    prompt_path = Path(__file__).parent / "prompts" / "basic_agent.txt"
    return textprompts.load_prompt(prompt_path, meta="strict")


def create_default_deps(persona: Persona | None = None) -> BasicAgentDeps:
    """Create default deps with optional persona override.

    Args:
        persona: Optional persona to use (if None, uses default persona)

    Returns:
        BasicAgentDeps with persona and loaded template
    """
    if persona is None:
        persona = Persona(
            background_context=(
                "You are a curious user interested in learning about voice AI technology."
            ),
            intent="You want to explore the capabilities of this voice assistant.",
        )

    template = load_default_template()
    return BasicAgentDeps(persona=persona, template=template)
