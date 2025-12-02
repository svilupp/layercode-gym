#!/usr/bin/env python3
"""
Webhook management CLI for LayerCode agents.

This is a standalone utility for CI workflows that need to manage agent webhooks.

Usage:
    # Get current webhook
    layercode-gym webhook get --agent-id ag-123456

    # Get as JSON (for scripting)
    layercode-gym webhook get --agent-id ag-123456 --json

    # Update webhook
    layercode-gym webhook update --agent-id ag-123456 --url https://new.example.com

CI Script Example:
    # Save original webhook
    ORIGINAL=$(layercode-gym webhook get --agent-id ag-123 --json | jq -r .webhook_url)

    # Update to PR backend
    layercode-gym webhook update --agent-id ag-123 --url https://pr-456.example.com

    # Run tests
    python run_tests.py

    # Restore original
    layercode-gym webhook update --agent-id ag-123 --url "$ORIGINAL"
"""

import argparse
import os
import sys
from typing import Sequence

from layercode_gym.webhook_utils import main_get, main_update


def create_parser() -> argparse.ArgumentParser:
    """Create the webhook CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="layercode-gym webhook",
        description="Manage LayerCode agent webhooks (utility for CI workflows)",
        epilog=(
            "Examples:\n"
            "  # Get current webhook\n"
            "  layercode-gym webhook get --agent-id ag-123456\n"
            "\n"
            "  # Get as JSON for scripting\n"
            "  layercode-gym webhook get --agent-id ag-123 --json\n"
            "\n"
            "  # Update webhook\n"
            "  layercode-gym webhook update --agent-id ag-123 --url https://new.com\n"
            "\n"
            "  # CI script pattern\n"
            "  ORIGINAL=$(layercode-gym webhook get --agent-id ag-123 --json | jq -r .webhook_url)\n"
            "  layercode-gym webhook update --agent-id ag-123 --url https://test.com\n"
            "  # ... run tests ...\n"
            "  layercode-gym webhook update --agent-id ag-123 --url \"$ORIGINAL\"\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Webhook command to execute",
    )

    # 'get' command
    get_parser = subparsers.add_parser(
        "get",
        help="Get current webhook URL for an agent",
        description="Get the current webhook URL configured for a LayerCode agent",
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
    get_parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="Return exit code 0 even on error (useful for CI cleanup scripts)",
    )

    # 'update' command
    update_parser = subparsers.add_parser(
        "update",
        help="Update webhook URL for an agent",
        description="Update the webhook URL for a LayerCode agent",
    )
    update_parser.add_argument(
        "--agent-id",
        required=True,
        metavar="ID",
        help="LayerCode agent ID (e.g., ag-123456)",
    )
    update_parser.add_argument(
        "--url",
        required=True,
        metavar="URL",
        help="New webhook URL (e.g., https://example.com/webhook)",
    )
    update_parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="LayerCode API key (or set LAYERCODE_API_KEY env var)",
    )
    update_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    update_parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="Return exit code 0 even on error (useful for CI cleanup scripts)",
    )

    return parser


def get_api_key(args: argparse.Namespace) -> str:
    """Get API key from args or environment.

    Args:
        args: Parsed command-line arguments

    Returns:
        API key string

    Raises:
        SystemExit: If API key not found
    """
    api_key = args.api_key or os.environ.get("LAYERCODE_API_KEY")

    if not api_key:
        print(
            "Error: API key required. Provide via --api-key or LAYERCODE_API_KEY env var",
            file=sys.stderr,
        )
        sys.exit(1)

    return api_key


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for webhook CLI.

    Args:
        argv: Command-line arguments (excluding 'webhook')

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()

    # If no arguments, show help
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 0:
        parser.print_help()
        return 0

    # Parse arguments
    args = parser.parse_args(argv)

    # Get API key
    api_key = get_api_key(args)

    # Route to appropriate handler
    if args.command == "get":
        return main_get(
            agent_id=args.agent_id,
            api_key=api_key,
            json_output=args.json,
            ignore_errors=args.ignore_errors,
        )
    elif args.command == "update":
        return main_update(
            agent_id=args.agent_id,
            api_key=api_key,
            webhook_url=args.url,
            json_output=args.json,
            ignore_errors=args.ignore_errors,
        )
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
