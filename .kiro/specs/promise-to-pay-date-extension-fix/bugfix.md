# Bugfix Requirements Document

## Introduction

When a user already has a promise-to-pay date set on an overdue invoice and requests to extend or change it to a new date (e.g., from March 7 to March 8), the agent either denies the request or sets an incorrect date. This happens because the "Bill overdue flow" instructions in `Backend/instructions.py` have no handling for modifying an existing promise-to-pay date. The flow always forces the full overdue-consequences sequence and treats every promise-to-pay interaction as a first-time setup, with no path for date extension when a promise date already exists. The `set_promise_date` tool in `Backend/tools/billing_tools.py` already supports updating an existing date and correctly validates the 7-day window — the bug is purely in the prompt instructions that govern agent behavior.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user has an existing promise-to-pay date and asks to extend it to a new date within the 7-day grace period THEN the system forces the full overdue-consequences flow (invoice summary, three consequences, "would you like to pay now?") instead of recognizing the extension request

1.2 WHEN a user has an existing promise-to-pay date and explicitly requests a specific new date (e.g., "can you move my promise date to March 8?") THEN the system either denies the request or sets a different date than what the user asked for, because the instructions have no path for modifying an existing promise date

1.3 WHEN a user has an existing promise-to-pay date and asks to extend it by a relative amount (e.g., "can I get one more day?") THEN the system does not retrieve the current promise date to calculate the new target date, and instead restarts the entire overdue flow

### Expected Behavior (Correct)

2.1 WHEN a user has an existing promise-to-pay date and asks to extend it to a new date within the 7-day grace period THEN the system SHALL recognize this as a date extension request, retrieve the current promise date using `get_promise_date`, and proceed directly to updating the date without repeating the overdue-consequences flow

2.2 WHEN a user has an existing promise-to-pay date and explicitly requests a specific new date (e.g., "can you move my promise date to March 8?") THEN the system SHALL call `set_promise_date` with the user's requested date, and if the tool succeeds, confirm the new date to the user

2.3 WHEN a user has an existing promise-to-pay date and asks to extend it by a relative amount (e.g., "can I get one more day?") THEN the system SHALL call `get_promise_date` to retrieve the current date, calculate the new date by adding the requested number of days, and call `set_promise_date` with the calculated date

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user mentions an overdue bill for the first time in a conversation and has no existing promise-to-pay date THEN the system SHALL CONTINUE TO show the full overdue-consequences flow (invoice details, three consequences, ask to pay now) before offering Promise to Pay

3.2 WHEN a user requests a promise-to-pay date extension but the new date exceeds the 7-day grace period from the overdue date THEN the system SHALL CONTINUE TO relay the error from `set_promise_date` and ask the user to choose a date within the allowed range

3.3 WHEN a user with an overdue bill explicitly says they want to pay now THEN the system SHALL CONTINUE TO follow the existing Make a Payment flow

3.4 WHEN a user is not eligible for Promise to Pay (`is_eligible_promise_to_pay` is false) THEN the system SHALL CONTINUE TO inform them they are not eligible and encourage payment
