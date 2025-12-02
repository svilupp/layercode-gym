#!/usr/bin/env python3
"""
Basic structure tests for webhook utilities.

These tests validate the structure and syntax without requiring dependencies.
Full functional tests should be run with dependencies installed (uv run pytest).
"""

import ast
import sys
from pathlib import Path

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_test(name: str) -> None:
    """Print test name."""
    print(f"\n{BLUE}▶ {name}{RESET}")


def print_pass(message: str) -> None:
    """Print pass message."""
    print(f"  {GREEN}✓{RESET} {message}")


def print_fail(message: str) -> None:
    """Print fail message."""
    print(f"  {RED}✗{RESET} {message}")


def test_webhook_utils_syntax() -> bool:
    """Test webhook_utils.py is valid Python."""
    print_test("Testing webhook_utils.py Syntax")

    try:
        utils_path = Path("src/layercode_gym/webhook_utils.py")

        if not utils_path.exists():
            print_fail("webhook_utils.py not found")
            return False

        with open(utils_path) as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)
        print_pass("webhook_utils.py is valid Python")

        # Check for required functions
        functions = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]

        required_functions = [
            "get_agent_webhook",
            "update_agent_webhook",
            "print_agent_info",
            "main_get",
            "main_update",
        ]

        for func in required_functions:
            if func not in functions:
                print_fail(f"Missing function: {func}")
                return False

        print_pass(f"All required functions present: {', '.join(required_functions)}")

        # Check for AgentInfo class
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        if "AgentInfo" not in classes:
            print_fail("Missing AgentInfo dataclass")
            return False

        print_pass("AgentInfo dataclass present")

        # Check for httpx import
        if "httpx" not in content:
            print_fail("Missing httpx import")
            return False

        print_pass("httpx import present")

        return True

    except Exception as e:
        print_fail(f"Syntax validation failed: {e}")
        return False


def test_webhook_cli_syntax() -> bool:
    """Test webhook_cli.py is valid Python."""
    print_test("Testing webhook_cli.py Syntax")

    try:
        cli_path = Path("src/layercode_gym/webhook_cli.py")

        if not cli_path.exists():
            print_fail("webhook_cli.py not found")
            return False

        with open(cli_path) as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)
        print_pass("webhook_cli.py is valid Python")

        # Check for required functions
        functions = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]

        required_functions = [
            "create_parser",
            "get_api_key",
            "main",
        ]

        for func in required_functions:
            if func not in functions:
                print_fail(f"Missing function: {func}")
                return False

        print_pass(f"All required functions present: {', '.join(required_functions)}")

        # Check for argparse usage
        if "argparse" not in content:
            print_fail("Missing argparse import")
            return False

        print_pass("argparse import present")

        # Check for subparsers (get/update commands)
        if "add_subparsers" not in content:
            print_fail("Missing subparsers for commands")
            return False

        print_pass("Subparsers for get/update commands present")

        # Check for webhook_utils import
        if "from layercode_gym.webhook_utils import" not in content:
            print_fail("Missing import from webhook_utils")
            return False

        print_pass("webhook_utils import present")

        return True

    except Exception as e:
        print_fail(f"Syntax validation failed: {e}")
        return False


def test_cli_integration() -> bool:
    """Test CLI integration with main CLI."""
    print_test("Testing CLI Integration")

    try:
        cli_path = Path("src/layercode_gym/cli.py")

        if not cli_path.exists():
            print_fail("cli.py not found")
            return False

        with open(cli_path) as f:
            content = f.read()

        # Check for webhook routing
        if 'argv[0] == "webhook"' not in content:
            print_fail("Missing webhook routing in main CLI")
            return False

        print_pass("Webhook routing present in main CLI")

        # Check for webhook_cli import
        if "from layercode_gym.webhook_cli import main as webhook_main" not in content:
            print_fail("Missing webhook_cli import")
            return False

        print_pass("webhook_cli import present")

        return True

    except Exception as e:
        print_fail(f"CLI integration test failed: {e}")
        return False


