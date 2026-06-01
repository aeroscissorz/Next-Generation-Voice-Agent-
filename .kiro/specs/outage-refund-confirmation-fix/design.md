# Outage Refund Confirmation Fix — Bugfix Design

## Overview

The AI telecom support agent auto-credits outage refunds without explicit user confirmation. The agent misinterprets complaints, questions, and ambiguous responses as "yes, process the refund," and also claims credits were applied without verifying tool call success. The fix is entirely prompt engineering — tightening the OUTAGE REFUND FLOW section in `Backend/instructions.py` by adding explicit confirmation word lists, ambiguity handling rules, and strict tool response verification instructions.

## Glossary

- **Bug_Condition (C)**: The agent receives a non-explicit-confirmation response (complaint, question, ambiguous statement) to the refund prompt, yet proceeds to process the refund — OR the agent claims credit was applied without verifying tool success.
- **Property (P)**: The agent SHALL only process a refund after receiving an explicit confirmation word, and SHALL only confirm credit application after verifying the tool returned success.
- **Preservation**: Existing behavior for explicit YES/NO responses, refund calculation formula, automatic outage lookup, and successful tool confirmation must remain unchanged.
- **UNIFIED_INSTRUCTION**: The prompt string in `Backend/instructions.py` that governs all agent behavior, including the OUTAGE REFUND FLOW section.
- **create_wallet_entry / update_wallet_amount**: Billing tools in `Backend/tools/billing_tools.py` that create or update wallet credits. These are NOT modified by this fix.
- **Explicit Confirmation**: A response from the user that unambiguously means "yes, proceed" — e.g., "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep".
- **Explicit Decline**: A response that unambiguously means "no" — e.g., "no", "no thanks", "never mind", "cancel", "don't", "skip".
- **Ambiguous Response**: A response that is neither explicit confirmation nor explicit decline — e.g., "I guess", "maybe", "let me think", "hmm", or any complaint/question about the refund.

## Bug Details

### Bug Condition

The bug manifests when the agent asks "Would you like me to process a refund for this?" and the user responds with anything other than an explicit confirmation or decline. The agent's current instructions lack a strict definition of what counts as confirmation, so the LLM interprets complaints, questions, and ambiguous statements as implicit agreement. Additionally, the agent tells the user "I've applied this credit" without checking whether the tool call actually succeeded.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { userResponse: string, toolCallResult: any }
  OUTPUT: boolean

  confirmWords = ["yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"]
  declineWords = ["no", "no thanks", "never mind", "cancel", "don't", "skip"]

  responseIsExplicitConfirm = ANY word IN confirmWords IS PRESENT IN lower(input.userResponse)
  responseIsExplicitDecline = ANY word IN declineWords IS PRESENT IN lower(input.userResponse)

  // Bug path 1: Non-confirmation treated as confirmation
  nonConfirmTreatedAsYes = NOT responseIsExplicitConfirm
                           AND NOT responseIsExplicitDecline
                           AND agentProceedsToProcessRefund()

  // Bug path 2: Credit claimed without tool verification
  creditClaimedWithoutVerification = agentClaimsCreditApplied()
                                     AND (input.toolCallResult IS NULL
                                          OR input.toolCallResult.success == False
                                          OR input.toolCallResult CONTAINS "error")

  RETURN nonConfirmTreatedAsYes OR creditClaimedWithoutVerification
