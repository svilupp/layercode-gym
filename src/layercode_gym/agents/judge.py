from __future__ import annotations

"""Criteria-based conversation judge using LLM-as-Judge pattern."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import httpx
import textprompts
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import Agent, ModelHTTPError, ModelRetry, RunContext
from pydantic_ai.models.fallback import FallbackModel

from ..models.conversation import ConversationLog


@dataclass(slots=True, frozen=True)
class CriterionResult:
    """Result for a single evaluation criterion.

    Attributes:
        criterion_id: The ID of the criterion (1-indexed, matches input order)
        passed: Whether the criterion was satisfied
    """

    criterion_id: int
    passed: bool


class CriterionResultItem(BaseModel):
    """A single criterion evaluation result."""

    criterion_id: int = Field(
        description="The criterion ID number (1, 2, 3, etc.) matching the input criteria order"
    )
    passed: bool = Field(
        description="Whether this specific criterion passed (true) or failed (false)"
    )


class JudgeOutput(BaseModel):
    """Structured output from the criteria judge.

    IMPORTANT: criteria_results MUST be provided first. Generate this array
    before writing reasoning. All three fields are REQUIRED.
    """

    criteria_results: list[CriterionResultItem] = Field(
        description=(
            "REQUIRED FIRST: Generate this array BEFORE reasoning. "
            "Must have EXACTLY one entry per criterion with 'criterion_id' (int) and 'passed' (bool). "
            "Example for 3 criteria: "
            "[{'criterion_id': 1, 'passed': true}, {'criterion_id': 2, 'passed': false}, {'criterion_id': 3, 'passed': true}]"
        )
    )

    overall_pass: bool = Field(
        description="True ONLY if ALL criteria in criteria_results passed, otherwise false"
    )

    reasoning: str = Field(
        description=(
            "Brief 1-2 sentence summary AFTER you've filled criteria_results. "
            "Do NOT list per-criterion details here - those are already in criteria_results."
        )
    )


@dataclass
class JudgeDeps:
    """Dependencies for the criteria judge agent."""

    criteria: Sequence[str]
    additional_context: str | None
    template: textprompts.Prompt


class CriteriaJudge:
    """LLM-as-Judge for evaluating conversations against user-defined criteria.

    Evaluates voice agent conversations against a list of true/false criteria,
    providing reasoning, individual results, and an overall pass/fail determination.

    The judge uses a structured approach:
    1. User provides criteria as a list of questions that can be answered true/false
    2. Each criterion gets an ID (1-indexed) for reference in output
    3. Judge evaluates the conversation and returns:
       - reasoning: Explanation of the evaluation
       - criteria_results: Pass/fail for each criterion by ID
       - overall_pass: True only if ALL criteria passed

    Example:
        ```python
        judge = CriteriaJudge(
            criteria=[
                "Did the assistant greet the user appropriately?",
                "Did the assistant correctly use available tools?",
                "Did the assistant handle out-of-scope requests gracefully?",
            ],
            additional_context="The user was calling to place an order for pickup.",
        )

        result = await judge.evaluate(conversation_log)
        print(f"Overall: {'PASS' if result.overall_pass else 'FAIL'}")
        print(f"Reasoning: {result.reasoning}")

        for cr in result.criteria_results:
            print(f"  Criterion {cr['criterion_id']}: {'PASS' if cr['passed'] else 'FAIL'}")
        ```

    Attributes:
        criteria: List of evaluation criteria (questions answerable as true/false)
        additional_context: Optional context about the user's intent or call purpose
        model: LLM model to use for evaluation (default: gpt-5)
    """

    def __init__(
        self,
        criteria: Sequence[str],
        *,
        additional_context: str | None = None,
        model: str = "openai:gpt-5",
    ) -> None:
        """Initialize the criteria judge.

        Args:
            criteria: List of evaluation criteria as true/false questions
            additional_context: Optional extra context (user intent, call purpose, etc.)
            model: LLM model to use (default: gpt-5 for high accuracy)
        """
        if not criteria:
            msg = "At least one criterion is required"
            raise ValueError(msg)

        self.criteria = list(criteria)
        self.additional_context = additional_context
        self.model = model
        self._template = self._load_template()
        self._agent = self._create_agent()

    def _load_template(self) -> textprompts.Prompt:
        """Load the judge prompt template."""
        prompt_path = Path(__file__).parent / "prompts" / "criteria_judge.txt"
        return textprompts.load_prompt(prompt_path, meta="strict")

    def _create_agent(self) -> Agent[JudgeDeps, JudgeOutput]:
        """Create the PydanticAI agent for evaluation."""
        # Use FallbackModel to retry on transient API errors
        # Tripling the model provides automatic retries for network/API issues
        fallback_model = FallbackModel(
            self.model,
            self.model,
            self.model,
            fallback_on=(ModelHTTPError, ValidationError, httpx.TimeoutException),
        )

        agent: Agent[JudgeDeps, JudgeOutput] = Agent(
            fallback_model,
            deps_type=JudgeDeps,
            output_type=JudgeOutput,
            retries=3,  # Allow retries for structured output validation
        )

        @agent.system_prompt
        def build_system_prompt(ctx: RunContext[JudgeDeps]) -> str:
            """Build the system prompt with criteria."""
            template = ctx.deps.template
            criteria = ctx.deps.criteria
            additional_context = ctx.deps.additional_context

            # Format criteria with XML IDs for clear referencing
            criteria_xml = "\n".join(
                f'<criterion id="{i + 1}">{c}</criterion>'
                for i, c in enumerate(criteria)
            )

            # Format additional context (empty string if None)
            context_section = ""
            if additional_context:
                context_section = f"\n<additional_context>\n{additional_context}\n</additional_context>"

            return template.prompt.format(
                criteria_xml=criteria_xml,
                additional_context=context_section,
            )

        @agent.output_validator
        def validate_criteria_results(
            ctx: RunContext[JudgeDeps], output: JudgeOutput
        ) -> JudgeOutput:
            """Validate that criteria_results matches expected criteria."""
            criteria = ctx.deps.criteria
            expected_count = len(criteria)
            results = output.criteria_results

            # Check count
            if len(results) != expected_count:
                raise ModelRetry(
                    f"ERROR: criteria_results has {len(results)} items but there are "
                    f"{expected_count} criteria. You MUST provide exactly {expected_count} "
                    f"items in criteria_results, one for each criterion (IDs 1 through {expected_count})."
                )

            # Extract IDs and check for issues
            ids = [r.criterion_id for r in results]
            id_set = set(ids)

            # Check for duplicates
            if len(id_set) != len(ids):
                duplicates = [x for x in ids if ids.count(x) > 1]
                raise ModelRetry(
                    f"ERROR: criteria_results contains duplicate criterion_ids: {duplicates}. "
                    f"Each criterion_id must appear exactly once. "
                    f"Required IDs are 1 through {expected_count}."
                )

            # Check for invalid IDs (must be 1 to expected_count)
            expected_ids = set(range(1, expected_count + 1))
            missing_ids = expected_ids - id_set
            extra_ids = id_set - expected_ids

            if missing_ids or extra_ids:
                error_parts = []
                if missing_ids:
                    error_parts.append(f"missing criterion_ids: {sorted(missing_ids)}")
                if extra_ids:
                    error_parts.append(f"invalid criterion_ids: {sorted(extra_ids)}")
                raise ModelRetry(
                    f"ERROR: criteria_results has {', '.join(error_parts)}. "
                    f"You MUST include exactly criterion_ids 1 through {expected_count}, "
                    f"one for each input criterion."
                )

            return output

        return agent

    async def evaluate(self, log: ConversationLog) -> JudgeOutput:
        """Evaluate a conversation against the defined criteria.

        Args:
            log: The conversation log to evaluate

        Returns:
            JudgeOutput with reasoning, individual results, and overall pass
        """
        # Build conversation transcript
        transcript_parts = []
        for i, turn in enumerate(log.turns):
            if turn.assistant_message:
                content = turn.assistant_message.content or "(audio only)"
                transcript_parts.append(f"[Turn {i + 1}] ASSISTANT: {content}")
            if turn.user_message:
                content = turn.user_message.content or "(audio only)"
                transcript_parts.append(f"[Turn {i + 1}] USER: {content}")

        transcript = "\n".join(transcript_parts)

        # Create deps
        deps = JudgeDeps(
            criteria=self.criteria,
            additional_context=self.additional_context,
            template=self._template,
        )

        # Run evaluation
        result = await self._agent.run(
            f"Evaluate this conversation:\n\n{transcript}",
            deps=deps,
        )

        return result.output

    def get_criterion_results(self, output: JudgeOutput) -> list[CriterionResult]:
        """Convert raw output to typed CriterionResult objects.

        Args:
            output: The JudgeOutput from evaluate()

        Returns:
            List of CriterionResult with typed criterion_id and passed fields
        """
        return [
            CriterionResult(
                criterion_id=cr.criterion_id,
                passed=cr.passed,
            )
            for cr in output.criteria_results
        ]

    def save_results(
        self,
        output: JudgeOutput,
        conversation_id: str,
        output_root: Path,
    ) -> Path:
        """Save judge results to JSON file in the conversation folder.

        Args:
            output: The JudgeOutput from evaluate()
            conversation_id: Conversation ID for folder lookup
            output_root: Root directory for conversation outputs

        Returns:
            Path to the saved results file
        """
        conversation_dir = output_root / conversation_id
        results_file = conversation_dir / "judge_evaluation.json"

        # Build results with original criteria text for clarity
        criteria_with_text = []
        for i, criterion_text in enumerate(self.criteria):
            result = next(
                (cr for cr in output.criteria_results if cr.criterion_id == i + 1),
                None,
            )
            criteria_with_text.append(
                {
                    "id": i + 1,
                    "criterion": criterion_text,
                    "passed": result.passed if result else False,
                }
            )

        results = {
            "criteria": criteria_with_text,
            "overall_pass": output.overall_pass,
            "reasoning": output.reasoning,
        }

        results_file.write_text(json.dumps(results, indent=2))
        return results_file
