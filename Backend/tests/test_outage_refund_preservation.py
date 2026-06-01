"""
Preservation Property Tests — Existing Explicit Confirmation/Decline and Flow Behavior

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests parse the OUTAGE REFUND FLOW section (and full UNIFIED_INSTRUCTION)
from Backend/instructions.py and assert that existing behavior is preserved:
  - Explicit YES words trigger refund processing
  - Explicit NO words halt refund processing
  - Refund calculation formula is present and unchanged
  - Automatic outage lookup flow is present and unchanged
  - "Do NOT ask the user for outage dates or area" instruction is present
  - Conversational tone instructions are present
  - Other flows (MAKE A PAYMENT FLOW, Bill overdue flow) are unaffected

These tests MUST PASS on unfixed code — they capture the baseline to preserve.
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
# Helper: extract the OUTAGE REFUND FLOW section (including trailing IMPORTANT lines)
# ---------------------------------------------------------------------------
def extract_outage_refund_flow(instruction_text: str) -> str:
    """Extract the OUTAGE REFUND FLOW section from UNIFIED_INSTRUCTION."""
    start = instruction_text.find("OUTAGE REFUND FLOW")
    if start == -1:
        return ""
    rest = instruction_text[start:]
    # Find the next major section boundary
    for boundary in ["Bill overdue flow", "MAKE A PAYMENT FLOW"]:
        end = rest.find(boundary)
        if end != -1:
            return rest[:end]
    return rest


# ---------------------------------------------------------------------------
# Strategies: generate explicit YES and NO words
# ---------------------------------------------------------------------------
YES_WORDS = ["yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"]
NO_WORDS = ["no", "no thanks", "never mind", "cancel", "don't", "skip"]

yes_word_strategy = st.sampled_from(YES_WORDS)
no_word_strategy = st.sampled_from(NO_WORDS)


# ---------------------------------------------------------------------------
# Property 2: Preservation — Existing behavior must be preserved
# ---------------------------------------------------------------------------
class TestPreservationExplicitConfirmationDecline:
    """
    Verify that the OUTAGE REFUND FLOW contains logic to process refunds
    on explicit confirmation and halt on explicit decline.
    """

    def setup_method(self):
        self.flow_text = extract_outage_refund_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()
        self.full_lower = UNIFIED_INSTRUCTION.lower()

    # -- Property 2a: Explicit YES words trigger refund processing ----------
    @given(yes_word=yes_word_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explicit_yes_triggers_refund_processing(self, yes_word: str):
        """
        **Validates: Requirements 3.1**

        The OUTAGE REFUND FLOW must contain logic that processes refunds when
        the user explicitly confirms. The flow says "Only if the user confirms
        they want a refund" — this must remain present.
        """
        # The flow must contain the confirmation gate instruction
        has_confirmation_gate = (
            "only if the user confirms" in self.flow_lower
            or "if the user confirms" in self.flow_lower
            or "user confirms they want a refund" in self.flow_lower
        )
        assert has_confirmation_gate, (
            f"OUTAGE REFUND FLOW no longer contains the confirmation gate instruction. "
            f"Explicit YES word '{yes_word}' should trigger refund processing, but the "
            f"instruction 'Only if the user confirms they want a refund' is missing."
        )

        # The flow must reference wallet tools for processing the refund
        has_wallet_processing = (
            "create_wallet_entry" in self.flow_text
            or "update_wallet_amount" in self.flow_text
        )
        assert has_wallet_processing, (
            f"OUTAGE REFUND FLOW no longer references wallet tools for refund processing. "
            f"Explicit YES word '{yes_word}' should trigger create_wallet_entry or "
            f"update_wallet_amount, but neither is mentioned in the flow."
        )

    # -- Property 2b: Explicit NO words halt refund processing --------------
    @given(no_word=no_word_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explicit_no_halts_refund_processing(self, no_word: str):
        """
        **Validates: Requirements 3.2**

        The OUTAGE REFUND FLOW must contain logic that halts refund processing
        when the user declines. The flow asks "Would you like me to process a
        refund for this?" — the conversational structure implies the agent
        respects a NO answer. The instruction "Do NOT process the refund
        without asking the user first" must remain present.
        """
        # The flow must contain the "ask before processing" guard
        has_ask_before_processing = (
            "do not process the refund without asking" in self.flow_lower
            or "do not process the refund without asking the user first" in self.flow_lower
        )
        assert has_ask_before_processing, (
            f"OUTAGE REFUND FLOW no longer contains the 'Do NOT process the refund "
            f"without asking the user first' instruction. Explicit NO word '{no_word}' "
            f"should halt refund processing, but the guard is missing."
        )

        # The flow must ask the user before processing
        has_ask_prompt = (
            "would you like me to process a refund" in self.flow_lower
            or "ask" in self.flow_lower
        )
        assert has_ask_prompt, (
            f"OUTAGE REFUND FLOW no longer asks the user before processing a refund. "
            f"Explicit NO word '{no_word}' should halt processing, but the prompt is missing."
        )


class TestPreservationRefundCalculation:
    """
    Verify that the refund calculation formula and outage lookup flow
    are present and unchanged.
    """

    def setup_method(self):
        self.flow_text = extract_outage_refund_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()
        self.full_text = UNIFIED_INSTRUCTION
        self.full_lower = UNIFIED_INSTRUCTION.lower()

    # -- Property 2c: Refund calculation formula is present -----------------
    @given(yes_word=yes_word_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_refund_calculation_formula_present(self, yes_word: str):
        """
        **Validates: Requirements 3.3**

        The OUTAGE REFUND FLOW must contain the refund calculation formula:
        (outage_days / days_in_month) × invoice_amount
        """
        has_formula = (
            "(outage_days / days_in_month)" in self.flow_lower
            and "invoice_amount" in self.flow_lower
        )
        assert has_formula, (
            f"OUTAGE REFUND FLOW no longer contains the refund calculation formula "
            f"'(outage_days / days_in_month) × invoice_amount'. "
            f"When user confirms with '{yes_word}', the refund must be calculated "
            f"using this formula."
        )

        # The formula must include showing the calculation to the user
        has_show_calculation = (
            "show the calculation" in self.flow_lower
            or "always show" in self.flow_lower
        )
        assert has_show_calculation, (
            f"OUTAGE REFUND FLOW no longer instructs the agent to show the calculation "
            f"to the user. The instruction 'Always show the calculation to the user' "
            f"is missing."
        )

    # -- Property 2d: Automatic outage lookup flow is present ---------------
    @given(yes_word=yes_word_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_automatic_outage_lookup_flow_present(self, yes_word: str):
        """
        **Validates: Requirements 3.4**

        The OUTAGE REFUND FLOW must contain the automatic outage lookup:
        get area from invoices → call check_outage. The agent must NOT ask
        the user for outage dates or area.
        """
        # Step 1: get_user_invoices to find area
        has_get_invoices = "get_user_invoices" in self.flow_text
        assert has_get_invoices, (
            f"OUTAGE REFUND FLOW no longer references get_user_invoices to find "
            f"the user's area. The automatic lookup flow is broken."
        )

        # Step 2: check_outage with that area
        has_check_outage = "check_outage" in self.flow_text
        assert has_check_outage, (
            f"OUTAGE REFUND FLOW no longer references check_outage. "
            f"The automatic outage lookup flow is broken."
        )

        # Must NOT ask user for area
        has_no_ask_area = (
            "do not ask the user for outage dates or area" in self.flow_lower
        )
        assert has_no_ask_area, (
            f"OUTAGE REFUND FLOW no longer contains the instruction "
            f"'Do NOT ask the user for outage dates or area'. "
            f"The agent might start asking users for area information."
        )


class TestPreservationConversationalTone:
    """
    Verify that conversational tone instructions and other flows are unaffected.
    """

    def setup_method(self):
        self.flow_text = extract_outage_refund_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()
        self.full_text = UNIFIED_INSTRUCTION
        self.full_lower = UNIFIED_INSTRUCTION.lower()

    # -- Property 2e: Conversational tone instructions present --------------
    @given(yes_word=yes_word_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_conversational_tone_instructions_present(self, yes_word: str):
        """
        **Validates: Requirements 3.1, 3.2**

        The instructions must contain "Be conversational" and
        "ask before taking action" directives.
        """
        has_be_conversational = "be conversational" in self.full_lower
        assert has_be_conversational, (
            f"UNIFIED_INSTRUCTION no longer contains 'Be conversational' directive. "
            f"The agent's conversational tone may be lost."
        )

        has_ask_before_action = (
            "ask before taking action" in self.full_lower
            or "confirm with the user before" in self.full_lower
        )
        assert has_ask_before_action, (
            f"UNIFIED_INSTRUCTION no longer contains 'ask before taking action' or "
            f"'confirm with the user before' directive. The agent may skip confirmations."
        )

    # -- Property 2f: Other flows are unaffected ----------------------------
    @given(yes_word=yes_word_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_other_flows_unaffected(self, yes_word: str):
        """
        **Validates: Requirements 3.1, 3.2**

        The MAKE A PAYMENT FLOW and Bill overdue flow must still be present
        and unaffected by any changes to the OUTAGE REFUND FLOW.
        """
        has_payment_flow = "MAKE A PAYMENT FLOW" in self.full_text
        assert has_payment_flow, (
            f"UNIFIED_INSTRUCTION no longer contains 'MAKE A PAYMENT FLOW'. "
            f"The payment flow may have been accidentally removed or modified."
        )

        has_overdue_flow = "Bill overdue flow" in self.full_text
        assert has_overdue_flow, (
            f"UNIFIED_INSTRUCTION no longer contains 'Bill overdue flow'. "
            f"The overdue flow may have been accidentally removed or modified."
        )

        # Verify payment flow still has its key elements
        payment_start = self.full_text.find("MAKE A PAYMENT FLOW")
        if payment_start != -1:
            payment_section = self.full_text[payment_start:]
            assert "make_payment" in payment_section, (
                f"MAKE A PAYMENT FLOW no longer references make_payment tool."
            )
            assert "Credit Card ending in 5566" in payment_section, (
                f"MAKE A PAYMENT FLOW no longer references the saved payment method."
            )

        # Verify overdue flow still has its key elements
        overdue_start = self.full_text.find("Bill overdue flow")
        if overdue_start != -1:
            overdue_section = self.full_text[overdue_start:]
            # Find end of overdue section
            overdue_end = overdue_section.find("MAKE A PAYMENT FLOW")
            if overdue_end != -1:
                overdue_section = overdue_section[:overdue_end]
            assert "promise" in overdue_section.lower(), (
                f"Bill overdue flow no longer references promise to pay."
            )
