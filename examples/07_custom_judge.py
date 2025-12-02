#!/usr/bin/env python
"""
Example 7: Custom Judge with PydanticAI

This example demonstrates how to create a custom conversation judge
using your own PydanticAI agent with a custom output type.

Use this approach when you need:
- Custom evaluation metrics beyond true/false criteria
- Numerical scores or ratings
- Domain-specific output structures

Usage:
    uv run examples/07_custom_judge.py
"""

import asyncio

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from layercode_gym import LayercodeClient, Settings, UserSimulator
from layercode_gym.models.conversation import ConversationLog, ConversationTurn


# Custom output type for our judge
class ConversationEvaluation(BaseModel):
    """Strict pass/fail evaluation of a voice assistant's conversational quality.

    Evaluate the ASSISTANT's performance (not the user). Be strict - only pass
    if the criterion is fully met with no issues.
    """

    greeted_appropriately: bool = Field(
        description=(
            "PASS only if: Assistant greeted the user within the first response "
            "AND the greeting was contextually appropriate. "
            "FAIL if: No greeting, delayed greeting, or inappropriate tone."
        ),
    )
    answered_all_questions: bool = Field(
        description=(
            "PASS only if: Every question the user asked received a direct, "
            "relevant answer. FAIL if: Any question was ignored, deflected, "
            "or answered with irrelevant information."
        ),
    )
    no_hallucinations: bool = Field(
        description=(
            "PASS only if: All factual claims made by the assistant are verifiable "
            "from the conversation context or are appropriately hedged. "
            "FAIL if: Assistant made up information or stated uncertain things as facts."
        ),
    )
    summary: str = Field(
        description="1-2 sentence explanation of any failures. If all passed, say 'All criteria met.'"
    )


# Create custom PydanticAI judge agent
# Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
# evaluation where accuracy matters more than cost
custom_judge = Agent(
    "openai:gpt-5-mini",
    output_type=ConversationEvaluation,
    system_prompt=(
        "You evaluate voice assistant conversations with strict pass/fail criteria. "
        "Evaluate the ASSISTANT only (not the user). "
        "Be strict - only mark pass if the criterion is fully met."
    ),
)


async def evaluate_with_custom_judge(log: ConversationLog) -> ConversationEvaluation:
    """Run custom evaluation on a conversation."""
    # Build transcript
    lines = []
    for i, turn in enumerate(log.turns):
        if turn.assistant_message:
            lines.append(
                f"[{i + 1}] ASSISTANT: {turn.assistant_message.content or '(audio)'}"
            )
        if turn.user_message:
            lines.append(f"[{i + 1}] USER: {turn.user_message.content or '(audio)'}")

    transcript = "\n".join(lines)
    result = await custom_judge.run(f"Evaluate this conversation:\n\n{transcript}")
    return result.output


async def turn_callback(turn: ConversationTurn, log: ConversationLog) -> None:
    """Simple turn logger."""
    n = len(log.turns)
    if turn.assistant_message:
        print(f"   [{n}] Assistant: {turn.assistant_message.content or '(audio)'}")
    if turn.user_message:
        print(f"   [{n}] User: {turn.user_message.content or '(audio)'}")


async def main() -> None:
    """Run conversation with custom judge evaluation."""
    settings = Settings.load()

    async def conversation_callback(log: ConversationLog) -> None:
        """Run custom judge when conversation ends."""
        print("\n" + "=" * 60)
        print("Running custom judge evaluation...")

        result = await evaluate_with_custom_judge(log)

        print("\nCustom Evaluation Results:")
        print(
            f"  Greeted appropriately:   {'PASS' if result.greeted_appropriately else 'FAIL'}"
        )
        print(
            f"  Answered all questions:  {'PASS' if result.answered_all_questions else 'FAIL'}"
        )
        print(
            f"  No hallucinations:       {'PASS' if result.no_hallucinations else 'FAIL'}"
        )
        all_passed = all(
            [
                result.greeted_appropriately,
                result.answered_all_questions,
                result.no_hallucinations,
            ]
        )
        print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
        print(f"Summary: {result.summary}")
        print("=" * 60)

    simulator = UserSimulator.from_text(
        messages=[
            "Hi, can you help me?",
            "What services do you offer?",
            "Thanks!",
        ],
        send_as_text=True,
    )

    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
        turn_callback=turn_callback,
        conversation_callback=conversation_callback,
    )

    print("Custom Judge Example")
    print("=" * 60)
    await client.run()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
