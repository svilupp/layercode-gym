from __future__ import annotations

"""Default agent implementation for user simulation."""

from dataclasses import dataclass
from pathlib import Path

import textprompts
from pydantic_ai import Agent, ModelRetry, RunContext

from .agent import Persona
from .protocols import AgentOutput, WaitForAssistant


# Instructions appended when wait is disabled (overrides base prompt's wait option)
WAIT_DISABLED_INSTRUCTIONS = """

NOTE: WaitForAssistant is NOT available. You must always respond with RespondToAssistant(message="...").
"""


@dataclass
class BasicAgentDeps:
    """Default dependencies for the basic agent.

    Attributes:
        persona: User persona with background context and intent
        template: Loaded prompt template for instructions
    """

    persona: Persona
    template: textprompts.Prompt


def create_basic_agent(
    model: str = "openai:gpt-5-mini",
    enable_wait_tool: bool = True,
) -> Agent[BasicAgentDeps, AgentOutput]:
    """Factory function to create the default basic agent.

    Args:
        model: Model string (e.g., "openai:gpt-5-mini", "anthropic:claude-sonnet-4-5")
        enable_wait_tool: If True, agent can return WaitForAssistant to wait
            for long-running assistant tasks. If False, agent must always respond
            with RespondToAssistant (WaitForAssistant triggers retry). Default True.

    Returns:
        Configured PydanticAI agent with system prompt injection.
        Output type is AgentOutput (RespondToAssistant | WaitForAssistant).
    """
    agent: Agent[BasicAgentDeps, AgentOutput] = Agent(
        model,
        deps_type=BasicAgentDeps,
        output_type=AgentOutput,
        retries=3,  # Enable retries for validation/model retry errors
    )

    @agent.system_prompt
    def build_instructions(ctx: RunContext[BasicAgentDeps]) -> str:
        """Dynamically build instructions from template + persona."""
        template = ctx.deps.template
        persona = ctx.deps.persona

        # Format the template with persona fields
        # Base prompt includes wait instructions - they're part of the core behavior
        base = template.prompt.format(
            background_context=persona.background_context,
            intent=persona.intent,
        )

        # When wait is disabled, append override notice
        if not enable_wait_tool:
            return base + WAIT_DISABLED_INSTRUCTIONS
        return base

    # When wait is disabled, reject WaitForAssistant and trigger retry
    if not enable_wait_tool:

        @agent.output_validator
        def reject_wait(
            ctx: RunContext[BasicAgentDeps], output: AgentOutput
        ) -> AgentOutput:
            """Reject WaitForAssistant when wait is disabled, triggering model retry."""
            if isinstance(output, WaitForAssistant):
                raise ModelRetry(
                    "WaitForAssistant is not available in this context. "
                    "You must respond with RespondToAssistant(message=...) instead."
                )
            return output

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
