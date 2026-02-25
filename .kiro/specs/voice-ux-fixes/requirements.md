# Requirements Document

## Introduction

This feature addresses two UX issues in the voice-based telecom customer support application. First, the voice assistant is difficult to interrupt while speaking due to overly conservative server-side VAD (Voice Activity Detection) settings. Second, the system accepts arbitrary numeric strings as user IDs without proper format or length validation, allowing invalid IDs to reach the database query unnecessarily.

## Glossary

- **VAD**: Voice Activity Detection — server-side mechanism that detects when a user is speaking to allow turn-taking in voice conversations.
- **VAD_Threshold**: A float value (0.0–1.0) controlling the sensitivity of voice detection. Lower values detect quieter speech; higher values require louder speech.
- **Silence_Duration**: The duration in milliseconds of silence required before the system considers the user's turn complete.
- **Prefix_Padding**: The duration in milliseconds of audio captured before detected speech onset, ensuring the beginning of utterances is not clipped.
- **Interceptor**: The Python FastAPI middleware service that manages voice sessions, tool calls, and communication between the frontend and OpenAI Realtime API.
- **User_ID**: A numeric identifier used to authenticate callers against the `users_voice` Supabase table.
- **Extract_Function**: The `extract_user_id_from_spoken()` function in `Interceptor/utils/helpers.py` that normalizes raw spoken input into a user ID string.
- **Validate_Function**: The `validate_user_id()` method in `Interceptor/services/voice_auth.py` that checks a user ID against the database.
- **Voice_Auth_Service**: The `VoiceAuthService` class that manages voice authentication state and user validation.

## Requirements

### Requirement 1: Improve VAD Responsiveness for Easier Interruption

**User Story:** As a caller, I want to interrupt the voice assistant more easily while it is speaking, so that I can correct misunderstandings or redirect the conversation without waiting.

#### Acceptance Criteria

1. THE Interceptor SHALL configure the VAD_Threshold to a value between 0.55 and 0.60 inclusive.
2. THE Interceptor SHALL configure the Silence_Duration to a value between 350 and 450 milliseconds inclusive.
3. THE Interceptor SHALL configure the Prefix_Padding to a value between 180 and 220 milliseconds inclusive.
4. WHEN the Interceptor creates an OpenAI Realtime session, THE Interceptor SHALL include the VAD_Threshold, Silence_Duration, and Prefix_Padding values in the `turn_detection` configuration.

### Requirement 2: Validate User ID Format Before Database Query

**User Story:** As a system operator, I want the system to reject obviously invalid user IDs before querying the database, so that unnecessary database calls are avoided and callers receive faster feedback.

#### Acceptance Criteria

1. WHEN the Extract_Function receives spoken input, THE Extract_Function SHALL strip all non-alphanumeric characters and return only digit characters.
2. WHEN the Extract_Function produces a result that is fewer than 2 digits or more than 10 digits, THE Extract_Function SHALL return an empty string.
3. WHEN the Validate_Function receives a User_ID, THE Validate_Function SHALL reject the User_ID with a descriptive message if the User_ID length is fewer than 2 digits or more than 10 digits.
4. WHEN the Validate_Function rejects a User_ID, THE Validate_Function SHALL return a tuple of (False, None, message) where message describes the rejection reason.
5. WHEN the Validate_Function successfully validates a User_ID against the database, THE Validate_Function SHALL return a tuple of (True, customer_id, message).

### Requirement 3: Ensure Proper Tool Call Response Structure for Failed Validation

**User Story:** As a caller, I want to receive clear feedback when my user ID is not recognized, so that I can retry with the correct ID.

#### Acceptance Criteria

1. WHEN the `_handle_validate_user` handler receives an empty User_ID after extraction, THE Interceptor SHALL return a JSON response with `authenticated` set to false and a `reason` field describing the issue.
2. WHEN the Validate_Function returns a failed validation result, THE `_handle_validate_user` handler SHALL return a JSON response with `authenticated` set to false, a `reason` field, and a `message` field containing the validation message.
3. WHEN the Validate_Function returns a successful validation result, THE `_handle_validate_user` handler SHALL return a JSON response with `authenticated` set to true, the `customer_id`, and a `message` field.

### Requirement 4: Add Logging for User ID Validation Flow

**User Story:** As a developer, I want detailed logging throughout the user ID validation flow, so that I can diagnose authentication issues in production.

#### Acceptance Criteria

1. WHEN the Extract_Function processes spoken input, THE Extract_Function SHALL log the raw input and the normalized output at INFO level.
2. WHEN the Extract_Function rejects input due to length constraints, THE Extract_Function SHALL log the rejection reason at INFO level.
3. WHEN the Validate_Function receives a User_ID, THE Validate_Function SHALL log the received User_ID and its length at INFO level.
4. WHEN the Validate_Function completes validation (success or failure), THE Validate_Function SHALL log the outcome at INFO level.
