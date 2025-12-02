#!/usr/bin/env python
"""
Example 4: Callbacks with CriteriaJudge

This example demonstrates:
1. Turn-level callbacks (called after each assistant response)
2. Conversation-level callbacks (called when conversation ends)
3. Using CriteriaJudge for easy true/false evaluation against custom criteria
4. Using ResponseDataProcessor to let the AI "see" tool call results
5. Saving judge results to a JSON file in the conversation folder

Usage:
    uv run examples/04_callbacks_judge.py
"""

import asyncio

from layercode_gym import (
    CriteriaJudge,
    LayercodeClient,
    Settings,
    UserSimulator,
    default_data_processor,
)
from layercode_gym.models.conversation import ConversationLog, ConversationTurn


async def turn_callback(turn: ConversationTurn, log: ConversationLog) -> None:
    """Called after each turn completes.

    This is useful for monitoring progress, logging, or triggering actions.
    """
    turn_num = len(log.turns)
    print(f"\n   Turn {turn_num} completed")

    if turn.assistant_message:
        content = turn.assistant_message.content or "(audio only)"
        print(f"   Assistant: {content[:60]}{'...' if len(content) > 60 else ''}")

    if turn.user_message:
        content = turn.user_message.content or "(audio only)"
        print(f"   User: {content[:60]}{'...' if len(content) > 60 else ''}")


async def main() -> None:
    """Run a conversation with turn and conversation callbacks."""

    # Configure settings
    settings = Settings.load()

    # Create the CriteriaJudge with custom evaluation criteria
    # Each criterion should be a question that can be answered true/false
    judge = CriteriaJudge(
        criteria=[
            "Did the assistant greet the user appropriately?",
            "Did the assistant's responses stay on topic?",
            "Did the assistant provide clear and understandable responses?",
            "Did the assistant maintain a professional tone?",
        ],
        # Optional: provide additional context about the conversation's purpose
        additional_context=(
            "The user was testing a voice AI assistant to understand its capabilities. "
            "The assistant should be helpful and informative."
        ),
        # Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
        # evaluation where accuracy matters more than cost
        model="openai:gpt-5-mini",
    )

    async def conversation_callback(log: ConversationLog) -> None:
        """Called when conversation ends - run the criteria judge."""
        print("\n" + "=" * 60)
        print("Conversation ended - Running CriteriaJudge evaluation...")
        print("=" * 60)

        # Evaluate the conversation
        print("Evaluating conversation against criteria...")
        result = await judge.evaluate(log)

        # Display results
        print("\nEVALUATION RESULTS:")
        print("=" * 60)

        # Show reasoning first
        print(f"\nReasoning:\n{result.reasoning}")

        # Show individual criteria results
        print("\nCriteria Results:")
        for i, criterion in enumerate(judge.criteria):
            # Find the matching result
            cr = next(
                (r for r in result.criteria_results if r.criterion_id == i + 1),
                None,
            )
            status = "PASS" if cr and cr.passed else "FAIL"
            print(f"  [{status}] {criterion}")

        # Show overall result
        overall = "PASS" if result.overall_pass else "FAIL"
        print(f"\nOverall: {overall}")
        print("=" * 60)

        # Save results to file
        results_file = judge.save_results(
            result, log.conversation_id, settings.output_root
        )
        print(f"\nResults saved to: {results_file}")

    # Create simulator with canned messages
    simulator = UserSimulator.from_text(
        messages=[
            "Hi! I'm looking for information about your services.",
            "What can you help me with?",
            "That sounds interesting. Can you tell me more?",
            "Thanks for the information!",
        ],
        send_as_text=True,
    )

    # Create client with callbacks and data processor
    # The data_processor converts response.data events (tool calls, UI updates)
    # into text that the AI user simulator can "see" and react to
    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
        turn_callback=turn_callback,
        conversation_callback=conversation_callback,
        data_processor=default_data_processor,  # Uses XML format by default
    )

    # Run the conversation
    print("Starting conversation with callbacks and CriteriaJudge...")
    print("=" * 60)

    conversation_id = await client.run()

    print("\n" + "=" * 60)
    print("All done!")
    print(f"Results saved to: {settings.output_root / conversation_id}")
    print("   - transcript.json (conversation history)")
    print("   - judge_evaluation.json (criteria judge results)")
    print("   - conversation_mix.wav (combined audio)")
    print(f"Conversation ID: {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
