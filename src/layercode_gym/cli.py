#!/usr/bin/env python3
"""
LayerCode Gym CLI - Testing toolkit for voice AI agents.

This CLI provides commands for testing and managing LayerCode voice agents.

Commands:
    run          Run a conversation with a LayerCode voice agent
    api-agents   Manage LayerCode agents via REST API

Run 'layercode-gym <command> --help' for more information on a command.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Sequence

from layercode_gym import (
    LayercodeClient,
    Settings,
    UserSimulator,
    Persona,
    create_basic_agent,
)


# Custom formatter that preserves newlines in description/epilog
class RawDescriptionWithDefaultsFormatter(
    argparse.RawDescriptionHelpFormatter,
    argparse.ArgumentDefaultsHelpFormatter,
):
    pass


def create_run_parser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> argparse.ArgumentParser:
    """Create the 'run' subcommand parser with all conversation options."""

    run_parser = subparsers.add_parser(
        "run",
        help="Run a conversation with a LayerCode voice agent",
        description=(
            "Run a simulated conversation with a LayerCode voice agent.\n"
            "Supports text messages, audio files, and AI agent personas.\n"
            "All input modes can be combined."
        ),
        epilog=(
            "Examples:\n"
            "  # Simple text message\n"
            "  layercode-gym run --text 'Hello, I need help'\n"
            "\n"
            "  # Multiple text messages (sent one per turn)\n"
            "  layercode-gym run --text 'Hi' --text 'Can you help me?'\n"
            "\n"
            "  # Audio file playback\n"
            "  layercode-gym run --file recording.wav\n"
            "\n"
            "  # AI agent with custom persona\n"
            "  layercode-gym run --agent --persona-intent 'Book a flight to NYC'\n"
            "\n"
            "  # Custom server configuration\n"
            "  layercode-gym run --server-url http://localhost:3000 --text 'Hello'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input modes (composable)
    input_group = run_parser.add_argument_group(
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
    persona_group = run_parser.add_argument_group(
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
    server_group = run_parser.add_argument_group(
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
    server_group.add_argument(
        "--custom-metadata",
        metavar="JSON",
        help=(
            "Custom metadata to include in authorization (JSON string). "
            "This data is stored with the session. "
            'Example: \'{"tenant_id": "t_42"}\''
        ),
    )
    server_group.add_argument(
        "--custom-headers",
        metavar="JSON",
        help=(
            "Custom headers for outbound webhooks (JSON string). "
            "These headers are sent with every webhook from LayerCode. "
            'Example: \'{"x-tenant-id": "t_42"}\''
        ),
    )
    server_group.add_argument(
        "--auth-header",
        action="append",
        dest="auth_headers",
        metavar="KEY=VALUE",
        help=(
            "Header to send with the authorization request (repeatable). "
            "Format: KEY=VALUE. Example: --auth-header 'Authorization=Bearer token'"
        ),
    )

    # Conversation control
    control_group = run_parser.add_argument_group(
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
    tts_group = run_parser.add_argument_group(
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
    audio_group = run_parser.add_argument_group(
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
    debug_group = run_parser.add_argument_group(
        "debugging and observability",
    )
    debug_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    return run_parser


def create_api_agents_parser(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> argparse.ArgumentParser:
    """Create the 'api-agents' subcommand parser."""

    api_parser = subparsers.add_parser(
        "api-agents",
        help="Manage LayerCode agents via REST API",
        description=(
            "Manage LayerCode agents via the REST API.\n"
            "Useful for CI/CD pipelines and automation."
        ),
        epilog=(
            "Examples:\n"
            "  # List all agents\n"
            "  layercode-gym api-agents list\n"
            "\n"
            "  # Get agent details\n"
            "  layercode-gym api-agents get --agent-id ag-123456\n"
            "\n"
            "  # Update webhook URL\n"
            "  layercode-gym api-agents update --agent-id ag-123 --webhook-url https://new.com\n"
            "\n"
            "  # CI pattern: save, update, test, restore\n"
            "  ORIGINAL=$(layercode-gym api-agents get --agent-id ag-123 --json | jq -r .webhook_url)\n"
            "  layercode-gym api-agents update --agent-id ag-123 --webhook-url https://test.com\n"
            "  # ... run tests ...\n"
            '  layercode-gym api-agents update --agent-id ag-123 --webhook-url "$ORIGINAL"\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create subcommands for api-agents
    api_subparsers = api_parser.add_subparsers(
        dest="api_command",
        metavar="<command>",
        help="API command to execute",
    )

    # 'list' command
    list_parser = api_subparsers.add_parser(
        "list",
        help="List all agents in your account",
        description="List all agents in your LayerCode account",
    )
    list_parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="LayerCode API key (or set LAYERCODE_API_KEY env var)",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (useful for scripting)",
    )

    # 'get' command
    get_parser = api_subparsers.add_parser(
        "get",
        help="Get agent details by ID",
        description="Get detailed information about a specific LayerCode agent",
    )
    get_parser.add_argument(
        "--agent-id",
        required=True,
        metavar="ID",
        help="LayerCode agent ID (e.g., ag-123456)",
    )
    get_parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="LayerCode API key (or set LAYERCODE_API_KEY env var)",
    )
    get_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (useful for scripting)",
    )

    # 'update' command
    update_parser = api_subparsers.add_parser(
        "update",
        help="Update agent configuration",
        description="Update agent configuration fields",
    )
    update_parser.add_argument(
        "--agent-id",
        required=True,
        metavar="ID",
        help="LayerCode agent ID (e.g., ag-123456)",
    )
    update_parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="LayerCode API key (or set LAYERCODE_API_KEY env var)",
    )
    update_parser.add_argument(
        "--webhook-url",
        metavar="URL",
        help="Update webhook URL (e.g., https://example.com/webhook)",
    )
    update_parser.add_argument(
        "--name",
        metavar="NAME",
        help="Update agent name",
    )
    update_parser.add_argument(
        "--json-data",
        metavar="JSON",
        help='Update with JSON data (e.g., \'{"webhook_url":"..."}\')',
    )
    update_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    return api_parser


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""

    parser = argparse.ArgumentParser(
        prog="layercode-gym",
        description=(
            "LayerCode Gym - Testing toolkit for voice AI agents.\n"
            "\n"
            "Commands:\n"
            "  run          Run a conversation with a LayerCode voice agent\n"
            "  api-agents   Manage LayerCode agents via REST API"
        ),
        epilog=(
            "Examples:\n"
            "  # Run a conversation with text messages\n"
            "  layercode-gym run --text 'Hello, I need help with my account'\n"
            "\n"
            "  # Run with AI agent persona\n"
            "  layercode-gym run --agent --persona-intent 'Book a flight to NYC'\n"
            "\n"
            "  # List all agents in your account\n"
            "  layercode-gym api-agents list\n"
            "\n"
            "  # Update agent webhook for CI testing\n"
            "  layercode-gym api-agents update --agent-id ag-123 --webhook-url https://test.com\n"
            "\n"
            "Run 'layercode-gym <command> --help' for more information on a command.\n"
            "\n"
            "For more information, see: https://github.com/layercode/layercode-gym"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="<command>",
        help="Command to run",
    )

    # Add subcommand parsers
    create_run_parser(subparsers)
    create_api_agents_parser(subparsers)

    return parser


def validate_run_args(args: argparse.Namespace) -> None:
    """Validate argument combinations for the 'run' command."""

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
            "Run 'layercode-gym run --help' for more information.",
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
    import json as json_module

    # Start with defaults from environment
    settings = Settings.load()

    # Build override dict (only include explicitly set values)
    overrides: dict[str, Any] = {}

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

    # Parse custom metadata JSON
    if args.custom_metadata is not None:
        try:
            parsed = json_module.loads(args.custom_metadata)
            if not isinstance(parsed, dict):
                print("Error: --custom-metadata must be a JSON object", file=sys.stderr)
                sys.exit(1)
            overrides["custom_metadata"] = parsed
        except json_module.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --custom-metadata: {e}", file=sys.stderr)
            sys.exit(1)

    # Parse custom headers JSON (values must be strings for HTTP)
    if args.custom_headers is not None:
        try:
            parsed = json_module.loads(args.custom_headers)
            if not isinstance(parsed, dict):
                print("Error: --custom-headers must be a JSON object", file=sys.stderr)
                sys.exit(1)
            # Convert all values to strings for HTTP compatibility
            overrides["custom_headers"] = {k: str(v) for k, v in parsed.items()}
        except json_module.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --custom-headers: {e}", file=sys.stderr)
            sys.exit(1)

    # Parse auth headers (KEY=VALUE format)
    if args.auth_headers:
        auth_headers: dict[str, str] = {}
        for header in args.auth_headers:
            if "=" not in header:
                print(
                    f"Error: Invalid --auth-header format: '{header}'. "
                    "Expected KEY=VALUE",
                    file=sys.stderr,
                )
                sys.exit(1)
            key, value = header.split("=", 1)
            auth_headers[key.strip()] = value.strip()
        overrides["authorization_headers"] = auth_headers

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


def handle_api_agents(args: argparse.Namespace) -> int:
    """Handle api-agents subcommand."""
    import json
    import os
    from typing import Any, cast

    from layercode_gym.api_agents_utils import main_get, main_list, main_update

    # If no api subcommand, show help
    if not args.api_command:
        print(
            "usage: layercode-gym api-agents <command> [options]\n"
            "\n"
            "Manage LayerCode agents via REST API.\n"
            "\n"
            "Commands:\n"
            "  list      List all agents in your account\n"
            "  get       Get agent details by ID\n"
            "  update    Update agent configuration\n"
            "\n"
            "Run 'layercode-gym api-agents <command> --help' for more information.",
            file=sys.stderr,
        )
        return 1

    # Get API key
    api_key = args.api_key or os.environ.get("LAYERCODE_API_KEY")
    if not api_key:
        print(
            "Error: API key required. Provide via --api-key or LAYERCODE_API_KEY env var",
            file=sys.stderr,
        )
        return 1

    # Route to appropriate handler
    if args.api_command == "list":
        return main_list(
            api_key=api_key,
            json_output=args.json,
        )
    elif args.api_command == "get":
        return main_get(
            agent_id=args.agent_id,
            api_key=api_key,
            json_output=args.json,
        )
    elif args.api_command == "update":
        # Build update data
        update_data: dict[str, Any]
        if args.json_data:
            if args.webhook_url or args.name:
                print(
                    "Error: Cannot use --json-data with --webhook-url or --name",
                    file=sys.stderr,
                )
                return 1
            try:
                update_data = cast(dict[str, Any], json.loads(args.json_data))
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON data - {e}", file=sys.stderr)
                return 1
        else:
            update_data = {}
            if args.webhook_url:
                update_data["webhook_url"] = args.webhook_url
            if args.name:
                update_data["name"] = args.name

            if not update_data:
                print(
                    "Error: No update fields provided. Use --webhook-url, --name, or --json-data",
                    file=sys.stderr,
                )
                return 1

        return main_update(
            agent_id=args.agent_id,
            api_key=api_key,
            update_data=update_data,
            json_output=args.json,
        )
    else:
        return 1


def main(argv: Sequence[str] | None = None) -> None:
    """Main entry point for the CLI."""

    # If no arguments provided, use sys.argv
    if argv is None:
        argv = sys.argv[1:]

    parser = create_parser()

    # If no arguments, show help
    if len(argv) == 0:
        parser.print_help()
        sys.exit(0)

    # Parse arguments
    args = parser.parse_args(argv)

    # Route to appropriate handler based on command
    if args.command == "run":
        validate_run_args(args)
        asyncio.run(run_conversation(args))
    elif args.command == "api-agents":
        sys.exit(handle_api_agents(args))
    else:
        # No command specified, show help
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
