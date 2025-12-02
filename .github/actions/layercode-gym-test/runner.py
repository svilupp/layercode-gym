#!/usr/bin/env python
"""
GitHub Action runner script for LayerCode Gym tests.

This script orchestrates batch persona testing with optional judging:
1. Configures webhook URL via LayerCode REST API
2. Runs multiple personas in parallel
3. Evaluates with LLM judge (optional)
4. Reports results and sets GitHub Action outputs
"""

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass

from tqdm.asyncio import tqdm_asyncio


# Patterns for sensitive data that should be redacted from error messages
_SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OpenAI API keys: sk-... or sk-proj-...
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_OPENAI_KEY]"),
    # Logfire tokens: pylf_...
    (re.compile(r"\bpylf_[A-Za-z0-9_-]+\b"), "[REDACTED_LOGFIRE_TOKEN]"),
    # Bearer tokens in headers
    (re.compile(r"Bearer\s+[A-Za-z0-9_.-]+", re.IGNORECASE), "Bearer [REDACTED]"),
    # Authorization header values
    (
        re.compile(r"['\"]?Authorization['\"]?\s*:\s*['\"]?[^'\"}\s]+", re.IGNORECASE),
        "'Authorization': '[REDACTED]'",
    ),
    # Generic API key patterns in headers/URLs
    (
        re.compile(
            r"['\"]?api[_-]?key['\"]?\s*[=:]\s*['\"]?[A-Za-z0-9_.-]+", re.IGNORECASE
        ),
        "api_key=[REDACTED]",
    ),
    # X-API-Key header
    (
        re.compile(r"['\"]?X-API-Key['\"]?\s*:\s*['\"]?[^'\"}\s]+", re.IGNORECASE),
        "'X-API-Key': '[REDACTED]'",
    ),
    # password/secret fields
    (
        re.compile(
            r"['\"]?(?:password|secret)['\"]?\s*[=:]\s*['\"]?[^'\"}\s]+", re.IGNORECASE
        ),
        "password=[REDACTED]",
    ),
]


def sanitize_error(error: BaseException | str) -> str:
    """Sanitize an error message by redacting sensitive information."""
    text = str(error)
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


@dataclass
class PersonaConfig:
    """Configuration for a single persona test."""

    background: str
    intent: str


@dataclass
class TestResult:
    """Result of a single conversation test."""

    persona_index: int
    conversation_id: str
    passed: bool | None = None  # None if judge not enabled
    judge_feedback: str = ""


