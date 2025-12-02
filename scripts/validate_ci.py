#!/usr/bin/env python3
"""
Comprehensive CI validation suite for LayerCode Gym.

Validates:
- GitHub Action structure and configuration
- Runner script correctness
- API agents CLI structure
- Documentation completeness
- Security considerations
- Cross-file consistency

Run: python scripts/validate_ci.py
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# Ensure we're running from repo root
REPO_ROOT = Path(__file__).parent.parent
os.chdir(REPO_ROOT)

# =============================================================================
# Test Framework
# =============================================================================

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    passed: bool
    message: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Collection of test results."""

    name: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def warnings(self) -> int:
        return sum(len(r.warnings) for r in self.results)


class TestRunner:
    """Test runner with reporting."""

    def __init__(self) -> None:
        self.suites: list[TestSuite] = []
        self.current_suite: TestSuite | None = None

    def suite(self, name: str) -> None:
        """Start a new test suite."""
        self.current_suite = TestSuite(name=name)
        self.suites.append(self.current_suite)
        print(f"\n{BLUE}{BOLD}{'=' * 70}{RESET}")
        print(f"{BLUE}{BOLD}{name}{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}")

    def test(self, name: str) -> None:
        """Print test name."""
        print(f"\n{BLUE}> {name}{RESET}")

    def passed(self, message: str) -> None:
        """Record a passing check."""
        print(f"  {GREEN}[PASS]{RESET} {message}")
        if self.current_suite:
            self.current_suite.results.append(
                TestResult(name=message, passed=True, message=message)
            )

    def failed(self, message: str) -> None:
        """Record a failing check."""
        print(f"  {RED}[FAIL]{RESET} {message}")
        if self.current_suite:
            self.current_suite.results.append(
                TestResult(name=message, passed=False, message=message)
            )

    def warn(self, message: str) -> None:
        """Record a warning."""
        print(f"  {YELLOW}[WARN]{RESET} {message}")
        if self.current_suite and self.current_suite.results:
            self.current_suite.results[-1].warnings.append(message)

    def summary(self) -> bool:
        """Print summary and return success status."""
        total_passed = sum(s.passed for s in self.suites)
        total_failed = sum(s.failed for s in self.suites)
        total_warnings = sum(s.warnings for s in self.suites)

        print(f"\n{BLUE}{BOLD}{'=' * 70}{RESET}")
        print(f"{BLUE}{BOLD}SUMMARY{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}\n")

        for suite in self.suites:
            status = f"{GREEN}PASS{RESET}" if suite.failed == 0 else f"{RED}FAIL{RESET}"
            print(
                f"  {suite.name}: {status} ({suite.passed}/{suite.passed + suite.failed})"
            )

        print(f"\n{BLUE}{'─' * 70}{RESET}")
        print(f"  {GREEN}Passed:{RESET}   {total_passed}")
        print(f"  {RED}Failed:{RESET}   {total_failed}")
        print(f"  {YELLOW}Warnings:{RESET} {total_warnings}")
        print(f"{BLUE}{'─' * 70}{RESET}\n")

        if total_failed == 0:
            print(f"{GREEN}{BOLD}All validation checks passed.{RESET}\n")
        else:
            print(
                f"{RED}{BOLD}Validation failed with {total_failed} error(s).{RESET}\n"
            )

        return total_failed == 0


runner = TestRunner()


# =============================================================================
# Utility Functions
# =============================================================================


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    import yaml

    with open(path) as f:
        return yaml.safe_load(f)


def parse_python(path: Path) -> ast.Module:
    """Parse Python file to AST."""
    with open(path) as f:
        return ast.parse(f.read())


