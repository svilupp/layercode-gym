#!/usr/bin/env python
"""
Example 4: Callbacks with LLM-as-Judge

This example demonstrates:
1. Turn-level callbacks (called after each assistant response)
2. Conversation-level callbacks (called when conversation ends)
3. An LLM judge that evaluates the assistant's performance on 5 rubrics
4. Saving judge results to a JSON file in the conversation folder

Usage:
    uv run examples/04_callbacks_judge.py
"""

import asyncio
import json
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent

from layercode_gym import LayercodeClient, Settings, UserSimulator
from layercode_gym.models.conversation import ConversationLog, ConversationTurn


# Define the rubric output structure
class ConversationRubric(BaseModel):
    """Rubrics for evaluating the assistant's conversational quality."""

    clarity: bool  # Were responses clear and easy to understand?
    relevance: bool  # Did responses address the user's questions?
    helpfulness: bool  # Did responses provide useful information?
    professionalism: bool  # Was the tone appropriate and professional?
    engagement: bool  # Did responses encourage further interaction?

    # Additional context
    overall_score: float  # 0-1 score
    feedback: str  # Brief explanation of the ratings


class ConversationJudge:
    """LLM-as-Judge for evaluating conversation quality."""

    def __init__(self) -> None:
        """Initialize the judge with a PydanticAI agent."""
        self.agent: Agent[None, ConversationRubric] = Agent(
            "openai:gpt-5-mini",
            result_type=ConversationRubric,
            system_prompt=(
                "You are an expert evaluator of conversational AI systems. "
                "Evaluate the ASSISTANT's performance (not the user's messages) based on these rubrics:\n\n"
                "1. CLARITY: Were the assistant's responses clear and easy to understand?\n"
                "2. RELEVANCE: Did the assistant address the user's questions and needs?\n"
                "3. HELPFULNESS: Did the assistant provide useful, actionable information?\n"
                "4. PROFESSIONALISM: Was the tone appropriate and professional?\n"
                "5. ENGAGEMENT: Did the assistant encourage continued interaction?\n\n"
                "Provide honest, objective ratings. Return true/false for each rubric, "
                "an overall score (0-1), and brief feedback explaining your assessment."
            ),
        )

    async def evaluate(self, log: ConversationLog) -> ConversationRubric:
        """Evaluate a conversation and return rubric scores."""

        # Extract conversation transcript
        transcript_parts = []
        for i, turn in enumerate(log.turns):
            if turn.assistant_message:
                transcript_parts.append(
                    f"[Turn {i}] ASSISTANT: {turn.assistant_message.content or '(audio only)'}"
                )
            if turn.user_message:
                transcript_parts.append(
                    f"[Turn {i}] USER: {turn.user_message.content or '(audio only)'}"
                )

        transcript = "\n".join(transcript_parts)

        # Build evaluation prompt
        prompt = f"""Evaluate this conversation:

{transcript}

Focus ONLY on the ASSISTANT's responses. Rate each rubric and provide overall feedback."""

        # Run the agent
        result = await self.agent.run(prompt)
        return result.data

    def save_results(
        self, rubric: ConversationRubric, conversation_id: str, output_root: Path
    ) -> Path:
        """Save judge results to JSON file in the conversation folder."""
        conversation_dir = output_root / conversation_id
        results_file = conversation_dir / "judge_evaluation.json"

        results = {
            "rubrics": {
                "clarity": rubric.clarity,
                "relevance": rubric.relevance,
                "helpfulness": rubric.helpfulness,
                "professionalism": rubric.professionalism,
                "engagement": rubric.engagement,
            },
            "overall_score": rubric.overall_score,
            "feedback": rubric.feedback,
        }

        results_file.write_text(json.dumps(results, indent=2))
        return results_file


async def turn_callback(turn: ConversationTurn, log: ConversationLog) -> None:
    """Called after each turn completes.

    This is useful for monitoring progress, logging, or triggering actions.
    """
    turn_num = len(log.turns)
    print(f"\n📍 Turn {turn_num} completed")

    if turn.assistant_message:
        content = turn.assistant_message.content or "(audio only)"
        print(f"   🤖 Assistant: {content[:60]}{'...' if len(content) > 60 else ''}")

    if turn.user_message:
        content = turn.user_message.content or "(audio only)"
        print(f"   👤 User: {content[:60]}{'...' if len(content) > 60 else ''}")


async def conversation_callback(log: ConversationLog) -> None:
    """Called when conversation ends.

    This is where we run the LLM judge to evaluate the conversation.
    """
    print("\n" + "=" * 60)
    print("🏁 Conversation ended - Running LLM Judge evaluation...")
    print("=" * 60)

    # Create judge
    judge = ConversationJudge()

    # Evaluate the conversation
    print("⏳ Evaluating conversation quality...")
    rubric = await judge.evaluate(log)

    # Display results
    print("\n📊 EVALUATION RESULTS:")
    print("=" * 60)
    print(f"✓ Clarity:          {'✅ PASS' if rubric.clarity else '❌ FAIL'}")
    print(f"✓ Relevance:        {'✅ PASS' if rubric.relevance else '❌ FAIL'}")
    print(f"✓ Helpfulness:      {'✅ PASS' if rubric.helpfulness else '❌ FAIL'}")
    print(f"✓ Professionalism:  {'✅ PASS' if rubric.professionalism else '❌ FAIL'}")
    print(f"✓ Engagement:       {'✅ PASS' if rubric.engagement else '❌ FAIL'}")
    print(f"\n📈 Overall Score: {rubric.overall_score:.2f}")
    print(f"\n💬 Feedback: {rubric.feedback}")
    print("=" * 60)

    # Save results
    settings = Settings.load()
    results_file = judge.save_results(rubric, log.conversation_id, settings.output_root)
    print(f"\n💾 Results saved to: {results_file}")


async def main() -> None:
    """Run a conversation with turn and conversation callbacks."""

    # Configure settings
    settings = Settings.load()

    # Create simulator with canned messages
    simulator = UserSimulator.from_text(
        messages=[
            "Hi! I'm looking for information about your AI voice agents.",
            "What are the main features?",
            "How much does it cost?",
            "Thanks, that's helpful!",
        ],
        send_as_text=True,
    )

    # Create client with callbacks
    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
        turn_callback=turn_callback,  # Called after each turn
        conversation_callback=conversation_callback,  # Called at end
    )

    # Run the conversation
    print("🎯 Starting conversation with callbacks and LLM judge...")
    print("=" * 60)

    conversation_id = await client.run()

    print("\n" + "=" * 60)
    print("✅ All done!")
    print(f"📁 Results saved to: {settings.output_root / conversation_id}")
    print("   - transcript.json (conversation history)")
    print("   - judge_evaluation.json (LLM judge results)")
    print("   - conversation_mix.wav (combined audio)")
    print(f"💬 Conversation ID: {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