def test_api_structure() -> bool:
    """Test webhook API structure."""
    print_test("Testing Webhook API Structure")

    try:
        utils_path = Path("src/layercode_gym/webhook_utils.py")

        with open(utils_path) as f:
            content = f.read()

        # Check for correct API endpoint
        if "api.layercode.com/v1/agents" not in content:
            print_fail("Missing correct LayerCode API endpoint")
            return False

        print_pass("LayerCode API endpoint correct")

        # Check for Bearer auth
        if "Bearer" not in content:
            print_fail("Missing Bearer authentication")
            return False

        print_pass("Bearer authentication present")

        # Check for GET request (get webhook)
        if ".get(" not in content:
            print_fail("Missing GET request method")
            return False

        print_pass("GET request method present")

        # Check for POST request (update webhook)
        if ".post(" not in content:
            print_fail("Missing POST request method")
            return False

        print_pass("POST request method present")

        # Check for webhook_url in payload
        if '"webhook_url"' not in content:
            print_fail("Missing webhook_url in payload")
            return False

        print_pass("webhook_url payload field present")

        return True

    except Exception as e:
        print_fail(f"API structure test failed: {e}")
        return False


def test_error_handling() -> bool:
    """Test error handling structure."""
    print_test("Testing Error Handling Structure")

    try:
        utils_path = Path("src/layercode_gym/webhook_utils.py")

        with open(utils_path) as f:
            content = f.read()

        # Check for HTTPStatusError handling
        if "HTTPStatusError" not in content:
            print_fail("Missing HTTPStatusError handling")
            return False

        print_pass("HTTPStatusError handling present")

        # Check for 401 handling
        if "401" not in content:
            print_fail("Missing 401 (Unauthorized) handling")
            return False

        print_pass("401 error handling present")

        # Check for 404 handling
        if "404" not in content:
            print_fail("Missing 404 (Not Found) handling")
            return False

        print_pass("404 error handling present")

        # Check for sys.stderr usage
        if "sys.stderr" not in content:
            print_fail("Missing error output to stderr")
            return False

        print_pass("Error output to stderr present")

        return True

    except Exception as e:
        print_fail(f"Error handling test failed: {e}")
        return False


def test_cli_help_docs() -> bool:
    """Test CLI has proper documentation."""
    print_test("Testing CLI Documentation")

    try:
        cli_path = Path("src/layercode_gym/webhook_cli.py")

        with open(cli_path) as f:
            content = f.read()

        # Check for module docstring
        if '"""' not in content[:500]:
            print_fail("Missing module docstring")
            return False

        print_pass("Module docstring present")

        # Check for examples in help
        if "Examples:" not in content:
            print_fail("Missing examples in help text")
            return False

        print_pass("Examples in help text")

        # Check for CI script example
        if "CI script" in content or "CI Script" in content:
            print_pass("CI script example present")
        else:
            print_fail("Missing CI script example")
            return False

        # Check for --json flag documentation
        if "--json" in content:
            print_pass("--json flag documented")
        else:
            print_fail("Missing --json flag")
            return False

        return True

    except Exception as e:
        print_fail(f"Documentation test failed: {e}")
        return False


def run_all_tests() -> bool:
    """Run all webhook utility tests."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Webhook Utilities Test Suite (Basic){RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    tests = [
        ("webhook_utils.py Syntax", test_webhook_utils_syntax),
        ("webhook_cli.py Syntax", test_webhook_cli_syntax),
        ("CLI Integration", test_cli_integration),
        ("Webhook API Structure", test_api_structure),
        ("Error Handling Structure", test_error_handling),
        ("CLI Documentation", test_cli_help_docs),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_fail(f"Test '{name}' raised exception: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    if failed == 0:
        print(f"{GREEN}Note: These are basic structure tests.{RESET}")
        print(f"{GREEN}Run 'uv run pytest' for full functional tests.{RESET}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
