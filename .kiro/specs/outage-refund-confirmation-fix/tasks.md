# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** — Non-Confirmation Responses Trigger Refund
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the agent processes refunds without explicit confirmation
  - **Scoped PBT Approach**: Scope the property to concrete failing cases — complaint, question, and ambiguous user responses to the refund confirmation prompt
  - Write a property-based test in `Backend/tests/test_outage_refund_confirmation.py` that:
    - Parses the OUTAGE REFUND FLOW section from `UNIFIED_INSTRUCTION` in `Backend/instructions.py`
    - Generates random non-confirmation user responses (complaints like "This is too low", questions like "How much?", ambiguous like "I guess", "maybe")
    - Asserts the instruction text contains an explicit confirmation word list gate (YES words: "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep")
    - Asserts the instruction text contains an ambiguous response handling branch that re-asks for confirmation
    - Asserts the instruction text contains a tool response verification gate that checks for success before confirming credit
    - Asserts the instruction text contains an anti-hallucination guard preventing "I've applied a credit" without verified tool success
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists because the current instructions lack these gates)
  - Document counterexamples found to understand root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** — Existing Explicit Confirmation/Decline and Flow Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: the OUTAGE REFUND FLOW already contains step 4 "Only if the user confirms they want a refund" and the refund calculation formula `(outage_days / days_in_month) × invoice_amount`
  - Observe on UNFIXED code: the flow already auto-retrieves area from invoices and calls check_outage without asking the user
  - Write property-based test in `Backend/tests/test_outage_refund_preservation.py` that:
    - Parses the OUTAGE REFUND FLOW section from `UNIFIED_INSTRUCTION` in `Backend/instructions.py`
    - Generates random explicit YES words from ["yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"] and asserts the instructions still contain logic to process refunds on confirmation
    - Generates random explicit NO words from ["no", "no thanks", "never mind", "cancel", "don't", "skip"] and asserts the instructions still contain logic to halt on decline
    - Asserts the refund calculation formula `(outage_days / days_in_month) × invoice_amount` is present and unchanged
    - Asserts the automatic outage lookup flow (get area from invoices → call check_outage) is present and unchanged
    - Asserts the instruction "Do NOT ask the user for outage dates or area" is present
    - Asserts the conversational tone instructions ("Be conversational", "ask before taking action") are present
    - Asserts other flows (MAKE A PAYMENT FLOW, Bill overdue flow) are unaffected
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for outage refund confirmation — tighten OUTAGE REFUND FLOW in `Backend/instructions.py`

  - [x] 3.1 Add explicit confirmation word lists and ambiguous response handling
    - In the OUTAGE REFUND FLOW section of `UNIFIED_INSTRUCTION` in `Backend/instructions.py`, between step 3 (respond to user) and step 4 (process refund):
    - Add a YES confirmation word list: "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"
    - Add a NO decline word list: "no", "no thanks", "never mind", "cancel", "don't", "skip"
    - Add an AMBIGUOUS response handling branch for responses matching neither YES nor NO:
      - Complaint (e.g., "too low", "not enough", "expected more"): acknowledge frustration, explain calculation and policy cap, re-ask for confirmation
      - Question (e.g., "how much?", "what's the amount?"): answer with calculated amount and formula, re-ask for confirmation
      - Ambiguous (e.g., "I guess", "maybe", "hmm", "let me think"): ask explicitly "Just to confirm — would you like me to go ahead and apply the ₹[amount] credit to your account?"
    - CRITICAL: Do NOT process the refund on any ambiguous/complaint/question response — always re-ask
    - _Bug_Condition: isBugCondition(input) where userResponse is NOT in confirmWords AND NOT in declineWords AND agent proceeds to process refund_
    - _Expected_Behavior: Agent re-asks for explicit confirmation instead of processing refund_
    - _Preservation: Explicit YES/NO responses continue to work as before_
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2_

  - [x] 3.2 Add strict tool response verification gate and anti-hallucination guard
    - In the OUTAGE REFUND FLOW section, restructure step 4 to make tool verification a hard gate:
    - After calling create_wallet_entry or update_wallet_amount, STOP and inspect the response
    - SUCCESS = response is a list containing data (e.g., `[{"id": ..., "amount": ...}]`)
    - FAILURE = response contains "success": False, contains "error", is empty, or is None
    - Only on SUCCESS: tell the user the credit was applied with the amount
    - On FAILURE: tell the user "I'm sorry, I wasn't able to process the refund right now" and offer to retry or escalate
    - Add anti-hallucination guard: "NEVER say 'I've applied a credit' or 'The credit has been added' unless you have received a successful tool response in this turn. If you are unsure whether the tool succeeded, say so."
    - _Bug_Condition: isBugCondition(input) where toolCallResult is null, error, or success=False AND agent claims credit applied_
    - _Expected_Behavior: Agent informs user refund could not be processed and offers retry/escalation_
    - _Preservation: Successful tool responses continue to trigger credit confirmation_
    - _Requirements: 2.4, 2.5, 3.5_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** — Non-Confirmation Responses No Longer Trigger Refund
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (confirmation word gate, ambiguous handling, tool verification)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** — Existing Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint — Ensure all tests pass
  - Run full test suite to confirm both bug condition and preservation tests pass
  - Ensure all tests pass, ask the user if questions arise
