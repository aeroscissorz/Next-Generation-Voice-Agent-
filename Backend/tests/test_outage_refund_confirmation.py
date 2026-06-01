"""
Bug Condition Exploration Test — Non-Confirmation Responses Trigger Refund

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

This test parses the OUTAGE REFUND FLOW section from UNIFIED_INSTRUCTION and
asserts that the instruction text contains the guardrails needed to prevent
the agent from processing refunds without explicit confirmation.

EXPECTED TO FAIL on unfixed code — failure confirms the bug exists.
"""

import re
import sys
import os

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# Ensure Backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from instructions import UNIFIED_INSTRUCTION


# ---------------------------------------------------------------------------
# Helper: extract the OUTAGE REFUND FLOW section
# ---------------------------------------------------------------------------
def extract_outage_refund_flow(instruction_text: str) -> str:
    """Extract the OUTAGE REFUND FLOW section from UNIFIED_INSTRUCTION."""
    pattern = r"OUTAGE REFUND FLOW\s*\n(.*?)(?=\n[A-Z][A-Z ]+FLOW|\n[A-Z][A-Z ]+\n|IMPORTANT:.*Do NOT ask the user for outage)"
    match = re.search(pattern, instruction_text, re.DOTALL)
    if match:
        return match.group(0)
    # Fallback: grab everything from "OUTAGE REFUND FLOW" to the next major section
    start = instruction_text.find("OUTAGE REFUND FLOW")
    if start == -1:
        return ""
    # Find the next major section header (all-caps line followed by newline)
    rest = instruction_text[start:]
    # Look for "Bill overdue flow" or "MAKE A PAYMENT FLOW" as section boundary
    for boundary in ["Bill overdue flow", "MAKE A PAYMENT FLOW"]:
        end = rest.find(boundary)
        if end != -1:
            return rest[:end]
    return rest


# ---------------------------------------------------------------------------
# Strategies: generate non-confirmation user responses
# ---------------------------------------------------------------------------
COMPLAINT_TEMPLATES = [
    "This is too low",
    "That's not enough",
    "I expected more",
    "This is too low for me",
    "Not enough compensation",
    "I deserve more than that",
    "That amount is ridiculous",
]

QUESTION_TEMPLATES = [
    "How much?",
    "How much will you refund me?",
    "What's the amount?",
    "What is the refund amount?",
    "Can you tell me the exact amount?",
    "How did you calculate that?",
]

AMBIGUOUS_TEMPLATES = [
    "I guess",
    "maybe",
    "hmm",
    "let me think",
    "I'm not sure",
    "possibly",
    "I suppose",
    "well...",
    "uh okay I think",
]

non_confirmation_responses = st.one_of(
    st.sampled_from(COMPLAINT_TEMPLATES),
    st.sampled_from(QUESTION_TEMPLATES),
    st.sampled_from(AMBIGUOUS_TEMPLATES),
)

# The YES words that should be defined as an explicit gate
EXPECTED_YES_WORDS = ["yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"]


