"""
Preservation Property Tests — First-Time Overdue Flow, Payment Flow,
Eligibility, and Error Handling Unchanged

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

These tests parse the "Bill overdue flow" and "MAKE A PAYMENT FLOW" sections
from Backend/instructions.py UNIFIED_INSTRUCTION and assert that existing
behavior is preserved after the promise-to-pay date extension fix.

Observation-first methodology: these tests were written by observing the
UNFIXED code and capturing the baseline elements that must remain unchanged.

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
# Helpers: extract sections from UNIFIED_INSTRUCTION
# ---------------------------------------------------------------------------
def extract_bill_overdue_flow(instruction_text: str) -> str:
    """Extract the Bill overdue flow section from UNIFIED_INSTRUCTION.

    The section starts at "Bill overdue flow" and ends at the next major
    section header. We look for "MAKE A PAYMENT FLOW" at the start of a
    line (the section header), not inline references like "follow the
    MAKE A PAYMENT FLOW below".
    """
    start = instruction_text.find("Bill overdue flow")
    if start == -1:
        return ""
    rest = instruction_text[start:]
    # Find "MAKE A PAYMENT FLOW" as a section header (at start of line)
    import re as _re
    match = _re.search(r"\n(?=MAKE A PAYMENT FLOW\n)", rest)
    if match:
        return rest[: match.start()]
    # Fallback: look for RULES section
    for boundary in ["RULES"]:
        end = rest.find(boundary)
        if end != -1:
            return rest[:end]
    return rest


def extract_payment_flow(instruction_text: str) -> str:
    """Extract the MAKE A PAYMENT FLOW section from UNIFIED_INSTRUCTION."""
    start = instruction_text.find("MAKE A PAYMENT FLOW")
    if start == -1:
        return ""
    rest = instruction_text[start:]
    for boundary in ["RULES"]:
        end = rest.find(boundary)
        if end != -1:
            return rest[:end]
    return rest


# ---------------------------------------------------------------------------
# Strategies: generate non-extension overdue messages (first-time interactions)
# ---------------------------------------------------------------------------
FIRST_TIME_OVERDUE_MESSAGES = [
    "my bill is overdue",
    "I have an unpaid bill",
    "I got a notice that my bill is past due",
    "when is my bill due?",
    "I can't pay my bill",
    "my account says overdue",
    "I need help with an overdue invoice",
]

PAYMENT_MESSAGES = [
    "I want to pay now",
    "let me pay my bill",
    "I'd like to make a payment",
    "go ahead and charge my card",
    "yes, I want to pay",
]

first_time_overdue_strategy = st.sampled_from(FIRST_TIME_OVERDUE_MESSAGES)
payment_message_strategy = st.sampled_from(PAYMENT_MESSAGES)


# ---------------------------------------------------------------------------
# Property 2a: Three consequences preserved for first-time overdue
# ---------------------------------------------------------------------------
class TestPreservationThreeConsequences:
    """
    **Validates: Requirements 3.1**

    The "Bill overdue flow" must contain all three consequences of not paying
    for first-time overdue interactions:
      a) Late fees will be added
      b) Service will be disconnected after the 7-day grace period
      c) It could negatively affect their account standing
    """

    def setup_method(self):
        self.flow_text = extract_bill_overdue_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_late_fees_consequence_present(self, msg: str):
        """
        **Validates: Requirements 3.1**

        The Bill overdue flow must mention late fees as a consequence.
        """
        assert "late fees" in self.flow_lower, (
            f"Bill overdue flow no longer mentions 'late fees' as a consequence. "
            f"First-time overdue message '{msg}' should trigger the full consequences "
            f"flow including late fees."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_service_disconnection_consequence_present(self, msg: str):
        """
        **Validates: Requirements 3.1**

        The Bill overdue flow must mention service disconnection as a consequence.
        """
        has_disconnection = (
            "service will be disconnected" in self.flow_lower
            or "service disconnection" in self.flow_lower
            or "disconnected" in self.flow_lower
        )
        assert has_disconnection, (
            f"Bill overdue flow no longer mentions service disconnection as a "
            f"consequence. First-time overdue message '{msg}' should trigger the "
            f"full consequences flow including service disconnection."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_account_standing_consequence_present(self, msg: str):
        """
        **Validates: Requirements 3.1**

        The Bill overdue flow must mention account standing as a consequence.
        """
        assert "account standing" in self.flow_lower, (
            f"Bill overdue flow no longer mentions 'account standing' as a "
            f"consequence. First-time overdue message '{msg}' should trigger the "
            f"full consequences flow including account standing impact."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_three_consequences_required(self, msg: str):
        """
        **Validates: Requirements 3.1**

        The Bill overdue flow must explicitly state that all three consequences
        are mandatory — "you MUST mention every one".
        """
        has_must_mention = (
            "must mention every one" in self.flow_lower
            or "must include the 3 consequences" in self.flow_lower
        )
        assert has_must_mention, (
            f"Bill overdue flow no longer contains the mandatory instruction to "
            f"include all three consequences. First-time overdue message '{msg}' "
            f"should trigger all three consequences without exception."
        )


# ---------------------------------------------------------------------------
# Property 2b: Eligibility check and denial path preserved
# ---------------------------------------------------------------------------
class TestPreservationEligibilityCheck:
    """
    **Validates: Requirements 3.4**

    The "Bill overdue flow" must contain the is_eligible_promise_to_pay
    eligibility check with a denial path for ineligible users.
    """

    def setup_method(self):
        self.flow_text = extract_bill_overdue_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_eligibility_check_present(self, msg: str):
        """
        **Validates: Requirements 3.4**

        The Bill overdue flow must reference is_eligible_promise_to_pay to
        check user eligibility before offering Promise to Pay.
        """
        assert "is_eligible_promise_to_pay" in self.flow_text, (
            f"Bill overdue flow no longer references 'is_eligible_promise_to_pay'. "
            f"The eligibility check for Promise to Pay is missing. "
            f"Message '{msg}' could lead to offering Promise to Pay to ineligible users."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_denial_path_for_ineligible_users(self, msg: str):
        """
        **Validates: Requirements 3.4**

        The Bill overdue flow must contain a denial path when
        is_eligible_promise_to_pay is false — telling the user they are
        not eligible.
        """
        has_false_check = (
            "is_eligible_promise_to_pay` is false" in self.flow_text
            or "is_eligible_promise_to_pay` is false or missing" in self.flow_text
        )
        has_not_eligible = (
            "not currently eligible" in self.flow_lower
            or "not eligible" in self.flow_lower
        )
        assert has_false_check and has_not_eligible, (
            f"Bill overdue flow no longer contains the denial path for ineligible "
            f"users. When is_eligible_promise_to_pay is false, the agent must tell "
            f"the user they are not eligible. Message '{msg}' could bypass this check."
        )


# ---------------------------------------------------------------------------
# Property 2c: set_promise_date error handling preserved
# ---------------------------------------------------------------------------
class TestPreservationErrorHandling:
    """
    **Validates: Requirements 3.2**

    The "Bill overdue flow" must contain set_promise_date error handling
    that relays the max allowed date from the tool error to the user.
    """

    def setup_method(self):
        self.flow_text = extract_bill_overdue_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_set_promise_date_error_relays_max_date(self, msg: str):
        """
        **Validates: Requirements 3.2**

        The Bill overdue flow must instruct the agent to relay the max date
        from a set_promise_date error to the user.
        """
        has_error_handling = (
            "if the tool returns an error" in self.flow_lower
            or "maximum allowed date" in self.flow_lower
            or "max date from error" in self.flow_lower
        )
        assert has_error_handling, (
            f"Bill overdue flow no longer contains set_promise_date error handling. "
            f"When the tool returns an error with a max date, the agent must relay "
            f"that to the user. Message '{msg}' could lead to unhandled errors."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_set_promise_date_error_asks_for_new_date(self, msg: str):
        """
        **Validates: Requirements 3.2**

        When set_promise_date returns an error, the agent must ask the user
        to pick a new date within range rather than retrying the same date.
        """
        has_ask_new_date = (
            "would you like me to use that date" in self.flow_lower
            or "prefer a different date" in self.flow_lower
            or "do not retry with the same date" in self.flow_lower
        )
        assert has_ask_new_date, (
            f"Bill overdue flow no longer asks the user to pick a new date when "
            f"set_promise_date returns an error. The agent must not retry with the "
            f"same date. Message '{msg}' could lead to infinite retry loops."
        )


# ---------------------------------------------------------------------------
# Property 2d: MAKE A PAYMENT FLOW preserved
# ---------------------------------------------------------------------------
class TestPreservationPaymentFlow:
    """
    **Validates: Requirements 3.3**

    The "MAKE A PAYMENT FLOW" section must still exist with its key elements:
    make_payment tool and "Credit Card ending in 5566".
    """

    def setup_method(self):
        self.full_text = UNIFIED_INSTRUCTION
        self.payment_flow = extract_payment_flow(UNIFIED_INSTRUCTION)
        self.payment_lower = self.payment_flow.lower()

    @given(msg=payment_message_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_payment_flow_section_exists(self, msg: str):
        """
        **Validates: Requirements 3.3**

        The MAKE A PAYMENT FLOW section must exist in UNIFIED_INSTRUCTION.
        """
        assert "MAKE A PAYMENT FLOW" in self.full_text, (
            f"UNIFIED_INSTRUCTION no longer contains 'MAKE A PAYMENT FLOW' section. "
            f"Payment message '{msg}' would have no flow to follow."
        )

    @given(msg=payment_message_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_make_payment_tool_referenced(self, msg: str):
        """
        **Validates: Requirements 3.3**

        The MAKE A PAYMENT FLOW must reference the make_payment tool.
        """
        assert "make_payment" in self.payment_flow, (
            f"MAKE A PAYMENT FLOW no longer references 'make_payment' tool. "
            f"Payment message '{msg}' would not trigger the payment tool."
        )

    @given(msg=payment_message_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_credit_card_payment_method_present(self, msg: str):
        """
        **Validates: Requirements 3.3**

        The MAKE A PAYMENT FLOW must reference the saved payment method
        "Credit Card ending in 5566".
        """
        assert "Credit Card ending in 5566" in self.payment_flow, (
            f"MAKE A PAYMENT FLOW no longer references 'Credit Card ending in 5566'. "
            f"Payment message '{msg}' would not use the correct payment method."
        )


# ---------------------------------------------------------------------------
# Property 2e: Naming instructions preserved ("Do NOT mention extension",
#              "Promise to Pay")
# ---------------------------------------------------------------------------
class TestPreservationNamingInstructions:
    """
    **Validates: Requirements 3.1**

    The "Bill overdue flow" must contain the naming instructions:
    - "Do NOT mention extension" (or similar anti-extension language)
    - Always call it "Promise to Pay" by name
    """

    def setup_method(self):
        self.flow_text = extract_bill_overdue_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_do_not_mention_extension_instruction(self, msg: str):
        """
        **Validates: Requirements 3.1**

        The Bill overdue flow must contain the instruction to NOT mention
        "extension" in the first response about an overdue bill.
        """
        has_no_extension = (
            "do not mention" in self.flow_lower
            and "extension" in self.flow_lower
        )
        assert has_no_extension, (
            f"Bill overdue flow no longer contains the 'Do NOT mention extension' "
            f"instruction. First-time overdue message '{msg}' could lead the agent "
            f"to mention extensions prematurely."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_promise_to_pay_naming(self, msg: str):
        """
        **Validates: Requirements 3.1**

        The Bill overdue flow must instruct the agent to always call the
        program "Promise to Pay" by name.
        """
        has_promise_to_pay_name = (
            "promise to pay" in self.flow_lower
            and "by name" in self.flow_lower
        )
        assert has_promise_to_pay_name, (
            f"Bill overdue flow no longer instructs the agent to call the program "
            f"'Promise to Pay' by name. Message '{msg}' could lead to inconsistent "
            f"naming of the program."
        )


# ---------------------------------------------------------------------------
# Property 2f: Step sequence preserved (step 1 → 2 → 3 → 4)
# ---------------------------------------------------------------------------
class TestPreservationStepSequence:
    """
    **Validates: Requirements 3.1, 3.3**

    The "Bill overdue flow" must preserve the existing step sequence for
    non-extension cases:
      Step 1: Call get_user_invoices
      Step 2: Show overdue consequences
      Step 3: If user wants to pay → MAKE A PAYMENT FLOW
      Step 4: If user can't pay → offer Promise to Pay (if eligible)
    """

    def setup_method(self):
        self.flow_text = extract_bill_overdue_flow(UNIFIED_INSTRUCTION)
        self.flow_lower = self.flow_text.lower()

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_step_1_get_user_invoices(self, msg: str):
        """
        **Validates: Requirements 3.1**

        Step 1 must call get_user_invoices to find the relevant invoice.
        """
        assert "get_user_invoices" in self.flow_text, (
            f"Bill overdue flow step 1 no longer references 'get_user_invoices'. "
            f"Message '{msg}' would not trigger invoice lookup."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_step_2_show_consequences(self, msg: str):
        """
        **Validates: Requirements 3.1**

        Step 2 must show the overdue consequences (invoice details + three
        consequences + ask to pay now).
        """
        # Step 2 must contain the "ask to pay now" prompt
        has_ask_to_pay = (
            "would you like to pay now" in self.flow_lower
        )
        assert has_ask_to_pay, (
            f"Bill overdue flow step 2 no longer asks 'Would you like to pay now?'. "
            f"Message '{msg}' would not prompt the user to pay."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_step_3_payment_flow_reference(self, msg: str):
        """
        **Validates: Requirements 3.3**

        Step 3 must reference the MAKE A PAYMENT FLOW for users who want
        to pay now.
        """
        has_payment_ref = (
            "make a payment flow" in self.flow_lower
            or "wants to pay now" in self.flow_lower
            or "want to pay now" in self.flow_lower
        )
        assert has_payment_ref, (
            f"Bill overdue flow step 3 no longer references the MAKE A PAYMENT FLOW. "
            f"Message '{msg}' would not route paying users to the payment flow."
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_step_4_promise_to_pay_offer(self, msg: str):
        """
        **Validates: Requirements 3.1**

        Step 4 must offer Promise to Pay only after the user explicitly says
        they cannot pay right now.
        """
        has_cant_pay_gate = (
            "cannot pay right now" in self.flow_lower
            or "can't pay today" in self.flow_lower
            or "explicitly says they cannot pay" in self.flow_lower
        )
        has_promise_offer = "set_promise_date" in self.flow_text

        assert has_cant_pay_gate and has_promise_offer, (
            f"Bill overdue flow step 4 no longer gates Promise to Pay behind "
            f"the user explicitly saying they can't pay. Message '{msg}' could "
            f"lead to premature Promise to Pay offers. "
            f"cant_pay_gate={has_cant_pay_gate}, promise_offer={has_promise_offer}"
        )

    @given(msg=first_time_overdue_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_step_sequence_order(self, msg: str):
        """
        **Validates: Requirements 3.1, 3.3**

        The steps must appear in order: get_user_invoices (step 1) before
        consequences (step 2) before payment flow reference (step 3) before
        promise to pay (step 4).
        """
        # Find positions of key markers in the flow
        pos_invoices = self.flow_text.find("get_user_invoices")
        pos_consequences = self.flow_text.find("consequences")
        pos_pay_now = self.flow_lower.find("wants to pay now")
        if pos_pay_now == -1:
            pos_pay_now = self.flow_lower.find("want to pay now")
        pos_promise = self.flow_lower.find("set_promise_date")

        # All must be present
        assert pos_invoices != -1, (
            f"get_user_invoices not found in Bill overdue flow."
        )
        assert pos_consequences != -1, (
            f"'consequences' not found in Bill overdue flow."
        )
        assert pos_promise != -1, (
            f"set_promise_date not found in Bill overdue flow."
        )

        # Order: invoices < consequences < promise
        assert pos_invoices < pos_consequences < pos_promise, (
            f"Bill overdue flow step sequence is out of order. "
            f"Expected: get_user_invoices ({pos_invoices}) < consequences "
            f"({pos_consequences}) < set_promise_date ({pos_promise}). "
            f"Message '{msg}' could trigger steps in wrong order."
        )
