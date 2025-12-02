#!/usr/bin/env python
"""
Example 6: Outdoor Shop Agent Evaluation with Custom Data Processor

This example demonstrates:
1. Running against the experimental layercode-create-app outdoor_shop agent
2. Using CriteriaJudge to evaluate based on the agent's actual prompt requirements
3. Custom ResponseDataProcessor for rendering products in a user-friendly way
4. Testing response.data streaming for product catalogs, orders, and policies

Prerequisites:
    Start the outdoor_shop agent server in another terminal:

    cd /path/to/layercode-create-app
    uvx --from /path/to/layercode-create-app layercode-create-app run --agent outdoor_shop --tunnel

    Or using a local path:
    uvx --from . layercode-create-app run --agent outdoor_shop --tunnel

Usage:
    uv run examples/06_outdoor_shop_eval.py
"""

import asyncio
from typing import Any

from layercode_gym import (
    CriteriaJudge,
    LayercodeClient,
    Persona,
    Settings,
    UserSimulator,
)
from layercode_gym.models.conversation import ConversationLog, ConversationTurn


def outdoor_shop_data_processor(data: dict[str, Any]) -> str:
    """Custom data processor for outdoor shop response.data events.

    Converts tool call results into human-readable text that the AI user
    simulator can "see" and respond to naturally.

    The outdoor_shop agent emits structured data for:
    - search_products: Product catalog results
    - lookup_order: Order tracking information
    - get_policy: Store policy details
    """
    tool = data.get("tool", "")
    payload = data.get("payload", {})

    if tool == "search_products":
        return _format_product_results(payload)
    elif tool == "lookup_order":
        return _format_order_info(data, payload)
    elif tool == "get_policy":
        return _format_policy_info(data, payload)
    else:
        # Fallback: show raw tool and event type
        event_type = data.get("event_type", "unknown")
        return f"[{tool}:{event_type}]"


def _format_product_results(payload: dict[str, Any]) -> str:
    """Format product search results for the user simulator."""
    products = payload.get("products", [])
    query = payload.get("query", "")
    count = payload.get("results_count", len(products))

    if not products:
        return f"[SCREEN: No products found for '{query}']"

    lines = [f"[SCREEN: {count} product(s) found for '{query}']"]

    for p in products:
        name = p.get("name", "Unknown")
        brand = p.get("brand", "")

        # Pricing
        pricing = p.get("pricing", {})
        regular = pricing.get("regular_price", 0)
        sale = pricing.get("sale_price")
        price_str = f"${sale:.2f} (was ${regular:.2f})" if sale else f"${regular:.2f}"

        # Availability
        avail = p.get("availability", {})
        stock_status = "In Stock" if avail.get("in_stock") else "Out of Stock"

        # Key specs
        specs = p.get("specifications", {})
        season = specs.get("season_rating", "")
        capacity = specs.get("capacity")

        # Ratings
        ratings = p.get("ratings", {})
        rating = ratings.get("overall", 0)
        reviews = ratings.get("review_count", 0)

        # Build product line
        spec_parts = []
        if capacity:
            spec_parts.append(f"{capacity}P")
        if season:
            spec_parts.append(season)
        spec_str = ", ".join(spec_parts) if spec_parts else ""

        lines.append(
            f"  - {name} ({brand}): {price_str} | {stock_status} | "
            f"{rating:.1f}/5 ({reviews} reviews)"
            + (f" | {spec_str}" if spec_str else "")
        )

    return "\n".join(lines)


def _format_order_info(data: dict[str, Any], payload: dict[str, Any]) -> str:
    """Format order lookup results for the user simulator."""
    found = data.get("found", payload.get("found", False))
    order_num = data.get("order_number", "")

    if not found:
        return f"[SCREEN: Order {order_num} not found]"

    order = payload.get("order", {})
    status = order.get("status", "unknown")
    totals = order.get("totals", {})
    shipping = order.get("shipping", {})
    items = order.get("items", [])

    # Format items
    item_names = [item.get("name", "Item") for item in items]
    items_str = ", ".join(item_names[:3])
    if len(item_names) > 3:
        items_str += f" (+{len(item_names) - 3} more)"

    # Delivery estimate
    est = shipping.get("estimated_delivery", {})
    delivery_str = ""
    if est:
        earliest = est.get("earliest", "")
        latest = est.get("latest", "")
        delivery_str = f"Est. delivery: {earliest} - {latest}"

    # Tracking
    tracking = shipping.get("tracking_number", "")
    tracking_str = f"Tracking: {tracking}" if tracking else "No tracking yet"

    total = totals.get("total", 0)

    return (
        f"[SCREEN: Order {order_num}]\n"
        f"  Status: {status.upper()}\n"
        f"  Items: {items_str}\n"
        f"  Total: ${total:.2f}\n"
        f"  {tracking_str}\n"
        f"  {delivery_str}"
    )


def _format_policy_info(data: dict[str, Any], payload: dict[str, Any]) -> str:
    """Format policy information for the user simulator."""
    found = data.get("found", payload.get("found", False))
    policy_type = data.get("policy_type", "")

    if not found:
        available = payload.get("available_policies", [])
        return f"[SCREEN: Policy '{policy_type}' not found. Available: {', '.join(available)}]"

    policy = payload.get("policy", {})
    name = policy.get("name", policy_type)
    summary = policy.get("summary", "")

    return f"[SCREEN: {name}]\n  {summary}"


