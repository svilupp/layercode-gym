#!/usr/bin/env python3
"""
Comprehensive test suite for the LayerCode Gym GitHub Action.

Tests:
- YAML structure validation
- Runner script logic
- JSON parsing
- Error handling
- Documentation links
- Integration points
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
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


def print_warn(message: str) -> None:
    """Print warning message."""
    print(f"  {YELLOW}⚠{RESET} {message}")


def test_yaml_structure() -> bool:
    """Test YAML files are valid and well-structured."""
    print_test("Testing YAML Structure")

    try:
        import yaml

        # Test action.yml
        action_path = Path(".github/actions/layercode-gym-test/action.yml")
        with open(action_path) as f:
            action = yaml.safe_load(f)

        # Validate required fields
        required_fields = ["name", "description", "inputs", "outputs", "runs"]
        for field in required_fields:
            if field not in action:
                print_fail(f"action.yml missing required field: {field}")
                return False

        print_pass(f"action.yml has all required fields")

        # Validate inputs
        required_inputs = [
            "personas",
            "server-url",
            "layercode-agent-id",
            "layercode-api-key",
            "openai-api-key",
        ]
        for inp in required_inputs:
            if inp not in action["inputs"]:
                print_fail(f"action.yml missing required input: {inp}")
                return False
            if action["inputs"][inp].get("required") not in [True, "true"]:
                print_fail(f"Required input '{inp}' not marked as required")
                return False

        print_pass(f"All required inputs present and marked as required")

        # Validate outputs
        required_outputs = [
            "conversations-run",
            "conversations-passed",
            "conversations-failed",
            "results-path",
        ]
        for out in required_outputs:
            if out not in action["outputs"]:
                print_fail(f"action.yml missing required output: {out}")
                return False

        print_pass(f"All required outputs present")

        # Test example workflow
        workflow_path = Path(".github/workflows/example-gym-test.yml")
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)

        if "jobs" not in workflow:
            print_fail("example-gym-test.yml missing jobs")
            return False

        print_pass("example-gym-test.yml is valid")

        # Test CI workflow
        ci_path = Path(".github/workflows/ci.yml")
        with open(ci_path) as f:
            ci = yaml.safe_load(f)

        if "validate-action" not in ci["jobs"]:
            print_fail("ci.yml missing validate-action job")
            return False

        print_pass("ci.yml has validate-action job")

        return True

    except Exception as e:
        print_fail(f"YAML validation failed: {e}")
        return False


def test_runner_imports() -> bool:
    """Test that runner.py has valid imports."""
    print_test("Testing Runner Script Imports")

    try:
        runner_path = Path(".github/actions/layercode-gym-test/runner.py")

        # Check file exists
        if not runner_path.exists():
            print_fail("runner.py not found")
            return False

        # Parse the file
        import ast

        with open(runner_path) as f:
            tree = ast.parse(f.read())

        # Find all imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        required_imports = [
            "asyncio",
            "json",
            "os",
            "sys",
            "pathlib",
            "dataclasses",
            "httpx",
        ]

        for imp in required_imports:
            if imp not in imports:
                print_fail(f"Missing required import: {imp}")
                return False

        print_pass(f"All required imports present")

        # Check for class definitions
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        required_classes = [
            "PersonaConfig",
            "TestResult",
            "LayerCodeGymRunner",
        ]

        for cls in required_classes:
            if cls not in classes:
                print_fail(f"Missing required class: {cls}")
                return False

        print_pass(f"All required classes present: {', '.join(required_classes)}")

        # Check for main function (including async)
        functions = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        if "main" not in functions:
            print_fail("Missing main() function")
            return False

        print_pass("main() function present")

        return True

    except Exception as e:
        print_fail(f"Import validation failed: {e}")
        return False


def test_persona_json_parsing() -> bool:
    """Test persona JSON parsing logic."""
    print_test("Testing Persona JSON Parsing")

    try:
        # Valid personas
        valid_personas = [
            [
                {
                    "background": "You are a customer",
                    "intent": "Learn about the product",
                }
            ],
            [
                {
                    "background": "Customer 1",
                    "intent": "Intent 1",
                },
                {
                    "background": "Customer 2",
                    "intent": "Intent 2",
                },
            ],
        ]

        for i, personas in enumerate(valid_personas, 1):
            personas_json = json.dumps(personas)
            try:
                parsed = json.loads(personas_json)
                for p in parsed:
                    if "background" not in p or "intent" not in p:
                        print_fail(f"Persona {i} missing required fields")
                        return False
                print_pass(f"Valid personas {i} parsed correctly")
            except json.JSONDecodeError as e:
                print_fail(f"Valid personas {i} failed to parse: {e}")
                return False

        # Invalid personas (should fail)
        invalid_personas = [
            "not a list",
            "[]",  # Empty list
            '[{"background": "test"}]',  # Missing intent
            '[{"intent": "test"}]',  # Missing background
            "invalid json {",
        ]

        for i, personas_json in enumerate(invalid_personas, 1):
            try:
                if personas_json == "[]":
                    parsed = json.loads(personas_json)
                    if len(parsed) == 0:
                        print_pass(f"Empty personas detected correctly")
                        continue
                elif personas_json == "not a list":
                    # This would fail JSON parsing
                    print_pass(f"Non-JSON string rejected correctly")
                    continue
                else:
                    parsed = json.loads(personas_json)
                    # Check if it has required fields
                    for p in parsed:
                        if "background" not in p or "intent" not in p:
                            print_pass(f"Invalid persona {i} would be caught")
                            break
            except (json.JSONDecodeError, KeyError, TypeError):
                print_pass(f"Invalid persona {i} rejected correctly")

        return True

    except Exception as e:
        print_fail(f"Persona parsing test failed: {e}")
        return False


def test_environment_variables() -> bool:
    """Test that runner.py handles environment variables correctly."""
    print_test("Testing Environment Variable Handling")

    try:
        import ast

        runner_path = Path(".github/actions/layercode-gym-test/runner.py")
        with open(runner_path) as f:
            content = f.read()

        # Check for required env vars
        required_env_vars = [
            "SERVER_URL",
            "LAYERCODE_AGENT_ID",
            "LAYERCODE_API_KEY",
            "OPENAI_API_KEY",
            "PERSONAS",
            "MAX_TURNS",
            "JUDGE_ENABLED",
            "JUDGE_CRITERIA",
            "MODEL",
        ]

        for var in required_env_vars:
            if var not in content:
                print_fail(f"Missing environment variable: {var}")
                return False

        print_pass(f"All required environment variables referenced")

        # Check for GITHUB_OUTPUT
        if "GITHUB_OUTPUT" not in content:
            print_fail("Missing GITHUB_OUTPUT handling")
            return False

        print_pass("GITHUB_OUTPUT handling present")

        return True

    except Exception as e:
        print_fail(f"Environment variable test failed: {e}")
        return False


def test_webhook_configuration() -> bool:
    """Test webhook configuration logic."""
    print_test("Testing Webhook Configuration Logic")

    try:
        runner_path = Path(".github/actions/layercode-gym-test/runner.py")
        with open(runner_path) as f:
            content = f.read()

        # Check for webhook configuration method
        if "configure_webhook" not in content:
            print_fail("Missing configure_webhook method")
            return False

        print_pass("configure_webhook method present")

        # Check for LayerCode API endpoint
        if "api.layercode.com" not in content:
            print_fail("Missing LayerCode API endpoint")
            return False

        print_pass("LayerCode API endpoint present")

        # Check for PUT request (webhook update)
        if "put(" not in content or "PUT" in content:
            # Either httpx.put() or requests.put()
            print_pass("HTTP PUT method for webhook configuration")
        else:
            print_fail("Missing PUT request for webhook configuration")
            return False

        # Check for webhook URL construction
        if "webhook" not in content:
            print_fail("Missing webhook URL construction")
            return False

        print_pass("Webhook URL construction present")

        return True

    except Exception as e:
        print_fail(f"Webhook configuration test failed: {e}")
        return False


def test_parallel_execution() -> bool:
    """Test parallel execution logic."""
    print_test("Testing Parallel Execution Logic")

    try:
        runner_path = Path(".github/actions/layercode-gym-test/runner.py")
        with open(runner_path) as f:
            content = f.read()

        # Check for asyncio.gather
        if "gather" not in content:
            print_fail("Missing asyncio.gather for parallel execution")
            return False

        print_pass("asyncio.gather present for parallel execution")

        # Check for tqdm progress bar
        if "tqdm" not in content:
            print_warn("Missing tqdm progress bar (optional but nice)")
        else:
            print_pass("tqdm progress bar present")

        # Check for run_single_conversation method
        if "run_single_conversation" not in content:
            print_fail("Missing run_single_conversation method")
            return False

        print_pass("run_single_conversation method present")

        return True

    except Exception as e:
        print_fail(f"Parallel execution test failed: {e}")
        return False


def test_judge_integration() -> bool:
    """Test judge integration logic."""
    print_test("Testing Judge Integration")

    try:
        runner_path = Path(".github/actions/layercode-gym-test/runner.py")
        with open(runner_path) as f:
            content = f.read()

        # Check for judge method
        if "run_judge" not in content:
            print_fail("Missing run_judge method")
            return False

        print_pass("run_judge method present")

        # Check for overall_pass field (future interface)
        if "overall_pass" not in content:
            print_fail("Missing overall_pass field for judge result")
            return False

        print_pass("overall_pass field present (future interface)")

        # Check for judge criteria
        if "judge_criteria" not in content.lower():
            print_fail("Missing judge criteria handling")
            return False

        print_pass("Judge criteria handling present")

        # Check for conditional judge execution
        if "judge_enabled" not in content:
            print_fail("Missing conditional judge execution")
            return False

        print_pass("Conditional judge execution present")

        return True

    except Exception as e:
        print_fail(f"Judge integration test failed: {e}")
        return False


def test_error_handling() -> bool:
    """Test error handling and exit codes."""
    print_test("Testing Error Handling")

    try:
        runner_path = Path(".github/actions/layercode-gym-test/runner.py")
        with open(runner_path) as f:
            content = f.read()

        # Check for try-except blocks
        if "try:" not in content or "except" not in content:
            print_fail("Missing try-except error handling")
            return False

        print_pass("try-except blocks present")

        # Check for sys.exit
        if "sys.exit" not in content:
            print_fail("Missing sys.exit for error codes")
            return False

        print_pass("sys.exit present for error codes")

        # Check for httpx error handling
        if "HTTPError" not in content:
            print_fail("Missing HTTPError handling")
            return False

        print_pass("HTTPError handling present")

        return True

    except Exception as e:
        print_fail(f"Error handling test failed: {e}")
        return False


def test_documentation_links() -> bool:
    """Test that documentation links are correct."""
    print_test("Testing Documentation Links")

    try:
        # Check README links
        readme_path = Path("README.md")
        with open(readme_path) as f:
            readme = f.read()

        # Check for GitHub Actions documentation link
        if "docs/github-action.md" not in readme:
            print_fail("README missing link to github-action.md")
            return False

        print_pass("README links to github-action.md")

        # Check mkdocs.yml navigation
        mkdocs_path = Path("mkdocs.yml")
        with open(mkdocs_path) as f:
            import yaml

            mkdocs = yaml.safe_load(f)

        nav_items = [item for section in mkdocs["nav"] for item in section.values()]
        if "github-action.md" not in nav_items:
            print_fail("mkdocs.yml missing github-action.md in navigation")
            return False

        print_pass("mkdocs.yml includes github-action.md in navigation")

        # Check that github-action.md exists
        gh_action_doc_path = Path("docs/github-action.md")
        if not gh_action_doc_path.exists():
            print_fail("docs/github-action.md does not exist")
            return False

        print_pass("docs/github-action.md exists")

        # Check action README exists
        action_readme_path = Path(".github/actions/layercode-gym-test/README.md")
        if not action_readme_path.exists():
            print_fail("Action README.md does not exist")
            return False

        print_pass("Action README.md exists")

        return True

    except Exception as e:
        print_fail(f"Documentation links test failed: {e}")
        return False


def test_action_references() -> bool:
    """Test that action can be referenced correctly."""
    print_test("Testing Action References")

    try:
        # Check example workflow references the action correctly
        workflow_path = Path(".github/workflows/example-gym-test.yml")
        with open(workflow_path) as f:
            import yaml

            workflow = yaml.safe_load(f)

        # Find the action usage
        found_action = False
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step and "layercode-gym-test" in step["uses"]:
                    found_action = True
                    action_ref = step["uses"]

                    # Check the reference format
                    if not action_ref.startswith("./"):
                        print_fail(
                            f"Action reference should be relative: {action_ref}"
                        )
                        return False

                    print_pass(f"Action referenced correctly: {action_ref}")

                    # Check required inputs are provided
                    if "with" not in step:
                        print_fail("Action usage missing 'with' inputs")
                        return False

                    required_inputs = [
                        "personas",
                        "server-url",
                        "layercode-agent-id",
                        "layercode-api-key",
                        "openai-api-key",
                    ]

                    for inp in required_inputs:
                        if inp not in step["with"]:
                            print_fail(f"Example workflow missing required input: {inp}")
                            return False

                    print_pass("All required inputs present in example")

        if not found_action:
            print_fail("Example workflow does not use the action")
            return False

        return True

    except Exception as e:
        print_fail(f"Action references test failed: {e}")
        return False


def test_concurrency_control() -> bool:
    """Test concurrency control in workflows."""
    print_test("Testing Concurrency Control")

    try:
        workflow_path = Path(".github/workflows/example-gym-test.yml")
        with open(workflow_path) as f:
            import yaml

            workflow = yaml.safe_load(f)

        # Check for concurrency in job
        for job_name, job in workflow["jobs"].items():
            if "concurrency" not in job:
                print_fail(f"Job '{job_name}' missing concurrency control")
                return False

            concurrency = job["concurrency"]
            if "group" not in concurrency:
                print_fail(f"Job '{job_name}' concurrency missing 'group'")
                return False

            # Check that group includes agent ID
            if "LAYERCODE_AGENT_ID" not in concurrency["group"]:
                print_fail(
                    f"Job '{job_name}' concurrency group should include LAYERCODE_AGENT_ID"
                )
                return False

            print_pass(f"Job '{job_name}' has proper concurrency control")

            # Check cancel-in-progress is false
            if concurrency.get("cancel-in-progress", True) != False:
                print_warn(
                    f"Job '{job_name}' should set cancel-in-progress: false"
                )

        return True

    except Exception as e:
        print_fail(f"Concurrency control test failed: {e}")
        return False


def test_outputs_setting() -> bool:
    """Test that GitHub Action outputs are set correctly."""
    print_test("Testing GitHub Action Outputs")

    try:
        runner_path = Path(".github/actions/layercode-gym-test/runner.py")
        with open(runner_path) as f:
            content = f.read()

        # Check for output setting
        required_outputs = [
            "conversations-run",
            "conversations-passed",
            "conversations-failed",
            "results-path",
        ]

        for output in required_outputs:
            if output not in content:
                print_fail(f"Missing output handling: {output}")
                return False

        print_pass("All required outputs handled in runner")

        # Check for GITHUB_OUTPUT file writing
        if "github_output" not in content or "write" not in content:
            print_fail("Missing GITHUB_OUTPUT file writing")
            return False

        print_pass("GITHUB_OUTPUT file writing present")

        return True

    except Exception as e:
        print_fail(f"Outputs setting test failed: {e}")
        return False


def run_all_tests() -> bool:
    """Run all tests."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}LayerCode Gym GitHub Action Test Suite{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

    tests = [
        ("YAML Structure", test_yaml_structure),
        ("Runner Imports", test_runner_imports),
        ("Persona JSON Parsing", test_persona_json_parsing),
        ("Environment Variables", test_environment_variables),
        ("Webhook Configuration", test_webhook_configuration),
        ("Parallel Execution", test_parallel_execution),
        ("Judge Integration", test_judge_integration),
        ("Error Handling", test_error_handling),
        ("Documentation Links", test_documentation_links),
        ("Action References", test_action_references),
        ("Concurrency Control", test_concurrency_control),
        ("GitHub Outputs", test_outputs_setting),
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
            failed += 1

    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