class LayerCodeGymRunner:
    """Orchestrates LayerCode Gym tests for CI."""

    def __init__(self) -> None:
        """Initialize runner with environment configuration."""
        # Required settings
        self.server_url = os.environ["SERVER_URL"]
        self.agent_id = os.environ["LAYERCODE_AGENT_ID"]
        self.openai_api_key = os.environ["OPENAI_API_KEY"]

        # Optional settings
        self.logfire_token = os.environ.get("LOGFIRE_TOKEN", "")

        # Test configuration
        self.personas_json = os.environ["PERSONAS"]
        self.max_turns = int(os.environ.get("MAX_TURNS", "5"))
        self.judge_enabled = os.environ.get("JUDGE_ENABLED", "false").lower() == "true"
        self.judge_criteria: list[str] = self._parse_judge_criteria(
            os.environ.get("JUDGE_CRITERIA", "[]")
        )
        self.fail_on_judge_failure = (
            os.environ.get("FAIL_ON_JUDGE_FAILURE", "true").lower() == "true"
        )
        self.model = os.environ.get("MODEL", "openai:gpt-4o-mini")
        self.store_audio = (
            os.environ.get("LAYERCODE_STORE_AUDIO", "false").lower() == "true"
        )

        # Parse personas
        self.personas = self._parse_personas()

        # Set GitHub output file
        self.github_output = os.environ.get("GITHUB_OUTPUT", "")

    def _parse_personas(self) -> list[PersonaConfig]:
        """Parse personas JSON from environment."""
        try:
            personas_data = json.loads(self.personas_json)
            return [
                PersonaConfig(background=p["background"], intent=p["intent"])
                for p in personas_data
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error parsing personas JSON: {e}", file=sys.stderr)
            print(f"Expected format: {self._example_personas_json()}", file=sys.stderr)
            sys.exit(1)

    @staticmethod
    def _example_personas_json() -> str:
        """Return example personas JSON format."""
        return json.dumps(
            [
                {
                    "background": "You are a 35-year-old small business owner",
                    "intent": "Learn about voice AI capabilities",
                }
            ],
            indent=2,
        )

    def _parse_judge_criteria(self, criteria_text: str) -> list[str]:
        """Parse judge criteria from YAML list format.

        Accepts YAML-style list with "- " prefix per line:
            - Did the agent greet the user?
            - Did the agent provide accurate info?

        Args:
            criteria_text: Multi-line string with YAML list items

        Returns:
            List of criteria strings
        """
        if not criteria_text or criteria_text.strip() == "":
            return []

        criteria: list[str] = []
        for line in criteria_text.strip().splitlines():
            line = line.strip()
            if line.startswith("- "):
                criterion = line[2:].strip()
                if criterion:
                    criteria.append(criterion)
            elif line and not line.startswith("#"):
                # Non-empty, non-comment line without "- " prefix
                print(
                    f"⚠️  Warning: judge-criteria line missing '- ' prefix: {line}",
                    file=sys.stderr,
                )
        return criteria

    async def run_single_conversation(
        self, persona_index: int, persona: PersonaConfig
    ) -> TestResult:
        """Run a single conversation with a persona.

        Args:
            persona_index: Index of the persona in the list
            persona: Persona configuration

        Returns:
            TestResult with conversation ID and optional judge result
        """
        # Import here to avoid issues with uvx installation timing
        from layercode_gym import LayercodeClient, Persona, Settings, UserSimulator

        # Create persona
        gym_persona = Persona(
            background_context=persona.background,
            intent=persona.intent,
        )

        # Create simulator
        simulator = UserSimulator.from_agent(
            persona=gym_persona,
            max_turns=self.max_turns,
            send_as_text=True,  # Use text for faster CI execution
            model=self.model,
        )

        # Load settings (will use env vars we set)
        settings = Settings.load()

        # Create client
        client = LayercodeClient(simulator=simulator, settings=settings)

        # Run conversation
        conversation_id = await client.run()

        return TestResult(
            persona_index=persona_index,
            conversation_id=conversation_id,
        )

    async def run_judge(self, result: TestResult) -> TestResult:
        """Run judge evaluation on a conversation using CriteriaJudge.

        Args:
            result: TestResult with conversation_id

        Returns:
            TestResult updated with judge evaluation
        """
        print(f"   🔍 Judging conversation {result.conversation_id}...")

        # Import here to avoid issues with uvx installation timing
        from layercode_gym import Settings
        from layercode_gym.agents.judge import CriteriaJudge
        from layercode_gym.models.conversation import ConversationLog

        # Load conversation log
        settings = Settings.load()
        conv_dir = settings.output_root / result.conversation_id
        transcript_file = conv_dir / "transcript.json"

        if not transcript_file.exists():
            print(f"   ⚠️  Transcript not found for {result.conversation_id}")
            result.passed = False
            result.judge_feedback = "Transcript not found"
            return result

        # Parse transcript
        with open(transcript_file) as f:
            log_data = json.load(f)
            log = ConversationLog(**log_data)

        # Use default criterion if none provided
        criteria = self.judge_criteria or [
            "Did the assistant provide helpful and accurate information?"
        ]

        try:
            # Create CriteriaJudge with the list of criteria
            judge = CriteriaJudge(
                criteria=criteria,
                model=self.model,
            )

            # Evaluate the conversation
            evaluation = await judge.evaluate(log)

            # Use overall_pass from judge output
            result.passed = evaluation.overall_pass
            result.judge_feedback = evaluation.reasoning

            # Save results using CriteriaJudge's built-in method
            judge.save_results(evaluation, result.conversation_id, settings.output_root)

        except Exception as e:
            # Sanitize error to prevent leaking API keys in CI logs
            safe_error = sanitize_error(e)
            print(f"   ⚠️  Judge evaluation failed: {safe_error}")
            result.passed = False
            result.judge_feedback = f"Judge error: {safe_error}"

        return result

    async def run_all_conversations(self) -> list[TestResult]:
        """Run all persona conversations in parallel.

        Returns:
            List of TestResults
        """
        print(f"\n🚀 Running {len(self.personas)} conversations in parallel...")
        print("=" * 70)

        # Create tasks for all personas
        tasks = [
            self.run_single_conversation(i, persona)
            for i, persona in enumerate(self.personas)
        ]

        # Run with progress bar
        results = await tqdm_asyncio.gather(
            *tasks, desc="Running conversations", unit="conv"
        )

        print("=" * 70)
        print("✅ All conversations complete!")

        return results

    async def run_all_judges(self, results: list[TestResult]) -> list[TestResult]:
        """Run judge evaluations on all conversations.

        Args:
            results: List of TestResults from conversations

        Returns:
            Updated list of TestResults with judge evaluations
        """
        if not self.judge_enabled:
            return results

        print("\n🏛️  Running judge evaluations...")
        print("=" * 70)

        # Run judges in parallel
        tasks = [self.run_judge(result) for result in results]
        results = await tqdm_asyncio.gather(
            *tasks, desc="Judging conversations", unit="eval"
        )

        print("=" * 70)
        print("✅ All evaluations complete!")

        return results

    def print_summary(self, results: list[TestResult]) -> None:
        """Print test summary and set GitHub Action outputs."""
        print("\n" + "=" * 70)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 70)

        total = len(results)
        passed = sum(1 for r in results if r.passed is True)
        failed = sum(1 for r in results if r.passed is False)

        print(f"\n📈 Conversations Run: {total}")

        if self.judge_enabled:
            print(f"✅ Passed: {passed}")
            print(f"❌ Failed: {failed}")

            print("\n📋 Details:")
            for i, result in enumerate(results, 1):
                status = "✅ PASS" if result.passed else "❌ FAIL"
                print(f"   {i}. Persona {result.persona_index + 1}: {status}")
                print(f"      Conversation: {result.conversation_id}")
                if result.judge_feedback:
                    feedback_preview = (
                        result.judge_feedback[:100] + "..."
                        if len(result.judge_feedback) > 100
                        else result.judge_feedback
                    )
                    print(f"      Feedback: {feedback_preview}")

        else:
            print("ℹ️  Judge not enabled - no pass/fail evaluation")
            for i, result in enumerate(results, 1):
                print(f"   {i}. Conversation: {result.conversation_id}")

        print("\n📁 Results Location: ./conversations/")
        print("=" * 70)

        # Set GitHub Action outputs
        if self.github_output:
            with open(self.github_output, "a") as f:
                f.write(f"conversations-run={total}\n")
                f.write(f"conversations-passed={passed}\n")
                f.write(f"conversations-failed={failed}\n")
                f.write("results-path=conversations\n")

    def determine_exit_code(self, results: list[TestResult]) -> int:
        """Determine exit code based on results.

        Args:
            results: List of TestResults

        Returns:
            0 for success, 1 for failure
        """
        if not self.judge_enabled:
            # No judge = always pass
            return 0

        if not self.fail_on_judge_failure:
            # Judge enabled but don't fail CI
            return 0

        # Fail if any conversation failed
        if any(r.passed is False for r in results):
            print("\n❌ Some conversations failed judge evaluation")
            return 1

        print("\n✅ All conversations passed!")
        return 0

    async def run(self) -> int:
        """Execute the full test workflow.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        print("=" * 70)
        print("🎯 LayerCode Gym CI Test Runner")
        print("=" * 70)
        print("\nConfiguration:")
        print(f"  • Agent ID: {self.agent_id}")
        print(f"  • Server URL: {self.server_url}")
        print(f"  • Personas: {len(self.personas)}")
        print(f"  • Max Turns: {self.max_turns}")
        print(f"  • Model: {self.model}")
        print(f"  • Store Audio: {self.store_audio}")
        print(f"  • Judge Enabled: {self.judge_enabled}")
        if self.judge_enabled:
            print(f"  • Fail on Judge Failure: {self.fail_on_judge_failure}")
            criteria_count = len(self.judge_criteria)
            print(f"  • Judge Criteria: {criteria_count} criterion(s)")
            for i, criterion in enumerate(self.judge_criteria, 1):
                print(f"      {i}. {criterion}")
        if self.logfire_token:
            print("  • LogFire: Enabled ✓")

        print(
            "\n💡 Note: Configure webhook before running tests using:\n"
            f"   layercode-gym api-agents update --agent-id {self.agent_id} "
            f"--webhook-url {self.server_url}/api/webhook\n"
        )

        # Run conversations
        results = await self.run_all_conversations()

        # Run judges if enabled
        results = await self.run_all_judges(results)

        # Print summary and set outputs
        self.print_summary(results)

        # Return exit code
        return self.determine_exit_code(results)


async def main() -> None:
    """Main entry point."""
    runner = LayerCodeGymRunner()
    exit_code = await runner.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