END FUNCTION
```

### Examples

- User says "This is too low for me" → Agent processes refund anyway (BUG). Expected: Agent acknowledges dissatisfaction, explains policy cap, re-asks for confirmation.
- User says "How much will you refund me?" → Agent processes refund anyway (BUG). Expected: Agent answers the question with the calculated amount, then re-asks for confirmation.
- User says "I guess" → Agent processes refund (BUG). Expected: Agent asks "Just to confirm — would you like me to go ahead and apply the ₹[amount] credit?"
- Tool call returns `{"success": False, "error": "duplicate key"}` → Agent says "I've applied ₹677 as a credit" (BUG). Expected: Agent says the refund could not be processed and offers to retry or escalate.
- User says "yes" → Agent processes refund (CORRECT — must be preserved).
- User says "no thanks" → Agent does not process refund (CORRECT — must be preserved).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Explicit YES responses ("yes", "sure", "go ahead", "proceed", "please do", "okay", "yep") must continue to trigger refund processing
- Explicit NO responses ("no", "no thanks", "never mind", "cancel") must continue to halt refund processing
- Refund calculation formula `(outage_days / days_in_month) × invoice_amount` must remain unchanged
- Automatic outage lookup (area from invoices → check_outage) must remain unchanged
- When tool call returns successfully with data, the agent must continue to confirm the credit to the user
- The conversational tone and warmth of the agent must be preserved
- All other flows (bill overdue, payment, roaming, etc.) must be completely unaffected

**Scope:**
All inputs that do NOT involve the outage refund confirmation step should be completely unaffected by this fix. This includes:
- All non-outage conversation flows (billing, roaming, payments, tickets)
- The outage lookup steps (steps 1-3 of the flow) before the confirmation prompt
- The refund calculation logic
- Any tool calls outside the outage refund context

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **Missing Confirmation Word List**: The OUTAGE REFUND FLOW says "Only if the user confirms they want a refund" but does not define what "confirms" means. The LLM has no explicit list of acceptable confirmation words, so it interprets any non-negative response as implicit confirmation.

2. **No Handling for Ambiguous/Non-Confirmation Responses**: The instructions have no branch for complaints, questions, or ambiguous statements. The flow goes from "ask the user" directly to "process the refund," with no intermediate handling for responses that are neither YES nor NO.

3. **No Tool Response Verification Instructions**: Step 4 says "CRITICAL: You MUST actually call the tool... and wait for its response" but the instruction to check the response is buried and not structured as a strict gate. The LLM sometimes skips verification and jumps to the confirmation message.

4. **Complaint Misinterpretation**: When a user says "This is too low," the LLM interprets the user's engagement with the refund amount as implicit acceptance of the refund itself, because the instructions don't explicitly say "a complaint about the amount is NOT confirmation."

## Correctness Properties

Property 1: Bug Condition — Non-Confirmation Responses Must Not Trigger Refund Processing

_For any_ user response to the refund confirmation prompt that is NOT an explicit confirmation word (from the defined YES list: "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"), the fixed OUTAGE REFUND FLOW instructions SHALL prevent the agent from calling create_wallet_entry or update_wallet_amount, and SHALL instead handle the response appropriately (acknowledge complaint, answer question, or ask for explicit confirmation).

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Bug Condition — Tool Response Must Be Verified Before Confirming Credit

_For any_ refund processing attempt where the tool call (create_wallet_entry or update_wallet_amount) returns an error, "success": False, or is not executed, the fixed instructions SHALL prevent the agent from telling the user the credit was applied, and SHALL instead inform the user the refund could not be processed.

**Validates: Requirements 2.4, 2.5**

Property 3: Preservation — Explicit Confirmations and Declines Continue Working

_For any_ user response that IS an explicit confirmation word ("yes", "sure", "go ahead", etc.) or an explicit decline word ("no", "no thanks", "cancel", etc.), the fixed instructions SHALL produce the same behavior as the original instructions — processing the refund on confirmation, halting on decline.

**Validates: Requirements 3.1, 3.2, 3.5**

Property 4: Preservation — Refund Calculation and Outage Lookup Unchanged

_For any_ outage refund flow invocation, the fixed instructions SHALL preserve the existing refund calculation formula, automatic area lookup from invoices, and the conversational structure of steps 1-3.

**Validates: Requirements 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `Backend/instructions.py`

**Section**: OUTAGE REFUND FLOW (within the `UNIFIED_INSTRUCTION` string)

**Specific Changes**:

1. **Add Explicit Confirmation Word List**: Insert a clearly defined YES list after step 3, before the refund processing step. Format it identically to the payment flow's confirmation list for consistency:
   - YES (proceed with refund): "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep"
   - NO (cancel refund): "no", "no thanks", "never mind", "cancel", "don't", "skip"

2. **Add Ambiguous Response Handling**: Add a new branch for responses that match neither YES nor NO:
   - If the response is a complaint about the amount (e.g., "too low", "not enough", "expected more"): acknowledge the frustration, explain the calculation and policy cap, then re-ask for confirmation
   - If the response is a question (e.g., "how much?", "what's the amount?"): answer the question with the calculated amount and formula, then re-ask for confirmation
   - If the response is ambiguous (e.g., "I guess", "maybe", "hmm", "let me think"): ask explicitly "Just to confirm — would you like me to go ahead and apply the ₹[amount] credit to your account?"
   - CRITICAL: Do NOT process the refund on any of these responses. Always re-ask.

3. **Strengthen Tool Response Verification**: Restructure step 4 to make verification a hard gate:
   - After calling create_wallet_entry or update_wallet_amount, STOP and inspect the response
   - SUCCESS = response is a list containing data (e.g., `[{"id": ..., "amount": ...}]`)
   - FAILURE = response contains `"success": False`, contains `"error"`, is empty, or is None
   - Only on SUCCESS: tell the user the credit was applied with the amount
   - On FAILURE: tell the user "I'm sorry, I wasn't able to process the refund right now" and offer to retry or escalate

4. **Add Anti-Hallucination Guard**: Add an explicit instruction: "NEVER say 'I've applied a credit' or 'The credit has been added' unless you have received a successful tool response in this turn. If you are unsure whether the tool succeeded, say so."

5. **Restructure Flow as Numbered Decision Tree**: Rewrite the confirmation handling as a clear if/else decision tree so the LLM has unambiguous branching logic rather than prose instructions.

### Files NOT Modified

- `Backend/tools/billing_tools.py` — No changes. The `id:1` hardcoded value in `create_wallet_entry` is a known issue but is explicitly out of scope for this fix.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior. Since this is a prompt engineering fix, testing involves sending conversation transcripts through the agent and observing its behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Send simulated conversation flows through the agent where the user responds to the refund confirmation prompt with non-confirmation responses. Observe whether the agent processes the refund anyway.

**Test Cases**:
1. **Complaint Response Test**: User says "This is too low for me" after refund offer → expect agent does NOT process refund (will fail on unfixed code)
2. **Question Response Test**: User says "How much exactly?" after refund offer → expect agent does NOT process refund (will fail on unfixed code)
3. **Ambiguous Response Test**: User says "I guess" or "maybe" after refund offer → expect agent does NOT process refund (will fail on unfixed code)
4. **Tool Failure Test**: Simulate create_wallet_entry returning `{"success": False, "error": "..."}` → expect agent does NOT claim credit was applied (will fail on unfixed code)

**Expected Counterexamples**:
- Agent calls create_wallet_entry or update_wallet_amount after receiving a complaint or question
- Agent says "I've applied the credit" when tool call was never made or returned an error
- Possible causes: missing confirmation word gate, no ambiguous response branch, no tool verification gate

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed instructions produce the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := agentWithFixedInstructions(input)
  ASSERT NOT result.refundProcessed OR result.toolCallVerified
  ASSERT NOT result.creditClaimedWithoutSuccess
  ASSERT result.reAskedForConfirmation OR result.informedOfFailure
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed instructions produce the same result as the original instructions.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT agentWithOriginalInstructions(input) = agentWithFixedInstructions(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many conversation variations automatically across the input domain
- It catches edge cases where the tightened instructions might accidentally block valid confirmations
- It provides strong guarantees that behavior is unchanged for explicit YES/NO responses

**Test Plan**: Observe behavior on UNFIXED instructions first for explicit confirmations and declines, then write tests capturing that behavior.

**Test Cases**:
1. **Explicit YES Preservation**: Verify that "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep" all still trigger refund processing after the fix
2. **Explicit NO Preservation**: Verify that "no", "no thanks", "never mind", "cancel" all still halt refund processing after the fix
3. **Refund Calculation Preservation**: Verify the formula `(outage_days / days_in_month) × invoice_amount` is still used and shown to the user
4. **Outage Lookup Preservation**: Verify the agent still auto-retrieves area from invoices and calls check_outage without asking the user

### Unit Tests

- Test each confirmation word individually to ensure it triggers refund processing
- Test each decline word individually to ensure it halts refund processing
- Test complaint phrases ("too low", "not enough", "expected more") to ensure re-ask behavior
- Test question phrases ("how much?", "what's the amount?") to ensure answer-then-re-ask behavior
- Test ambiguous phrases ("I guess", "maybe", "hmm") to ensure explicit re-ask behavior
- Test tool failure responses to ensure the agent does not claim credit was applied

### Property-Based Tests

- Generate random non-confirmation user responses and verify the agent never processes a refund without re-asking
- Generate random explicit confirmation words from the YES list and verify the agent always processes the refund
- Generate random explicit decline words from the NO list and verify the agent never processes the refund
- Generate random tool failure responses and verify the agent never claims credit was applied

### Integration Tests

- Full outage refund flow: outage lookup → offer refund → complaint → re-ask → explicit yes → tool success → confirm credit
- Full outage refund flow: outage lookup → offer refund → ambiguous → re-ask → explicit no → no refund
- Full outage refund flow: outage lookup → offer refund → yes → tool failure → inform user → offer retry
- Verify other flows (payment, overdue, roaming) are completely unaffected by the instruction changes
