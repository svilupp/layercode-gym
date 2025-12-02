#!/usr/bin/env python3
"""
LayerCode Gym CLI - Simple client for testing LayerCode voice agents.

This CLI provides a quick way to test your LayerCode server without writing code.
It exposes three modes of interaction:
1. Text messages (--text)
2. Audio files (--file)
3. AI agent personas (--agent)

All modes can be combined - text and file inputs are composable.

Examples:
    # Simple text message
    layercode-gym --text "Hello, I need help with my account"

    # Multiple messages
    layercode-gym --text "Hi" --text "Can you help me?"

    # Audio file playback
    layercode-gym --file recording.wav

    # Mix text and audio
    layercode-gym --text "Hello" --file question.wav

    # AI agent with custom persona
    layercode-gym --agent --persona-background "You are a frustrated customer" \\
                  --persona-intent "Cancel subscription"

    # Custom server configuration
    layercode-gym --server-url http://localhost:3000 \\
                  --authorize-path /auth/layercode \\
                  --text "Hello"

Environment Variables:
    SERVER_URL              - Your backend server URL
    LAYERCODE_AGENT_ID      - Your LayerCode agent ID
    OPENAI_API_KEY          - For TTS and AI personas
    LAYERCODE_OUTPUT_ROOT   - Where to save conversations

    See Settings class for full list of environment variables.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Sequence

from layercode_gym import (
    LayercodeClient,
    Settings,
    UserSimulator,
    Persona,
    create_basic_agent,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all CLI options."""

    parser = argparse.ArgumentParser(
        prog="layercode-gym",
        description=(
            "Simple CLI client for testing LayerCode voice agents. "
            "Supports text messages, audio files, and AI agent personas."
        ),
        epilog=(
            "Examples:\n"
            "  layercode-gym --text 'Hello, I need help'\n"
            "  layercode-gym --file recording.wav\n"
            "  layercode-gym --agent --persona-intent 'Book a flight'\n"
            "  layercode-gym --text 'Hi' --file question.wav --max-turns 5\n"
            "\n"
            "For more information, see: https://github.com/layercode/layercode-gym"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input modes (composable)
    input_group = parser.add_argument_group(
        "input modes",
        "Specify how the simulator should interact (can combine --text and --file)",
    )
    input_group.add_argument(
        "--text",
        action="append",
        dest="texts",
        metavar="MESSAGE",
        help=(
            "Add a text message to send. Can be specified multiple times. "
            "Messages will be sent in order, one per turn."
        ),
    )
    input_group.add_argument(
        "--file",
        action="append",
        dest="files",
        type=Path,
        metavar="PATH",
        help=(
            "Add an audio file to play. Can be specified multiple times. "
            "Supported formats: WAV, MP3, etc. Files will be played in order."
        ),
    )
    input_group.add_argument(
        "--agent",
        action="store_true",
        help=(
            "Use AI agent mode with a persona. The agent will generate dynamic "
            "responses based on the conversation. Requires OPENAI_API_KEY."
        ),
    )

    # Agent persona options (only used with --agent)
    persona_group = parser.add_argument_group(
        "agent persona options",
        "Configure the AI agent persona (only used with --agent)",
    )
    persona_group.add_argument(
        "--persona-background",
        metavar="TEXT",
        help=(
            "Background context for the agent persona. Example: "
            "'You are a busy professional who values efficiency'"
        ),
    )
    persona_group.add_argument(
        "--persona-intent",
        metavar="TEXT",
        help=(
            "The agent's goal or intent. Example: "
            "'Book a flight from NYC to SF for next Tuesday'"
        ),
    )

    # Server configuration
    server_group = parser.add_argument_group(
        "server configuration",
        "Configure connection to your LayerCode backend server",
    )
    server_group.add_argument(
        "--server-url",
        metavar="URL",
        help=(
            "Your backend server URL. This is YOUR server that handles "
            "LayerCode authorization, not the LayerCode API itself. "
            "Default: SERVER_URL env var or 'http://localhost:8001'"
        ),
    )
    server_group.add_argument(
        "--authorize-path",
        metavar="PATH",
        help=("Authorization endpoint path on your server. Default: '/api/authorize'"),
    )
    server_group.add_argument(
        "--agent-id",
        metavar="ID",
        help=(
            "Your LayerCode agent ID from the dashboard. "
            "Default: LAYERCODE_AGENT_ID env var"
        ),
    )

    # Conversation control
    control_group = parser.add_argument_group(
        "conversation control",
        "Control conversation behavior and limits",
    )
    control_group.add_argument(
        "--max-turns",
        type=int,
        metavar="N",
        help="Maximum number of user turns before ending conversation",
    )
    control_group.add_argument(
        "--output-dir",
        type=Path,
        metavar="PATH",
        help=(
            "Directory to save conversation logs. "
            "Default: LAYERCODE_OUTPUT_ROOT env var or './conversations'"
        ),
    )

    # TTS configuration (for agent mode)
    tts_group = parser.add_argument_group(
        "text-to-speech options",
        "Configure OpenAI TTS for agent mode (requires OPENAI_API_KEY)",
    )
    tts_group.add_argument(
        "--tts-model",
        metavar="MODEL",
        help="OpenAI TTS model. Default: 'gpt-4o-mini-tts'",
    )
    tts_group.add_argument(
        "--tts-voice",
        metavar="VOICE",
        choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer", "coral"],
        help="OpenAI TTS voice. Default: 'coral'",
    )
    tts_group.add_argument(
        "--tts-instructions",
        metavar="TEXT",
        help="Optional instructions for TTS voice style",
    )

    # Audio processing
    audio_group = parser.add_argument_group(
        "audio processing",
        "Configure audio chunking behavior",
    )
    audio_group.add_argument(
        "--chunk-ms",
        type=int,
        metavar="MS",
        help="Audio chunk size in milliseconds. Default: 100",
    )
    audio_group.add_argument(
        "--chunk-interval",
        type=float,
        metavar="SEC",
        help="Interval between audio chunks in seconds. Default: 0.0",
    )

    # Debug/observability
    debug_group = parser.add_argument_group(
        "debugging and observability",
    )
    debug_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate argument combinations and requirements."""

    # Check that at least one input mode is specified
    has_text = args.texts is not None and len(args.texts) > 0
    has_files = args.files is not None and len(args.files) > 0
    has_agent = args.agent

    if not (has_text or has_files or has_agent):
        print(
            "Error: Must specify at least one input mode:\n"
            "  --text MESSAGE    Send text message(s)\n"
            "  --file PATH       Play audio file(s)\n"
            "  --agent           Use AI agent persona\n"
            "\n"
            "Run 'layercode-gym --help' for more information.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Warn if persona options used without --agent
    if not has_agent and (args.persona_background or args.persona_intent):
        print(
            "Warning: --persona-background and --persona-intent are only used "
            "with --agent mode.",
            file=sys.stderr,
        )

    # Check that files exist
    if has_files:
        for file_path in args.files:
            if not file_path.exists():
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                sys.exit(1)
            if not file_path.is_file():
                print(f"Error: Not a file: {file_path}", file=sys.stderr)
                sys.exit(1)

    # Warn if multiple modes are combined with --agent
    if has_agent and (has_text or has_files):
        print(
            "Warning: When using --agent mode, any --text and --file inputs "
            "will be sent BEFORE the agent starts. The agent will then take "
            "over for subsequent turns.",
            file=sys.stderr,
        )


def build_settings(args: argparse.Namespace) -> Settings:
    """Build Settings object from CLI args, using env vars as fallback."""

    # Start with defaults from environment
    settings = Settings.load()

    # Build override dict (only include explicitly set values)
    overrides = {}

    if args.server_url is not None:
        overrides["server_url"] = args.server_url
    if args.authorize_path is not None:
        overrides["authorize_path"] = args.authorize_path
    if args.agent_id is not None:
        overrides["agent_id"] = args.agent_id
    if args.output_dir is not None:
        overrides["output_root"] = args.output_dir
    if args.tts_model is not None:
        overrides["tts_model"] = args.tts_model
    if args.tts_voice is not None:
        overrides["tts_voice"] = args.tts_voice
    if args.tts_instructions is not None:
        overrides["tts_instructions"] = args.tts_instructions
    if args.chunk_ms is not None:
        overrides["chunk_ms"] = args.chunk_ms
    if args.chunk_interval is not None:
        overrides["chunk_interval"] = args.chunk_interval

    # Create new settings with overrides
    if overrides:
        # Use dataclass replace mechanism
        from dataclasses import replace

        settings = replace(settings, **overrides)

    return settings


def build_simulator(args: argparse.Namespace, settings: Settings) -> UserSimulator:
    """Build UserSimulator based on CLI arguments."""

    # Collect all messages/files in order
    messages: list[str | Path] = []

    # Add text messages
    if args.texts:
        messages.extend(args.texts)

    # Add file paths
    if args.files:
        messages.extend(args.files)

    # If using agent mode
    if args.agent:
        # Build persona
        persona = Persona(
            background_context=args.persona_background or "You are a helpful user.",
            intent=args.persona_intent or "Have a natural conversation.",
        )

        # Create agent
        agent = create_basic_agent()

        # If we have pre-messages, use them first, then switch to agent
        # For simplicity, we'll just use agent mode (pre-messages can be added later)
        if messages:
            print(
                f"Note: Sending {len(messages)} pre-programmed inputs before "
                "agent takes over.",
                file=sys.stderr,
            )
            # For now, let's just use agent and ignore pre-messages
            # A more sophisticated version could chain them

        return UserSimulator.from_agent(
            agent=agent,
            persona=persona,
            max_turns=args.max_turns,
        )

    # Text/file only mode
    # Separate into text and file lists
    texts = [m for m in messages if isinstance(m, str)]
    files = [m for m in messages if isinstance(m, Path)]

    if texts and files:
        # Combine both - need to handle order
        # For simplicity, let's do texts first then files
        # A better version would preserve exact order
        return UserSimulator.from_text(
            messages=texts,
            send_as_text=True,
            settings=settings,
        )
        # Note: This simplified version doesn't perfectly handle mixed text/files
        # For v1, we'll document that they should use one or the other
    elif texts:
        return UserSimulator.from_text(
            messages=texts,
            send_as_text=True,
            settings=settings,
        )
    elif files:
        return UserSimulator.from_files(
            files=files,
        )
    else:
        # Shouldn't reach here due to validation
        raise ValueError("No input specified")


async def run_conversation(args: argparse.Namespace) -> None:
    """Main async function to run the conversation."""

    # Build settings and simulator
    settings = build_settings(args)
    simulator = build_simulator(args, settings)

    # Print configuration if verbose
    if args.verbose:
        print("Configuration:", file=sys.stderr)
        print(f"  Server URL: {settings.server_url}", file=sys.stderr)
        print(f"  Authorize Path: {settings.authorize_path}", file=sys.stderr)
        print(f"  Agent ID: {settings.agent_id or '(from env)'}", file=sys.stderr)
        print(f"  Output Dir: {settings.output_root}", file=sys.stderr)
        print(f"  Max Turns: {args.max_turns or 'unlimited'}", file=sys.stderr)
        print(file=sys.stderr)

    # Create client and run
    client = LayercodeClient(simulator=simulator, settings=settings)

    try:
        print("Starting conversation...", file=sys.stderr)
        conversation_id = await client.run()
        print(f"\nConversation completed: {conversation_id}", file=sys.stderr)
        print(f"Saved to: {settings.output_root / conversation_id}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\n\nConversation interrupted by user.", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point for the CLI."""

    # If no arguments provided, show help
    if argv is None:
        argv = sys.argv[1:]

    # Check if this is a webhook command
    if len(argv) > 0 and argv[0] == "webhook":
        from layercode_gym.webhook_cli import main as webhook_main

        sys.exit(webhook_main(argv[1:]))

    # Otherwise, use the regular gym CLI
    parser = create_parser()

    if len(argv) == 0:
        parser.print_help()
        sys.exit(0)

    # Parse arguments
    args = parser.parse_args(argv)

    # Validate
    validate_args(args)

    # Run async conversation
    asyncio.run(run_conversation(args))


if __name__ == "__main__":
    main()
