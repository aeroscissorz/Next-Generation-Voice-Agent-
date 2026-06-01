# Bugfix Requirements Document

## Introduction

The AI telecom support agent (built with ADK) processes outage refunds without receiving explicit user confirmation. In observed conversation transcripts, the agent interpreted a complaint ("This is too low for me") as confirmation to proceed with a refund, then claimed a credit was applied to the customer's account. The root cause is that the OUTAGE REFUND FLOW instructions in `Backend/instructions.py` lack strict guardrails defining what constitutes explicit confirmation, how to handle non-confirmations (complaints, questions, ambiguous responses), and the requirement to verify tool call success before claiming a credit was applied.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the agent asks "Would you like me to process this refund?" and the user responds with a complaint (e.g., "This is too low for me", "That's not enough", "I expected more") THEN the system treats the complaint as confirmation and proceeds to process the refund

1.2 WHEN the agent asks for refund confirmation and the user responds with a question about the refund amount (e.g., "How much will you refund me?", "What's the amount?") THEN the system treats the question as confirmation and proceeds to process the refund

1.3 WHEN the agent asks for refund confirmation and the user responds with an ambiguous or non-committal statement (e.g., "I guess", "maybe", "let me think") THEN the system treats the ambiguous response as confirmation and proceeds to process the refund

1.4 WHEN the agent processes a refund but the tool call (create_wallet_entry or update_wallet_amount) fails or is not actually executed THEN the system tells the user "I've applied this amount as a credit to your account" without verifying the tool response

1.5 WHEN the agent processes a refund and the tool call returns an error or "success": False THEN the system still tells the user the credit was applied successfully

### Expected Behavior (Correct)

2.1 WHEN the agent asks "Would you like me to process this refund?" and the user responds with a complaint (e.g., "This is too low for me", "That's not enough") THEN the system SHALL acknowledge the user's dissatisfaction, explain the refund calculation and policy cap, and re-ask whether the user would like to proceed with the calculated amount

2.2 WHEN the agent asks for refund confirmation and the user responds with a question about the refund amount THEN the system SHALL answer the question (provide the calculated amount and formula) and then re-ask for explicit confirmation to proceed

2.3 WHEN the agent asks for refund confirmation and the user responds with an ambiguous or non-committal statement THEN the system SHALL ask for explicit confirmation by saying something like "Just to confirm — would you like me to go ahead and apply the ₹[amount] credit to your account?"

2.4 WHEN the agent processes a refund THEN the system SHALL only confirm the credit was applied after verifying that the tool call (create_wallet_entry or update_wallet_amount) returned a successful response (a list with data, not an error)

2.5 WHEN the agent processes a refund and the tool call returns an error or "success": False THEN the system SHALL inform the user that the refund could not be processed and offer to retry or escalate to a human agent

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the user explicitly confirms the refund with words like "yes", "sure", "go ahead", "proceed", "please do", "okay", "yep" THEN the system SHALL CONTINUE TO process the refund by calling the appropriate wallet tool and confirming the result

3.2 WHEN the user explicitly declines the refund with words like "no", "no thanks", "never mind", "cancel" THEN the system SHALL CONTINUE TO respect the user's decision and not process the refund

3.3 WHEN the outage refund is calculated THEN the system SHALL CONTINUE TO use the formula (outage_days / days_in_month) × invoice_amount and show the calculation to the user

3.4 WHEN the agent looks up outage information THEN the system SHALL CONTINUE TO automatically retrieve the user's area from invoices and call check_outage without asking the user for outage dates or area

3.5 WHEN the tool call (create_wallet_entry or update_wallet_amount) returns successfully with data THEN the system SHALL CONTINUE TO confirm the credit to the user and provide the amount applied