# Evaluation criteria derived from outdoor_shop.txt prompt
OUTDOOR_SHOP_CRITERIA = [
    # Response length (CRITICAL in the prompt)
    "Did the assistant keep responses to 1-2 sentences maximum?",
    # Tone requirements
    "Did the assistant maintain a neutral, factual tone without enthusiasm or sales language?",
    # Brand neutrality (STRICT in the prompt)
    "Did the assistant avoid making positive or negative comments about any brands?",
    # Progressive disclosure
    "Did the assistant provide only the key fact first without volunteering extra information?",
    # Tool usage
    "Did the assistant appropriately use available tools (search_products, lookup_order, get_policy) when needed?",
]


async def turn_callback(turn: ConversationTurn, log: ConversationLog) -> None:
    """Monitor each turn for debugging."""
    turn_num = len(log.turns)
    print(f"\n   Turn {turn_num}")

    if turn.assistant_message:
        content = turn.assistant_message.content or "(audio only)"
        # Show full response to verify length constraint
        print(f"   Assistant: {content}")

    if turn.user_message:
        content = turn.user_message.content or "(audio only)"
        print(f"   User: {content[:80]}{'...' if len(content) > 80 else ''}")


async def main() -> None:
    """Run outdoor shop evaluation with custom data processor and criteria judge."""

    # Configure settings
    settings = Settings.load()

    # Create the CriteriaJudge with criteria derived from outdoor_shop.txt prompt
    # The additional_context provides key reference examples from the agent's actual prompt
    judge = CriteriaJudge(
        criteria=OUTDOOR_SHOP_CRITERIA,
        additional_context=(
            "Reference examples from the agent's prompt:\n"
            "GOOD response: 'The CloudLite 2P is $379, rated 3-season. Want specs?'\n"
            "BAD response: 'The CloudLite 2P tent is currently on sale for $379.99, "
            "reduced from $449.99. It's a 3-season tent weighing 2 lbs 4 oz...'\n\n"
            "Forbidden phrases: 'great', 'excellent', 'best-seller', 'known for quality', "
            "'Great news, it's in stock!'"
        ),
        # Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
        # evaluation where accuracy matters more than cost
        model="openai:gpt-5-mini",
    )

    async def conversation_callback(log: ConversationLog) -> None:
        """Run criteria evaluation when conversation ends."""
        print("\n" + "=" * 70)
        print("Conversation ended - Running CriteriaJudge evaluation...")
        print("=" * 70)

        result = await judge.evaluate(log)

        print("\nEVALUATION RESULTS (based on outdoor_shop.txt prompt):")
        print("=" * 70)

        print(f"\nReasoning:\n{result.reasoning}")

        print("\nCriteria Results:")
        for i, criterion in enumerate(OUTDOOR_SHOP_CRITERIA):
            cr = next(
                (r for r in result.criteria_results if r.criterion_id == i + 1),
                None,
            )
            status = "PASS" if cr and cr.passed else "FAIL"
            print(f"  [{status}] {criterion}")

        overall = "PASS" if result.overall_pass else "FAIL"
        print(f"\nOverall: {overall}")
        print("=" * 70)

        results_file = judge.save_results(
            result, log.conversation_id, settings.output_root
        )
        print(f"\nResults saved to: {results_file}")

    # Create AI-driven user simulator with a shopping persona
    persona = Persona(
        background_context=(
            "You are a customer interested in buying outdoor gear for an upcoming "
            "backpacking trip. You're looking for a lightweight tent and want to "
            "know about pricing and specifications."
        ),
        intent=(
            "Ask about tents, get pricing information, and maybe ask a follow-up "
            "question about specifications. Keep your questions natural and concise."
        ),
    )

    simulator = UserSimulator.from_agent(
        persona=persona,
        max_turns=4,  # A few turns to test tool usage and response length
        send_as_text=True,
    )

    # Create client with custom data processor
    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
        turn_callback=turn_callback,
        conversation_callback=conversation_callback,
        data_processor=outdoor_shop_data_processor,  # Custom processor for products
    )

    print("Outdoor Shop Agent Evaluation")
    print("=" * 70)
    print("Testing against: outdoor_shop agent (Nimbus Gear Trail Guide)")
    print("Data Processor: Custom product/order/policy formatter")
    print("Judge Criteria: 5 criteria from outdoor_shop.txt prompt")
    print("=" * 70)
    print("\nEnsure the outdoor_shop server is running:")
    print("  uvx --from /path/to/layercode-create-app layercode-create-app run \\")
    print("      --agent outdoor_shop --tunnel")
    print("=" * 70)

    conversation_id = await client.run()

    print("\n" + "=" * 70)
    print("Evaluation complete!")
    print(f"Results saved to: {settings.output_root / conversation_id}")
    print("   - transcript.json (conversation history)")
    print("   - judge_evaluation.json (criteria evaluation results)")
    print("   - conversation_mix.wav (combined audio)")
    print(f"Conversation ID: {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
