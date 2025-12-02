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
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tqdm.asyncio import tqdm_asyncio


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
        self.layercode_api_key = os.environ["LAYERCODE_API_KEY"]
        self.openai_api_key = os.environ["OPENAI_API_KEY"]

        # Optional settings
        self.logfire_token = os.environ.get("LOGFIRE_TOKEN", "")

        # Test configuration
        self.personas_json = os.environ["PERSONAS"]
        self.max_turns = int(os.environ.get("MAX_TURNS", "5"))
        self.judge_enabled = os.environ.get("JUDGE_ENABLED", "false").lower() == "true"
        self.judge_criteria = os.environ.get("JUDGE_CRITERIA", "")
        self.fail_on_judge_failure = (
            os.environ.get("FAIL_ON_JUDGE_FAILURE", "true").lower() == "true"
        )
        self.model = os.environ.get("MODEL", "openai:gpt-4o-mini")

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

    async def configure_webhook(self) -> None:
        """Configure webhook URL via LayerCode REST API.

        This ensures the agent sends events to the correct backend server.
        Note: LayerCode agents support one webhook at a time.
        """
        print("🔧 Configuring webhook URL...")

        webhook_url = f"{self.server_url}/api/webhook"
        api_url = f"https://api.layercode.com/v1/agents/{self.agent_id}/webhook"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {self.layercode_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"url": webhook_url},
                    timeout=30.0,
                )
                response.raise_for_status()
                print(f"✅ Webhook configured: {webhook_url}")
            except httpx.HTTPError as e:
                print(f"❌ Failed to configure webhook: {e}", file=sys.stderr)
                print(
                    "   Check your LAYERCODE_API_KEY and LAYERCODE_AGENT_ID",
                    file=sys.stderr,
                )
                sys.exit(1)

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
        """Run judge evaluation on a conversation.

        NOTE: This implements the FUTURE judge interface as described by the user.
        The next version of layercode-gym will have:
        - A built-in judge that takes string criteria
        - Returns result.output.overall_pass (bool)

        For now, this is a placeholder implementation.

        Args:
            result: TestResult with conversation_id

        Returns:
            TestResult updated with judge evaluation
        """
        print(f"   🔍 Judging conversation {result.conversation_id}...")

        # TODO: Replace this with actual judge when available in next gym version
        # Expected usage:
        #   from layercode_gym import ConversationJudge
        #   judge = ConversationJudge(criteria=self.judge_criteria)
        #   evaluation = await judge.evaluate(conversation_id)
        #   overall_pass = evaluation.output.overall_pass

        # For now, implement a basic judge using the pattern from example 04
        from layercode_gym import Settings
        from layercode_gym.models.conversation import ConversationLog
        from pydantic import BaseModel
        from pydantic_ai import Agent

        # Define judge result format (future interface)
        class JudgeResult(BaseModel):
            """Future judge interface: simple pass/fail with criteria."""

            overall_pass: bool
            feedback: str

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

        # Build transcript
        transcript_parts = []
        for i, turn in enumerate(log.turns):
            if turn.assistant_message:
                transcript_parts.append(
                    f"[Turn {i}] ASSISTANT: {turn.assistant_message.content or '(audio only)'}"
                )
            if turn.user_message:
                transcript_parts.append(
                    f"[Turn {i}] USER: {turn.user_message.content or '(audio only)'}"
                )

        transcript = "\n".join(transcript_parts)

        # Create judge agent
        judge_agent: Agent[None, JudgeResult] = Agent(
            self.model,
            result_type=JudgeResult,
            system_prompt=(
                "You are an expert evaluator of conversational AI systems. "
                "Evaluate the ASSISTANT's performance based on the provided criteria. "
                "Return a simple pass/fail decision with brief feedback."
            ),
        )

        # Evaluate
        criteria_prompt = self.judge_criteria or "The assistant provided helpful and accurate information"
        prompt = f"""Evaluate this conversation based on the following criteria:

{criteria_prompt}

Conversation transcript:
{transcript}

Did the assistant meet the criteria? Provide a pass/fail decision and brief feedback."""

        try:
            agent_result = await judge_agent.run(prompt)
            evaluation = agent_result.data

            result.passed = evaluation.overall_pass
            result.judge_feedback = evaluation.feedback

            # Save judge results
            judge_file = conv_dir / "judge_evaluation.json"
            judge_file.write_text(
                json.dumps(
                    {
                        "criteria": criteria_prompt,
                        "overall_pass": evaluation.overall_pass,
                        "feedback": evaluation.feedback,
                    },
                    indent=2,
                )
            )

        except Exception as e:
            print(f"   ⚠️  Judge evaluation failed: {e}")
            result.passed = False
            result.judge_feedback = f"Judge error: {e}"

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

        print(f"\n🏛️  Running judge evaluations...")
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
                        result.judge_feedback[:100]
                        + "..."
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
        print(f"\nConfiguration:")
        print(f"  • Agent ID: {self.agent_id}")
        print(f"  • Server URL: {self.server_url}")
        print(f"  • Personas: {len(self.personas)}")
        print(f"  • Max Turns: {self.max_turns}")
        print(f"  • Model: {self.model}")
        print(f"  • Judge Enabled: {self.judge_enabled}")
        if self.judge_enabled:
            print(f"  • Fail on Judge Failure: {self.fail_on_judge_failure}")
            print(f"  • Judge Criteria: {self.judge_criteria or '(default)'}")
        if self.logfire_token:
            print(f"  • LogFire: Enabled ✓")

        # Configure webhook
        await self.configure_webhook()

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
