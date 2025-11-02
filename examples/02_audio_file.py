#!/usr/bin/env python
"""
Example 2: Audio File with from_files()

This example shows how to use pre-recorded audio files as a user simulator.
The simulator will send the intro audio file and then end the conversation.

Usage:
    uv run examples/02_audio_file.py
"""

import asyncio
from pathlib import Path

from layercode_gym import LayercodeClient, Settings, UserSimulator


async def main() -> None:
    """Run a simple conversation with a pre-recorded audio file."""

    # Configure settings
    settings = Settings.load()

    # Path to the audio file
    project_root = Path(__file__).parent
    audio_file = project_root / "data" / "intro-example-8000hz.wav"

    if not audio_file.exists():
        print(f"❌ Error: Audio file not found at {audio_file}")
        print("\n💡 To use this example:")
        print("   1. Create a 'data' folder in the project root")
        print("   2. Add an audio file: data/intro-example-8000hz.wav")
        print("   3. Or modify the audio_file path above to point to your audio file")
        return

    # Create simulator with audio file
    # The audio file will be sent as-is to the LayerCode server
    simulator = UserSimulator.from_files(
        files=[audio_file],  # Can provide multiple audio files
    )

    # Create client
    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
    )

    # Run the conversation
    print("🎯 Starting conversation with audio file...")
    print(f"🔊 Audio file: {audio_file.name}")
    print("=" * 60)

    conversation_id = await client.run()

    print("=" * 60)
    print("✅ Conversation complete!")
    print(f"📁 Results saved to: {settings.output_root / conversation_id}")
    print(f"💬 Conversation ID: {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
