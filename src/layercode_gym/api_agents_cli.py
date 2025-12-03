#!/usr/bin/env python3
"""
LayerCode Agents REST API CLI.

Direct mapping to LayerCode REST API for agent management.

Usage:
    # List all agents
    layercode-gym api-agents list [--json]

    # Get agent details
    layercode-gym api-agents get --agent-id ag-123456 [--json]

    # Update agent webhook
    layercode-gym api-agents update --agent-id ag-123 --webhook-url https://new.com

    # Update from JSON
    layercode-gym api-agents update --agent-id ag-123 --json-data '{"webhook_url":"..."}'

CI Script Example:
    # Save original webhook
    ORIGINAL=$(layercode-gym api-agents get --agent-id ag-123 --json | jq -r .webhook_url)

    # Update to PR backend
    layercode-gym api-agents update --agent-id ag-123 --webhook-url https://pr-456.com

    # Run tests
    python run_tests.py

    # Restore original
    layercode-gym api-agents update --agent-id ag-123 --webhook-url "$ORIGINAL"
"""

import argparse
import json
import os
import sys
from typing import Any, Sequence, cast

from layercode_gym.api_agents_utils import main_get, main_list, main_update


def create_parser() -> argparse.ArgumentParser:
    """Create the api-agents CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="layercode-gym api-agents",
        description="Manage LayerCode agents via REST API",
        epilog=(
            "Examples:\n"
            "  # List all agents\n"
            "  layercode-gym api-agents list\n"
            "\n"
            "  # Get agent details\n"
            "  layercode-gym api-agents get --agent-id ag-123456\n"
            "\n"
            "  # Get as JSON for scripting\n"
            "  layercode-gym api-agents get --agent-id ag-123 --json\n"
            "\n"
            "  # Update webhook\n"
            "  layercode-gym api-agents update --agent-id ag-123 --webhook-url https://new.com\n"
            "\n"
            "  # Update with JSON data\n"
            '  layercode-gym api-agents update --agent-id ag-123 --json-data \'{"webhook_url":"..."}\'\n'
            "\n"
            "  # CI script pattern\n"
            "  ORIGINAL=$(layercode-gym api-agents get --agent-id ag-123 --json | jq -r .webhook_url)\n"
            "  layercode-gym api-agents update --agent-id ag-123 --webhook-url https://test.com\n"
            "  # ... run tests ...\n"
            '  layercode-gym api-agents update --agent-id ag-123 --webhook-url "$ORIGINAL"\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="API command to execute",
    )

    # 'list' command
    list_parser = subparsers.add_parser(
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
    get_parser = subparsers.add_parser(
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
    update_parser = subparsers.add_parser(
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


def build_update_data(args: argparse.Namespace) -> dict[str, Any]:
    """Build update data dict from args.

    Args:
        args: Parsed command-line arguments

    Returns:
        Dict with fields to update

    Raises:
        SystemExit: If no update fields provided or conflicting args
    """
    # If JSON data provided, use that
    if args.json_data:
        if args.webhook_url or args.name:
            print(
                "Error: Cannot use --json-data with --webhook-url or --name",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            return cast(dict[str, Any], json.loads(args.json_data))
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON data - {e}", file=sys.stderr)
            sys.exit(1)

    # Build from individual flags
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
        sys.exit(1)

    return update_data


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for api-agents CLI.

    Args:
        argv: Command-line arguments (excluding 'api-agents')

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
    if args.command == "list":
        return main_list(
            api_key=api_key,
            json_output=args.json,
        )
    elif args.command == "get":
        return main_get(
            agent_id=args.agent_id,
            api_key=api_key,
            json_output=args.json,
        )
    elif args.command == "update":
        update_data = build_update_data(args)
        return main_update(
            agent_id=args.agent_id,
            api_key=api_key,
            update_data=update_data,
            json_output=args.json,
        )
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