# ---------------------------------------------------------------------------
# Property 1: Bug Condition — the OUTAGE REFUND FLOW must contain guardrails
# ---------------------------------------------------------------------------
class TestBugConditionExploration:
    """
    These tests assert that the OUTAGE REFUND FLOW section contains the
    guardrails needed to prevent the agent from processing refunds without
    explicit confirmation. On unfixed code, these WILL FAIL — that failure
    confirms the bug exists.
    """

    def setup_method(self):
        self.flow_text = extract_outage_refund_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()

    # -- Property 1a: Explicit confirmation word list gate ------------------
    @given(response=non_confirmation_responses)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explicit_confirmation_word_list_gate(self, response: str):
        """
        **Validates: Requirements 1.1, 1.2, 1.3**

        The OUTAGE REFUND FLOW must define an explicit list of YES confirmation
        words that gate refund processing. Without this list, the agent treats
        non-confirmation responses (like '{response}') as implicit agreement.
        """
        # The flow must contain a clearly defined YES word list as a gate
        # Check that the flow explicitly lists confirmation words together
        has_yes_word_list = all(
            f'"{word}"' in self.flow_lower or f"'{word}'" in self.flow_lower
            for word in EXPECTED_YES_WORDS
        )
        assert has_yes_word_list, (
            f"OUTAGE REFUND FLOW lacks an explicit YES confirmation word list gate. "
            f"Non-confirmation response '{response}' could be misinterpreted as confirmation. "
            f"Expected all of {EXPECTED_YES_WORDS} to be listed as explicit confirmation words."
        )

    # -- Property 1b: Ambiguous response handling branch --------------------
    @given(response=non_confirmation_responses)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_ambiguous_response_handling_branch(self, response: str):
        """
        **Validates: Requirements 1.1, 1.2, 1.3**

        The OUTAGE REFUND FLOW must contain an explicit branch for handling
        ambiguous/non-confirmation responses that re-asks for confirmation
        instead of processing the refund.
        """
        # The flow must have handling for ambiguous responses that re-asks
        has_ambiguous_handling = (
            ("ambiguous" in self.flow_lower or "neither yes nor no" in self.flow_lower)
            and ("re-ask" in self.flow_lower or "ask for explicit confirmation" in self.flow_lower
                 or "just to confirm" in self.flow_lower)
        )
        assert has_ambiguous_handling, (
            f"OUTAGE REFUND FLOW lacks an ambiguous response handling branch. "
            f"Response '{response}' is neither YES nor NO but there is no instruction "
            f"to re-ask for confirmation. The agent may process the refund anyway."
        )

    # -- Property 1c: Tool response verification gate ----------------------
    @given(response=non_confirmation_responses)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tool_response_verification_gate(self, response: str):
        """
        **Validates: Requirements 1.4, 1.5**

        The OUTAGE REFUND FLOW must contain a strict tool response verification
        gate that checks for SUCCESS vs FAILURE before confirming credit to the
        user. The gate must use explicit SUCCESS/FAILURE labels as a hard gate
        and include a STOP-and-inspect instruction after the tool call.
        """
        # Must define SUCCESS and FAILURE as labeled conditions (hard gate)
        has_success_label = (
            "success =" in self.flow_lower or "success:" in self.flow_lower
        )
        has_failure_label = (
            "failure =" in self.flow_lower or "failure:" in self.flow_lower
        )
        # Must have an explicit "only on success" gate
        has_only_on_success = "only on success" in self.flow_lower or "only if" in self.flow_lower
        # Must have an "on failure" branch with retry/escalate
        has_on_failure_branch = (
            ("on failure" in self.flow_lower or "if.*fail" in self.flow_lower)
            and ("retry" in self.flow_lower or "escalate" in self.flow_lower)
        )

        has_strict_gate = (
            has_success_label and has_failure_label
            and has_only_on_success and has_on_failure_branch
        )

        assert has_strict_gate, (
            f"OUTAGE REFUND FLOW lacks a strict tool response verification gate with "
            f"explicit SUCCESS/FAILURE label definitions as a hard gate. The agent may "
            f"claim credit was applied without verifying the tool response. "
            f"Expected 'SUCCESS = ...' and 'FAILURE = ...' labels with 'Only on SUCCESS' "
            f"and 'On FAILURE' branches."
        )

    # -- Property 1d: Anti-hallucination guard -----------------------------
    @given(response=non_confirmation_responses)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_anti_hallucination_guard(self, response: str):
        """
        **Validates: Requirements 1.4, 1.5**

        The OUTAGE REFUND FLOW must contain an anti-hallucination guard that
        explicitly prevents the agent from saying "I've applied a credit"
        without a verified successful tool response.
        """
        has_anti_hallucination = (
            ("never say" in self.flow_lower or "do not say" in self.flow_lower
             or "must not say" in self.flow_lower or "never claim" in self.flow_lower)
            and ("applied" in self.flow_lower or "credit has been" in self.flow_lower
                 or "added" in self.flow_lower)
            and ("successful tool response" in self.flow_lower
                 or "tool response" in self.flow_lower
                 or "verified" in self.flow_lower
                 or "tool returned" in self.flow_lower)
        )
        assert has_anti_hallucination, (
            f"OUTAGE REFUND FLOW lacks an anti-hallucination guard. There is no explicit "
            f"instruction preventing the agent from claiming 'I've applied a credit' without "
            f"a verified successful tool response."
        )