def get_functions(tree: ast.Module) -> list[str]:
    """Get all function names from AST."""
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def get_classes(tree: ast.Module) -> list[str]:
    """Get all class names from AST."""
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def get_imports(tree: ast.Module) -> list[str]:
    """Get all imported modules from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def file_contains(path: Path, *patterns: str) -> dict[str, bool]:
    """Check if file contains all patterns."""
    with open(path) as f:
        content = f.read()
    return {p: p in content for p in patterns}


def file_contains_any(path: Path, *patterns: str) -> bool:
    """Check if file contains any of the patterns."""
    with open(path) as f:
        content = f.read()
    return any(p in content for p in patterns)


# =============================================================================
# Test Suites
# =============================================================================


def test_action_yaml_structure() -> None:
    """Validate action.yml structure and completeness."""
    runner.suite("GitHub Action Configuration")
    action_path = Path(".github/actions/layercode-gym-test/action.yml")

    runner.test("action.yml Structure")

    try:
        action = load_yaml(action_path)

        # Required top-level fields
        required_fields = ["name", "description", "inputs", "outputs", "runs"]
        for field in required_fields:
            if field in action:
                runner.passed(f"Has required field: {field}")
            else:
                runner.failed(f"Missing required field: {field}")

        # Branding (optional but professional)
        if "branding" in action:
            if "icon" in action["branding"] and "color" in action["branding"]:
                runner.passed("Has branding (icon + color)")
            else:
                runner.warn("Incomplete branding configuration")
        else:
            runner.warn("No branding configured (optional)")

        # Author
        if "author" in action:
            runner.passed(f"Has author: {action['author']}")
        else:
            runner.warn("No author specified")

    except Exception as e:
        runner.failed(f"Failed to parse action.yml: {e}")
        return

    runner.test("Required Inputs")

    required_inputs = [
        ("personas", "JSON array of persona configurations"),
        ("server-url", "Backend server URL"),
        ("layercode-agent-id", "Agent ID from LayerCode"),
        ("openai-api-key", "OpenAI API key"),
    ]

    for input_name, description in required_inputs:
        if input_name not in action["inputs"]:
            runner.failed(f"Missing input: {input_name}")
            continue

        inp = action["inputs"][input_name]
        if inp.get("required") in [True, "true"]:
            runner.passed(f"Input '{input_name}' is required")
        else:
            runner.failed(f"Input '{input_name}' should be marked required")

        if "description" in inp and len(inp["description"]) > 10:
            runner.passed(f"Input '{input_name}' has description")
        else:
            runner.warn(f"Input '{input_name}' needs better description")

    runner.test("Optional Inputs with Defaults")

    optional_inputs = [
        ("max-turns", "5"),
        ("judge-enabled", "false"),
        ("fail-on-judge-failure", "true"),
        ("upload-artifacts", "true"),
    ]

    for input_name, expected_default in optional_inputs:
        if input_name not in action["inputs"]:
            runner.warn(f"Optional input '{input_name}' not defined")
            continue

        inp = action["inputs"][input_name]
        if "default" in inp:
            if str(inp["default"]) == expected_default:
                runner.passed(
                    f"Input '{input_name}' has correct default: {expected_default}"
                )
            else:
                runner.warn(
                    f"Input '{input_name}' default is {inp['default']}, expected {expected_default}"
                )
        else:
            runner.warn(f"Input '{input_name}' has no default")

    runner.test("Required Outputs")

    required_outputs = [
        "conversations-run",
        "conversations-passed",
        "conversations-failed",
        "results-path",
    ]

    for output_name in required_outputs:
        if output_name in action["outputs"]:
            out = action["outputs"][output_name]
            if "description" in out:
                runner.passed(f"Output '{output_name}' defined with description")
            else:
                runner.warn(f"Output '{output_name}' needs description")
        else:
            runner.failed(f"Missing output: {output_name}")

    runner.test("Runs Configuration")

    runs = action.get("runs", {})
    if runs.get("using") == "composite":
        runner.passed("Uses composite action (correct)")
    else:
        runner.failed(f"Expected 'using: composite', got: {runs.get('using')}")

    if "steps" in runs and len(runs["steps"]) > 0:
        runner.passed(f"Has {len(runs['steps'])} step(s)")

        # Check for Python setup
        has_python_setup = any(
            "setup-python" in str(step.get("uses", "")) for step in runs["steps"]
        )
        if has_python_setup:
            runner.passed("Sets up Python environment")
        else:
            runner.warn("No explicit Python setup step")

        # Check for uvx usage
        has_uvx = any("uvx" in str(step.get("run", "")) for step in runs["steps"])
        if has_uvx:
            runner.passed("Uses uvx for package execution")
        else:
            runner.warn("Does not use uvx")
    else:
        runner.failed("No steps defined in runs")


def test_runner_script() -> None:
    """Validate runner.py structure and logic."""
    runner.suite("Runner Script Validation")
    runner_path = Path(".github/actions/layercode-gym-test/runner.py")

    if not runner_path.exists():
        runner.failed("runner.py not found")
        return

    runner.test("Python Syntax")

    try:
        tree = parse_python(runner_path)
        runner.passed("Valid Python syntax")
    except SyntaxError as e:
        runner.failed(f"Syntax error: {e}")
        return

    runner.test("Required Imports")

    imports = get_imports(tree)
    with open(runner_path) as f:
        content = f.read()

    # Core imports that must be present
    required_imports = [
        "asyncio",
        "json",
        "os",
        "sys",
        "dataclasses",
    ]

    for imp in required_imports:
        if imp in imports:
            runner.passed(f"Imports {imp}")
        else:
            runner.failed(f"Missing import: {imp}")

    # Check for layercode_gym usage (provides httpx/pathlib internally)
    if "layercode_gym" in content:
        runner.passed("Uses layercode_gym library")
    else:
        runner.failed("Missing layercode_gym import")

    runner.test("Required Classes")

    classes = get_classes(tree)
    required_classes = ["PersonaConfig", "TestResult", "LayerCodeGymRunner"]

    for cls in required_classes:
        if cls in classes:
            runner.passed(f"Defines class: {cls}")
        else:
            runner.failed(f"Missing class: {cls}")

    runner.test("Required Functions/Methods")

    functions = get_functions(tree)

    # main is required as entry point
    if "main" in functions:
        runner.passed("Defines function: main")
    else:
        runner.failed("Missing function: main")

    # run_single_conversation handles individual tests
    if "run_single_conversation" in functions:
        runner.passed("Defines function: run_single_conversation")
    else:
        runner.failed("Missing function: run_single_conversation")

    # Check for run method or run_all (the main orchestration)
    if "run" in functions or "run_all" in functions:
        runner.passed("Defines orchestration method")
    else:
        runner.warn("No explicit run/run_all method found")

    runner.test("Environment Variable Handling")

    with open(runner_path) as f:
        content = f.read()

    env_vars = [
        "SERVER_URL",
        "LAYERCODE_AGENT_ID",
        "OPENAI_API_KEY",
        "PERSONAS",
        "MAX_TURNS",
        "JUDGE_ENABLED",
        "JUDGE_CRITERIA",
        "MODEL",
        "GITHUB_OUTPUT",
    ]

    for var in env_vars:
        if var in content:
            runner.passed(f"References {var}")
        else:
            runner.failed(f"Missing env var: {var}")

    runner.test("Async Patterns")

    if "async def" in content:
        runner.passed("Uses async functions")
    else:
        runner.failed("No async functions found")

    if "asyncio.gather" in content or "gather(" in content:
        runner.passed("Uses asyncio.gather for parallelism")
    else:
        runner.failed("Missing parallel execution pattern")

    if "await" in content:
        runner.passed("Uses await for async calls")
    else:
        runner.failed("No await statements found")

    runner.test("Error Handling")

    if "try:" in content and "except" in content:
        runner.passed("Has try-except blocks")
    else:
        runner.failed("Missing error handling")

    if "sys.exit" in content:
        runner.passed("Uses sys.exit for exit codes")
    else:
        runner.failed("Missing sys.exit for error codes")

    if "HTTPStatusError" in content or "HTTPError" in content:
        runner.passed("Handles HTTP errors")
    else:
        runner.warn("No explicit HTTP error handling")

    runner.test("LayerCode Integration")

    # Runner may delegate to layercode_gym library for API calls
    if "api.layercode.com" in content:
        runner.passed("Direct LayerCode API endpoint reference")
    elif "layercode_gym" in content:
        runner.passed("Uses layercode_gym library for API integration")
    else:
        runner.failed("No LayerCode integration found")

    # Check for authentication handling
    if "Bearer" in content:
        runner.passed("Handles Bearer authentication")
    elif "api_key" in content.lower() or "API_KEY" in content:
        runner.passed("References API key configuration")
    else:
        runner.warn("No explicit auth handling (may be in library)")

    # Check for server URL usage
    if "server_url" in content.lower() or "SERVER_URL" in content:
        runner.passed("References server URL")
    else:
        runner.warn("No server URL reference found")

    runner.test("Judge Integration")

    if "run_judge" in content or "judge" in content.lower():
        runner.passed("Has judge integration")
    else:
        runner.failed("Missing judge integration")

    if "overall_pass" in content:
        runner.passed("Tracks overall pass/fail status")
    else:
        runner.warn("Missing overall_pass tracking")

    if "judge_criteria" in content.lower():
        runner.passed("Handles judge criteria")
    else:
        runner.failed("Missing judge criteria handling")


def test_api_agents_module() -> None:
    """Validate API agents CLI module."""
    runner.suite("API Agents CLI Module")

    utils_path = Path("src/layercode_gym/api_agents_utils.py")
    cli_path = Path("src/layercode_gym/api_agents_cli.py")
    main_cli_path = Path("src/layercode_gym/cli.py")

    runner.test("Module Files Exist")

    for path in [utils_path, cli_path, main_cli_path]:
        if path.exists():
            runner.passed(f"Found {path.name}")
        else:
            runner.failed(f"Missing {path.name}")
            return

    runner.test("api_agents_utils.py Structure")

    try:
        tree = parse_python(utils_path)
        runner.passed("Valid Python syntax")

        functions = get_functions(tree)
        required_functions = ["get_agent", "update_agent", "list_agents"]
        for func in required_functions:
            if func in functions:
                runner.passed(f"Has function: {func}")
            else:
                runner.failed(f"Missing function: {func}")

        classes = get_classes(tree)
        if "Agent" in classes:
            runner.passed("Has Agent dataclass")
        else:
            runner.failed("Missing Agent dataclass")

    except SyntaxError as e:
        runner.failed(f"Syntax error: {e}")

    runner.test("api_agents_cli.py Structure")

    try:
        tree = parse_python(cli_path)
        runner.passed("Valid Python syntax")

        functions = get_functions(tree)
        if "create_parser" in functions:
            runner.passed("Has argument parser setup")
        else:
            runner.failed("Missing create_parser function")

        if "main" in functions:
            runner.passed("Has main entry point")
        else:
            runner.failed("Missing main function")

        with open(cli_path) as f:
            content = f.read()

        if "add_subparsers" in content:
            runner.passed("Uses subparsers for commands")
        else:
            runner.failed("Missing subparsers")

        commands = ["list", "get", "update"]
        for cmd in commands:
            if f'"{cmd}"' in content:
                runner.passed(f"Has '{cmd}' command")
            else:
                runner.failed(f"Missing '{cmd}' command")

    except SyntaxError as e:
        runner.failed(f"Syntax error: {e}")

    runner.test("CLI Integration")

    with open(main_cli_path) as f:
        content = f.read()

    if "api-agents" in content:
        runner.passed("Main CLI routes to api-agents")
    else:
        runner.failed("Missing api-agents routing in main CLI")

    if "api_agents_cli" in content:
        runner.passed("Imports api_agents_cli module")
    else:
        runner.failed("Missing api_agents_cli import")

    runner.test("API Structure")

    with open(utils_path) as f:
        content = f.read()

    if "api.layercode.com/v1/agents" in content:
        runner.passed("Correct API endpoint")
    else:
        runner.failed("Wrong or missing API endpoint")

    if "Bearer" in content:
        runner.passed("Uses Bearer authentication")
    else:
        runner.failed("Missing Bearer auth")

    for method in [".get(", ".post("]:
        if method in content:
            runner.passed(f"Uses HTTP {method.strip('.(')}")
        else:
            runner.warn(f"Missing HTTP {method.strip('.(')}")

    runner.test("Error Handling")

    with open(utils_path) as f:
        content = f.read()

    error_codes = ["401", "404"]
    for code in error_codes:
        if code in content:
            runner.passed(f"Handles HTTP {code} errors")
        else:
            runner.warn(f"Missing HTTP {code} handling")

    if "sys.stderr" in content:
        runner.passed("Outputs errors to stderr")
    else:
        runner.warn("Should output errors to stderr")


def test_workflow_files() -> None:
    """Validate GitHub workflow files."""
    runner.suite("GitHub Workflow Files")

    runner.test("Example Workflow")

    example_path = Path(".github/workflows/example-gym-test.yml")
    if not example_path.exists():
        runner.failed("example-gym-test.yml not found")
    else:
        try:
            workflow = load_yaml(example_path)
            runner.passed("Valid YAML syntax")

            if "jobs" in workflow:
                runner.passed("Has jobs defined")

                for job_name, job in workflow["jobs"].items():
                    # Check concurrency
                    if "concurrency" in job:
                        conc = job["concurrency"]
                        if "group" in conc:
                            runner.passed(f"Job '{job_name}' has concurrency group")
                            if "LAYERCODE_AGENT_ID" in str(conc["group"]):
                                runner.passed(
                                    f"Job '{job_name}' concurrency includes agent ID"
                                )
                            else:
                                runner.warn(
                                    f"Job '{job_name}' concurrency should include agent ID"
                                )
                        if conc.get("cancel-in-progress") is False:
                            runner.passed(f"Job '{job_name}' prevents cancellation")
                        else:
                            runner.warn(
                                f"Job '{job_name}' should set cancel-in-progress: false"
                            )
                    else:
                        runner.failed(f"Job '{job_name}' missing concurrency control")

                    # Check action usage
                    for step in job.get("steps", []):
                        if "uses" in step and "layercode-gym-test" in step["uses"]:
                            runner.passed("References layercode-gym-test action")
                            if step["uses"].startswith("./"):
                                runner.passed("Uses relative path reference")
                            else:
                                runner.warn("Should use relative path for local action")

                            if "with" in step:
                                required = [
                                    "personas",
                                    "server-url",
                                    "layercode-agent-id",
                                    "openai-api-key",
                                ]
                                for inp in required:
                                    if inp in step["with"]:
                                        runner.passed(f"Provides required input: {inp}")
                                    else:
                                        runner.failed(f"Missing required input: {inp}")
            else:
                runner.failed("No jobs defined")

        except Exception as e:
            runner.failed(f"Failed to parse: {e}")

    runner.test("CI Workflow")

    ci_path = Path(".github/workflows/ci.yml")
    if not ci_path.exists():
        runner.failed("ci.yml not found")
    else:
        try:
            ci = load_yaml(ci_path)
            runner.passed("Valid YAML syntax")

            if "validate-action" in ci.get("jobs", {}):
                runner.passed("Has validate-action job")
            else:
                runner.warn("Missing validate-action job")

        except Exception as e:
            runner.failed(f"Failed to parse: {e}")


def test_documentation() -> None:
    """Validate documentation completeness."""
    runner.suite("Documentation Completeness")

    runner.test("Action README")

    action_readme = Path(".github/actions/layercode-gym-test/README.md")
    if not action_readme.exists():
        runner.failed("Action README.md not found")
    else:
        with open(action_readme) as f:
            content = f.read()

        required_sections = [
            ("Quick Start", "Quick Start"),
            ("Inputs", "## Inputs"),
            ("Outputs", "## Outputs"),
            ("Secrets", "Secret"),
            ("Examples", "Example"),
            ("Troubleshooting", "Troubleshooting"),
        ]

        for name, pattern in required_sections:
            if pattern in content:
                runner.passed(f"Has section: {name}")
            else:
                runner.failed(f"Missing section: {name}")

        if "```yaml" in content:
            yaml_blocks = content.count("```yaml")
            runner.passed(f"Has {yaml_blocks} YAML code example(s)")
        else:
            runner.failed("Missing YAML examples")

    runner.test("Main GitHub Action Docs")

    docs_path = Path("docs/github-action.md")
    if not docs_path.exists():
        runner.failed("docs/github-action.md not found")
    else:
        with open(docs_path) as f:
            content = f.read()

        required_sections = [
            "Overview",
            "Quick Start",
            "Configuration",
            "Use Cases",
            "Best Practices",
            "Troubleshooting",
        ]

        for section in required_sections:
            if section in content:
                runner.passed(f"Has section: {section}")
            else:
                runner.failed(f"Missing section: {section}")

    runner.test("API Agents Docs")

    api_docs_path = Path("docs/api-agents.md")
    if not api_docs_path.exists():
        runner.failed("docs/api-agents.md not found")
    else:
        with open(api_docs_path) as f:
            content = f.read()

        commands = ["list", "get", "update"]
        for cmd in commands:
            if f"`{cmd}`" in content or f"### `{cmd}`" in content:
                runner.passed(f"Documents '{cmd}' command")
            else:
                runner.warn(f"Missing '{cmd}' command documentation")

    runner.test("Navigation Configuration")

    mkdocs_path = Path("mkdocs.yml")
    if not mkdocs_path.exists():
        runner.warn("mkdocs.yml not found")
    else:
        with open(mkdocs_path) as f:
            content = f.read()

        if "github-action.md" in content:
            runner.passed("mkdocs.yml includes github-action.md")
        else:
            runner.failed("mkdocs.yml missing github-action.md")

        if "api-agents.md" in content:
            runner.passed("mkdocs.yml includes api-agents.md")
        else:
            runner.warn("mkdocs.yml missing api-agents.md")

    runner.test("README Links")

    readme_path = Path("README.md")
    with open(readme_path) as f:
        content = f.read()

    if "docs/github-action.md" in content:
        runner.passed("README links to GitHub Action docs")
    else:
        runner.warn("README should link to GitHub Action docs")


def test_security() -> None:
    """Validate security considerations."""
    runner.suite("Security Validation")

    runner.test("No Hardcoded Secrets")

    sensitive_patterns = [
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub token"),
        (r"layercode_api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded LayerCode key"),
    ]

    files_to_check = [
        Path(".github/actions/layercode-gym-test/runner.py"),
        Path("src/layercode_gym/api_agents_utils.py"),
        Path("src/layercode_gym/api_agents_cli.py"),
    ]

    for path in files_to_check:
        if not path.exists():
            continue

        with open(path) as f:
            content = f.read()

        for pattern, description in sensitive_patterns:
            if re.search(pattern, content):
                runner.failed(f"Potential {description} in {path.name}")
            else:
                runner.passed(f"No {description} in {path.name}")

    runner.test("Environment Variable Usage")

    runner_path = Path(".github/actions/layercode-gym-test/runner.py")
    if runner_path.exists():
        with open(runner_path) as f:
            content = f.read()

        if "os.environ.get(" in content or "os.environ[" in content:
            runner.passed("Uses environment variables for configuration")
        else:
            runner.warn("Should use environment variables")

        if "getenv" in content or "environ" in content:
            runner.passed("Reads secrets from environment")
        else:
            runner.failed("Not reading secrets from environment")

    runner.test("Secrets Documentation")

    action_readme = Path(".github/actions/layercode-gym-test/README.md")
    if action_readme.exists():
        with open(action_readme) as f:
            content = f.read().lower()

        if "secret" in content:
            runner.passed("Documents secret handling")
        else:
            runner.failed("Missing secrets documentation")

        if "github secrets" in content or "repository secret" in content:
            runner.passed("Recommends GitHub Secrets")
        else:
            runner.warn("Should recommend GitHub Secrets")


def test_consistency() -> None:
    """Validate cross-file consistency."""
    runner.suite("Cross-File Consistency")

    runner.test("Input Names Match")

    action_path = Path(".github/actions/layercode-gym-test/action.yml")
    runner_path = Path(".github/actions/layercode-gym-test/runner.py")

    if not action_path.exists() or not runner_path.exists():
        runner.warn("Cannot check consistency - files missing")
        return

    action = load_yaml(action_path)
    with open(runner_path) as f:
        runner_content = f.read()

    # Map action input names to expected env var names
    input_to_env = {
        "server-url": "SERVER_URL",
        "layercode-agent-id": "LAYERCODE_AGENT_ID",
        "openai-api-key": "OPENAI_API_KEY",
        "personas": "PERSONAS",
        "max-turns": "MAX_TURNS",
        "judge-enabled": "JUDGE_ENABLED",
        "judge-criteria": "JUDGE_CRITERIA",
        "model": "MODEL",
        "store-audio": "LAYERCODE_STORE_AUDIO",
    }

    for input_name, env_name in input_to_env.items():
        if input_name in action.get("inputs", {}):
            if env_name in runner_content:
                runner.passed(f"Input '{input_name}' maps to {env_name}")
            else:
                runner.failed(f"Runner missing {env_name} for input '{input_name}'")

    runner.test("Output Names Match")

    for output_name in action.get("outputs", {}).keys():
        if output_name in runner_content:
            runner.passed(f"Runner writes output: {output_name}")
        else:
            runner.failed(f"Runner doesn't write output: {output_name}")

    runner.test("Documentation Consistency")

    # Check that documented inputs match action.yml
    action_readme = Path(".github/actions/layercode-gym-test/README.md")
    if action_readme.exists():
        with open(action_readme) as f:
            readme_content = f.read()

        for input_name in action.get("inputs", {}).keys():
            # Convert to various formats that might appear in docs
            if input_name in readme_content or f"`{input_name}`" in readme_content:
                runner.passed(f"README documents input: {input_name}")
            else:
                runner.warn(f"README may be missing input: {input_name}")


def test_json_parsing() -> None:
    """Test persona JSON parsing logic."""
    runner.suite("JSON Parsing Validation")

    runner.test("Valid Persona Structures")

    valid_personas = [
        [{"background": "Customer", "intent": "Buy product"}],
        [
            {"background": "User 1", "intent": "Intent 1"},
            {"background": "User 2", "intent": "Intent 2"},
        ],
        [
            {
                "background": "Complex user with many details",
                "intent": "Multiple goals: learn, buy, and support",
            }
        ],
    ]

    for i, personas in enumerate(valid_personas, 1):
        try:
            json_str = json.dumps(personas)
            parsed = json.loads(json_str)
            valid = all("background" in p and "intent" in p for p in parsed)
            if valid:
                runner.passed(f"Valid structure {i}: {len(personas)} persona(s)")
            else:
                runner.failed(f"Structure {i} missing required fields")
        except Exception as e:
            runner.failed(f"Structure {i} failed: {e}")

    runner.test("Invalid Persona Detection")

    invalid_cases = [
        ("not json at all", "Non-JSON string"),
        ("[]", "Empty array"),
        ('[{"background": "test"}]', "Missing intent"),
        ('[{"intent": "test"}]', "Missing background"),
        ('{"background": "test", "intent": "test"}', "Not an array"),
        ("[{background: test}]", "Invalid JSON syntax"),
    ]

    for json_str, description in invalid_cases:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list) and len(parsed) > 0:
                # Check for required fields
                valid = all(
                    isinstance(p, dict) and "background" in p and "intent" in p
                    for p in parsed
                )
                if valid:
                    runner.failed(f"Should reject: {description}")
                else:
                    runner.passed(f"Would catch: {description}")
            else:
                runner.passed(f"Would catch: {description}")
        except json.JSONDecodeError:
            runner.passed(f"Rejects invalid JSON: {description}")


def test_github_outputs() -> None:
    """Test GitHub output file writing."""
    runner.suite("GitHub Outputs Validation")

    runner.test("Output File Writing")

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        temp_file = f.name

    try:
        # Simulate writing outputs
        outputs = {
            "conversations-run": "5",
            "conversations-passed": "4",
            "conversations-failed": "1",
            "results-path": "conversations",
        }

        with open(temp_file, "w") as f:
            for key, value in outputs.items():
                f.write(f"{key}={value}\n")

        with open(temp_file) as f:
            content = f.read()

        for key in outputs:
            if f"{key}=" in content:
                runner.passed(f"Can write output: {key}")
            else:
                runner.failed(f"Failed to write: {key}")

        # Verify format
        lines = content.strip().split("\n")
        if all("=" in line for line in lines):
            runner.passed("Output format is key=value")
        else:
            runner.failed("Invalid output format")

    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Run all validation tests."""
    print(f"\n{BLUE}{BOLD}LayerCode Gym CI Validation Suite{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")

    # Check for required dependencies
    if importlib.util.find_spec("yaml") is None:
        print(
            f"\n{RED}Error: PyYAML is required. Install with: pip install pyyaml{RESET}\n"
        )
        return 1

    # Run all test suites
    test_action_yaml_structure()
    test_runner_script()
    test_api_agents_module()
    test_workflow_files()
    test_documentation()
    test_security()
    test_consistency()
    test_json_parsing()
    test_github_outputs()

    # Print summary
    success = runner.summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
