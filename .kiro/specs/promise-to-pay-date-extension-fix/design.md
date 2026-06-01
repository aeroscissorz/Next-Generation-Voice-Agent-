# Promise-to-Pay Date Extension Fix — Bugfix Design

## Overview

When a user already has a promise-to-pay date on an overdue invoice and asks to extend or change it, the agent fails to handle the request correctly. It either restarts the full overdue-consequences flow or sets the wrong date. The root cause is that the "Bill overdue flow" section in `Backend/instructions.py` has no branch for modifying an existing promise date — every interaction is treated as a first-time setup. The fix is a targeted prompt-engineering change: add an early detection step in the overdue flow that checks for an existing promise date and, if found, routes extension requests to a streamlined update path using the existing `get_promise_date` and `set_promise_date` tools.

## Glossary

- **Bug_Condition (C)**: The user has an existing promise-to-pay date on an overdue invoice AND requests to change or extend that date
- **Property (P)**: The agent recognizes the extension request, retrieves the current promise date, and updates it to the user's requested date (absolute or relative) without repeating the overdue-consequences flow
- **Preservation**: All existing behavior for first-time overdue interactions, payment flows, ineligible users, and out-of-range date validation must remain unchanged
- **UNIFIED_INSTRUCTION**: The prompt string in `Backend/instructions.py` that governs all agent behavior
- **Bill overdue flow**: The section within UNIFIED_INSTRUCTION that handles overdue bill conversations
- **set_promise_date**: Tool in `Backend/tools/billing_tools.py` that sets or updates the promise date on an invoice (already supports updates and validates the 7-day window)
- **get_promise_date**: Tool in `Backend/tools/billing_tools.py` that retrieves the current promise date for an invoice

## Bug Details

### Bug Condition

The bug manifests when a user who already has a promise-to-pay date set on an overdue invoice asks to extend or change that date. The "Bill overdue flow" instructions always force the full overdue-consequences sequence (invoice summary → three consequences → "would you like to pay now?") regardless of whether a promise date already exists, because there is no conditional branch to detect and handle extension requests.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type UserMessage with conversation context
  OUTPUT: boolean

  RETURN userHasExistingPromiseDate(input.userId, input.invoiceId)
         AND userIsRequestingDateChange(input.message)
         AND (isAbsoluteDateRequest(input.message) OR isRelativeDateRequest(input.message))
