#!/usr/bin/env python
"""
Run All Simple Examples

This script runs all 4 simple examples in sequence with proper error handling.
Each example is run in isolation to demonstrate different features.

Usage:
    uv run python examples/run_all.py
"""

import asyncio
import sys
from pathlib import Path

# Add examples to path
sys.path.insert(0, str(Path(__file__).parent))


async def run_example(name: str, module_name: str) -> bool:
    """Run a single example and return success status."""
    print("\n" + "=" * 80)
    print(f"🚀 Running Example: {name}")
    print("=" * 80)

    try:
        # Import and run the example's main function
        module = __import__(module_name)
        await module.main()
        print(f"\n✅ {name} - SUCCESS")
        return True

    except Exception as e:
        print(f"\n❌ {name} - FAILED")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> None:
    """Run all examples in sequence."""
    print("=" * 80)
    print("🎯 LayerCode Gym - Simple Examples Suite")
    print("=" * 80)
    print("\nThis will run 5 examples demonstrating different features:")
    print("  1. Text Messages (from_text)")
    print("  2. Audio File (from_files)")
    print("  3. AI Agent with Persona (from_agent)")
    print("  4. Callbacks with LLM Judge")
    print("  5. Batch Evaluation")
    print("\nNote: Examples 3, 4, and 5 require OPENAI_API_KEY")
    print("=" * 80)

    # Track results
    results = []

    # Example 1: Text Messages
    results.append(
        (
            "Text Messages",
            await run_example("01 - Text Messages (from_text)", "01_text_messages"),
        )
    )

    # Example 2: Audio File
    results.append(
        (
            "Audio File",
            await run_example("02 - Audio File (from_files)", "02_audio_file"),
        )
    )

    # Example 3: AI Agent with Persona
    results.append(
        (
            "AI Agent with Persona",
            await run_example(
                "03 - AI Agent with Persona (from_agent)", "03_agent_persona"
            ),
        )
    )

    # Example 4: Callbacks with LLM Judge
    results.append(
        (
            "Callbacks with Judge",
            await run_example("04 - Callbacks with LLM Judge", "04_callbacks_judge"),
        )
    )

    # Example 5: Batch Evaluation
    results.append(
        (
            "Batch Evaluation",
            await run_example("05 - Batch Evaluation", "05_batch_evaluation"),
        )
    )

    # Print summary
    print("\n" + "=" * 80)
    print("📊 RESULTS SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {name}")

    print("=" * 80)
    print(f"Final Score: {passed}/{total} examples passed")
    print("=" * 80)

    if passed == total:
        print("\n🎉 All examples completed successfully!")
    else:
        print(f"\n⚠️  {total - passed} example(s) failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
