"""
Bug Condition Exploration Test — Promise-to-Pay Extension Requests Bypass Overdue Flow

**Validates: Requirements 1.1, 1.2, 1.3**

This test parses the "Bill overdue flow" section from UNIFIED_INSTRUCTION and
asserts that the instruction text contains the conditional branches and sub-flow
needed to handle promise-to-pay date extension requests without restarting the
full overdue-consequences flow.

EXPECTED TO FAIL on unfixed code — failure confirms the bug exists:
- No conditional branch for existing promise_date
- No PROMISE DATE EXTENSION sub-flow
- No extension-detection phrases
- No guard against re-showing consequences for extension requests
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
# Helper: extract the "Bill overdue flow" section
# ---------------------------------------------------------------------------
def extract_bill_overdue_flow(instruction_text: str) -> str:
    """Extract the Bill overdue flow section from UNIFIED_INSTRUCTION."""
    start = instruction_text.find("Bill overdue flow")
    if start == -1:
        return ""
    rest = instruction_text[start:]
    # Find the next major section boundary
    for boundary in ["MAKE A PAYMENT FLOW", "RULES"]:
        end = rest.find(boundary)
        if end != -1:
            return rest[:end]
    return rest


# ---------------------------------------------------------------------------
# Strategies: generate extension request phrases
# ---------------------------------------------------------------------------
ABSOLUTE_DATE_REQUESTS = [
    "can you move my promise date to March 8?",
    "move my promise date to March 10",
    "change my promise date to the 9th",
    "I'd like to set my promise date to March 8th",
    "can you update my promise date to March 9?",
    "switch my promise date to March 8",
    "set my promise date to March 10th please",
]

RELATIVE_DATE_REQUESTS = [
    "can I get one more day?",
    "push it back a day",
    "I need one more day",
    "can I extend by 2 days?",
    "push it back 2 days",
    "give me a couple more days",
    "I need to push my promise date back a couple days",
    "can I get an extension?",
    "extend my promise date please",
]

extension_request_phrases = st.one_of(
    st.sampled_from(ABSOLUTE_DATE_REQUESTS),
    st.sampled_from(RELATIVE_DATE_REQUESTS),
)

# Phrases the instructions should recognize as extension requests
EXPECTED_DETECTION_PHRASES = [
    "extend",
    "move my date",
    "push it back",
    "one more day",
]


# ---------------------------------------------------------------------------
# Property 1: Bug Condition — the Bill overdue flow must handle extensions
# ---------------------------------------------------------------------------
class TestBugConditionExploration:
    """
    These tests assert that the "Bill overdue flow" section contains the
    conditional branches and sub-flow needed to handle promise-to-pay date
    extension requests. On unfixed code, these WILL FAIL — that failure
    confirms the bug exists.
    """

    def setup_method(self):
        self.flow_text = extract_bill_overdue_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()


    # -- Property 1a: Conditional check for existing promise_date -----------
    @given(request=extension_request_phrases)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_conditional_check_for_existing_promise_date(self, request: str):
        """
        **Validates: Requirements 1.1**

        The Bill overdue flow must contain a conditional check for an existing
        promise_date before proceeding to step 2 (overdue-consequences). When
        a user already has a promise date and sends '{request}', the flow
        should branch to the extension sub-flow instead of showing consequences.
        """
        # The flow must check for existing promise_date as a branching condition
        has_promise_date_check = (
            "promise_date" in self.flow_lower
            and (
                "already has" in self.flow_lower
                or "existing" in self.flow_lower
                or "already set" in self.flow_lower
                or "has a promise" in self.flow_lower
            )
            and (
                "extension" in self.flow_lower
                or "sub-flow" in self.flow_lower
                or "do not proceed to step 2" in self.flow_lower
                or "skip" in self.flow_lower
            )
        )
        assert has_promise_date_check, (
            f"Bill overdue flow lacks a conditional check for existing promise_date. "
            f"Extension request '{request}' would trigger the full overdue-consequences "
            f"flow instead of branching to an extension path. "
            f"Expected: check for existing promise_date before step 2."
        )

    # -- Property 1b: PROMISE DATE EXTENSION sub-flow exists ----------------
    @given(request=extension_request_phrases)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_extension_sub_flow_exists(self, request: str):
        """
        **Validates: Requirements 1.2, 1.3**

        The Bill overdue flow must contain a PROMISE DATE EXTENSION sub-flow
        with steps for get_promise_date, date calculation (absolute and
        relative), user confirmation, and set_promise_date.
        """
        # Must have a labeled extension sub-flow
        has_extension_label = (
            "promise date extension" in self.flow_lower
            or "extension sub-flow" in self.flow_lower
            or "extension flow" in self.flow_lower
        )

        # Must call get_promise_date to retrieve current date
        has_get_promise_date = "get_promise_date" in self.flow_lower

        # Must handle both absolute and relative date requests
        has_date_calculation = (
            ("absolute" in self.flow_lower or "specific date" in self.flow_lower)
            and ("relative" in self.flow_lower or "add" in self.flow_lower)
        )

        # Must confirm with user before calling set_promise_date
        has_confirmation_step = (
            "confirm" in self.flow_lower
            and "set_promise_date" in self.flow_lower
        )

        has_full_sub_flow = (
            has_extension_label
            and has_get_promise_date
            and has_date_calculation
            and has_confirmation_step
        )

        assert has_full_sub_flow, (
            f"Bill overdue flow lacks a PROMISE DATE EXTENSION sub-flow. "
            f"Extension request '{request}' cannot be handled because: "
            f"extension label={has_extension_label}, "
            f"get_promise_date call={has_get_promise_date}, "
            f"date calculation (abs+rel)={has_date_calculation}, "
            f"confirmation step={has_confirmation_step}. "
            f"Expected: a complete sub-flow with retrieval, calculation, "
            f"confirmation, and update steps."
        )

    # -- Property 1c: Extension-detection phrases present -------------------
    @given(request=extension_request_phrases)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_extension_detection_phrases_present(self, request: str):
        """
        **Validates: Requirements 1.1, 1.2**

        The Bill overdue flow must contain extension-detection phrases so the
        agent can recognize when a user is asking to modify an existing promise
        date rather than setting one up for the first time.
        """
        # At least some of the expected detection phrases must be present
        found_phrases = [
            phrase for phrase in EXPECTED_DETECTION_PHRASES
            if phrase in self.flow_lower
        ]

        assert len(found_phrases) >= 2, (
            f"Bill overdue flow lacks extension-detection phrases. "
            f"Found only {found_phrases} out of {EXPECTED_DETECTION_PHRASES}. "
            f"Without these phrases, the agent cannot recognize '{request}' "
            f"as an extension request and will restart the overdue flow."
        )

    # -- Property 1d: Guard against re-showing consequences -----------------
    @given(request=extension_request_phrases)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_guard_against_reshowing_consequences(self, request: str):
        """
        **Validates: Requirements 1.1**

        The Bill overdue flow must contain an explicit guard that prevents
        re-showing the overdue-consequences summary when an existing promise
        date is detected and the user is requesting an extension. This guard
        must specifically mention extension requests — general "do not repeat"
        instructions for follow-up turns are not sufficient.
        """
        import re as _re

        # We need a SPECIFIC guard that connects extension requests to
        # skipping the consequences flow. The existing instructions have
        # "Do NOT mention extension" (about naming) and "Do NOT repeat
        # this summary on follow-up turns" (about general follow-ups),
        # but neither is a guard for extension requests.
        #
        # Look for patterns that explicitly link:
        #   - existing promise date / extension request context
        #   - with skipping consequences / not proceeding to step 2

        guard_patterns = [
            r"existing\s+promise.*do\s+not\s+proceed\s+to\s+step\s+2",
            r"extension\s+request.*(?:do\s+not|must\s+not|shall\s+not).*consequence",
            r"(?:do\s+not|must\s+not).*repeat.*consequence.*extension",
            r"(?:do\s+not|must\s+not).*re-show.*consequence",
            r"without\s+repeating\s+the\s+overdue",
            r"skip\s+step\s+2.*extension",
            r"extension.*skip.*consequence",
            r"promise\s+date\s+extension.*(?:do\s+not|must\s+not|shall\s+not)",
            r"existing\s+promise\s+date.*(?:do\s+not|must\s+not)\s+(?:show|repeat|re-show)",
        ]

        has_extension_specific_guard = any(
            _re.search(pattern, self.flow_lower)
            for pattern in guard_patterns
        )
        assert has_extension_specific_guard, (
            f"Bill overdue flow lacks an extension-specific guard against "
            f"re-showing consequences. When a user with an existing promise date "
            f"sends '{request}', the agent would repeat the full overdue-consequences "
            f"summary instead of going directly to the extension flow. "
            f"Expected: explicit instruction that extension requests should NOT "
            f"trigger the consequences flow (step 2)."
        )