END FUNCTION
```

### Examples

- User says "can I get one more day?" when promise date is March 7 → Expected: agent retrieves March 7, calculates March 8, calls `set_promise_date` with March 8, confirms. Actual: agent restarts overdue flow with consequences.
- User says "move my promise date to March 8" when promise date is March 7 → Expected: agent calls `set_promise_date` with March 8, confirms. Actual: agent denies or sets wrong date.
- User says "I need to push my promise date back a couple days" when promise date is March 5 → Expected: agent retrieves March 5, calculates March 7, calls `set_promise_date` with March 7, confirms. Actual: agent restarts overdue flow.
- User says "can I extend to March 15?" when overdue date is March 1 (max = March 8) → Expected: `set_promise_date` returns error, agent relays max date and asks user to pick a new one. Actual: same as correct behavior if the tool is reached, but the bug prevents reaching the tool.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- First-time overdue bill interactions (no existing promise date) must continue to show the full consequences flow before offering Promise to Pay
- The `set_promise_date` tool's 7-day validation must continue to reject out-of-range dates, and the agent must relay the error
- Users who say they want to pay now must continue through the Make a Payment flow
- Users ineligible for Promise to Pay (`is_eligible_promise_to_pay` is false) must continue to be told they are not eligible
- All non-overdue flows (refunds, roaming, billing inquiries, etc.) must be completely unaffected

**Scope:**
All inputs where the user does NOT have an existing promise-to-pay date, or where the user is not requesting a date change, should be completely unaffected by this fix. This includes:
- First-time overdue bill mentions
- Payment requests
- Non-billing conversations
- Promise-to-pay setup for users who don't yet have one

## Hypothesized Root Cause

Based on the bug description and analysis of `Backend/instructions.py`, the root cause is:

1. **Missing conditional branch in "Bill overdue flow"**: The flow's step 1 calls `get_user_invoices` and checks `overdue_date` and `status`, but never checks `promise_date`. There is no early exit for users who already have a promise date set.

2. **No extension detection logic**: The instructions contain no language to recognize phrases like "extend my promise date", "move my date", "one more day", or "push it back" as modification requests distinct from first-time setup.

3. **Forced linear flow**: Steps 2–4 are written as a strict sequence (show consequences → ask to pay → only then offer Promise to Pay). There is no way to skip to the update step when the user already has a promise date and just wants to change it.

4. **No guidance for relative date calculation**: The instructions never tell the agent to call `get_promise_date` first and then compute a new date from a relative request like "one more day".

## Correctness Properties

Property 1: Bug Condition — Extension requests update the promise date directly

_For any_ user message where the user has an existing promise-to-pay date and requests to change or extend it (isBugCondition returns true), the fixed agent instructions SHALL cause the agent to retrieve the current promise date, determine the new target date (from an absolute or relative request), call `set_promise_date` with the new date, and confirm the result to the user — without repeating the overdue-consequences flow.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — First-time overdue and other flows unchanged

_For any_ user message where the user does NOT have an existing promise-to-pay date, or is not requesting a date change (isBugCondition returns false), the fixed agent instructions SHALL produce the same agent behavior as the original instructions, preserving the full overdue-consequences flow for first-time interactions, payment flows, eligibility checks, and all non-overdue functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `Backend/instructions.py`

**Section**: `Bill overdue flow` within `UNIFIED_INSTRUCTION`

**Specific Changes**:

1. **Add early promise-date check**: After step 1 (calling `get_user_invoices`), add a new conditional branch: "If the user already has a `promise_date` set on the invoice AND the user's message is asking to extend, change, or move that date, go to the PROMISE DATE EXTENSION sub-flow below. Do NOT proceed to step 2."

2. **Add PROMISE DATE EXTENSION sub-flow**: Insert a new labeled sub-flow within the Bill overdue flow section with these steps:
   - Step E1: Call `get_promise_date(user_id, invoice_id)` to retrieve the current promise date.
   - Step E2: Determine the new target date:
     - If the user gave an absolute date (e.g., "March 8"), use that date directly.
     - If the user gave a relative request (e.g., "one more day", "push it back 2 days"), add the requested number of days to the current promise date.
   - Step E3: Confirm the new date with the user before calling the tool: "I can move your Promise to Pay date from [current date] to [new date]. Shall I go ahead?"
   - Step E4: On confirmation, call `set_promise_date(user_id, invoice_id, new_date)`.
   - Step E5: If the tool succeeds, confirm: "Done — your Promise to Pay date is now [new date]."
   - Step E6: If the tool returns an error (e.g., date exceeds 7-day window), relay the max date from the error and ask the user to pick a new date within range.

3. **Add detection guidance**: Include example phrases the agent should recognize as extension requests: "extend my promise date", "move my date to", "push it back", "one more day", "can I get an extension", "change my promise date".

4. **Add guard against re-showing consequences**: Explicitly state that when an existing promise date is detected and the user is requesting an extension, the agent must NOT repeat the overdue-consequences summary or ask "would you like to pay now?"

5. **Preserve existing flow entry**: Add a note that if the user has a promise date but is NOT asking to change it (e.g., they ask "what's my promise date?" or "I want to pay now"), the existing flow steps should still apply as-is.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Construct agent prompt scenarios where a user has an existing promise date and sends extension requests. Run these against the UNFIXED `UNIFIED_INSTRUCTION` to observe that the agent restarts the overdue flow instead of handling the extension.

**Test Cases**:
1. **Absolute date extension**: User has promise date March 7, says "can you move my promise date to March 8?" — expect agent to restart overdue flow (will fail on unfixed code)
2. **Relative date extension**: User has promise date March 7, says "can I get one more day?" — expect agent to restart overdue flow (will fail on unfixed code)
3. **Multi-day relative extension**: User has promise date March 5, says "push it back 2 days" — expect agent to restart overdue flow (will fail on unfixed code)
4. **Out-of-range extension**: User has promise date March 7 (max March 8), says "extend to March 15" — expect agent to either restart overdue flow or not reach the tool validation (will fail on unfixed code)

**Expected Counterexamples**:
- Agent responds with full overdue-consequences summary instead of acknowledging the extension request
- Agent does not call `get_promise_date` to retrieve the current date
- Possible causes: no conditional branch for existing promise date, no extension detection logic

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed instructions produce the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := agentResponse_fixed(input)
  ASSERT result does NOT contain overdue-consequences summary
  ASSERT result calls get_promise_date
  ASSERT result calls set_promise_date with correct new date
  ASSERT result confirms the updated date to the user
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed instructions produce the same agent behavior as the original instructions.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT agentResponse_original(input) ≈ agentResponse_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many conversation scenarios automatically across the input domain
- It catches edge cases where the new branch might accidentally trigger on non-extension inputs
- It provides strong guarantees that first-time overdue flows, payment flows, and eligibility checks are unchanged

**Test Plan**: Observe behavior on UNFIXED code first for first-time overdue interactions, payment requests, and ineligible users, then write property-based tests capturing that behavior.

**Test Cases**:
1. **First-time overdue preservation**: User mentions overdue bill with no existing promise date — verify full consequences flow still triggers after fix
2. **Payment flow preservation**: User with overdue bill says "I want to pay now" — verify Make a Payment flow is unchanged
3. **Ineligibility preservation**: User with `is_eligible_promise_to_pay` = false — verify agent still denies Promise to Pay
4. **Out-of-range error preservation**: User requests date beyond 7-day window — verify `set_promise_date` error is still relayed correctly

### Unit Tests

- Test that the instruction text contains the new PROMISE DATE EXTENSION sub-flow
- Test that extension-detection phrases are present in the instructions
- Test that the guard against re-showing consequences is present
- Test that the existing overdue flow steps are preserved unchanged for non-extension cases

### Property-Based Tests

- Generate random conversation contexts (with/without existing promise dates, various message types) and verify the correct flow branch is taken
- Generate random date extension requests (absolute and relative) and verify the agent instructions would route to the extension sub-flow
- Generate random non-extension overdue messages and verify the original flow is preserved

### Integration Tests

- End-to-end test: user with existing promise date asks for one more day → agent retrieves date, calculates new date, confirms, updates
- End-to-end test: user with existing promise date gives absolute date → agent confirms and updates
- End-to-end test: user with existing promise date asks for extension beyond 7-day window → agent relays error from tool
- End-to-end test: user with no promise date mentions overdue bill → full consequences flow triggers as before
