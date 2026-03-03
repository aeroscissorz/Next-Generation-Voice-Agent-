# Bugfix Requirements Document

## Introduction

The voice agent skips self-introduction when greeting callers. Instead of first identifying itself as "Jessica from Verizon support," it jumps directly to a generic greeting like "thanks for calling in" and then asks for the user ID. The correct greeting flow should be: (1) self-introduction with agent name and company, (2) warm greeting, (3) ask for user ID. This affects the caller experience by making the interaction feel impersonal and not establishing trust at the start of the call.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a voice call is initiated THEN the system greets the user with a generic phrase like "thanks for calling in" without first introducing itself by name and company

1.2 WHEN a voice call is initiated THEN the system asks for the user ID immediately after the generic greeting, skipping the self-introduction step entirely

1.3 WHEN the voice system prompt (`eleven_labs_prompts/system.md`) is loaded THEN the system has no instruction to introduce itself by name or company affiliation before greeting the caller

### Expected Behavior (Correct)

2.1 WHEN a voice call is initiated THEN the system SHALL first introduce itself by saying its name and company (e.g., "Hi, I am Jessica from Verizon support") before any other greeting

2.2 WHEN a voice call is initiated THEN the system SHALL follow the self-introduction with a warm greeting and then ask for the user ID, in that specific order

2.3 WHEN the voice system prompt is loaded THEN the system SHALL contain explicit instructions defining the agent's identity as "Jessica" from "Verizon support" and the required greeting sequence: (1) self-introduction, (2) warm greeting, (3) ask for user ID

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the user has already been greeted and identified THEN the system SHALL CONTINUE TO handle billing, roaming, outage, and other support queries as before

3.2 WHEN the voice agent is in mid-conversation (past the greeting phase) THEN the system SHALL CONTINUE TO use the existing warm, compassionate tone and 1-3 sentence response style

3.3 WHEN the user provides their user ID THEN the system SHALL CONTINUE TO call `validate_user` and authenticate the user as before without re-introducing itself

3.4 WHEN the voice session is configured via the `/voice/token` endpoint THEN the system SHALL CONTINUE TO use the same OpenAI Realtime model, voice ("coral"), VAD settings, and tool definitions
