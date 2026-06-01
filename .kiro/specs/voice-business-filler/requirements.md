# Requirements Document

## Introduction

The voice-business-filler feature enhances the Verizon telecom support voice agent ("Jessica") by replacing silent hold music during tool call processing with spoken, business-context-aware filler phrases delivered by the OpenAI Realtime voice agent itself. When a tool call begins, the frontend injects a system message into the WebRTC data channel prompting the model to speak a context-aware filler phrase in Jessica's own voice. If the tool call takes longer than expected, follow-up filler prompts are chained to fill the silence naturally. This eliminates hold music entirely and keeps the experience seamless — the same voice, the same persona, no jarring transitions.

The feature is implemented entirely in the **Frontend** (`VoiceInterface.jsx`):
- Detects the active tool call and classifies the user's intent
- Injects filler prompts into the OpenAI data channel so the model speaks them in its own voice
- Chains follow-up filler prompts if the tool call exceeds a time threshold
- Removes the existing `useHoldMusic` hook

## Glossary

- **Voice_Agent**: The OpenAI Realtime API-powered voice assistant named "Jessica" that handles telecom support calls via WebRTC.
- **Filler_Prompt**: A system message injected into the data channel (`conversation.item.create` with role `user` and `input_text`) that instructs the Voice_Agent to speak a brief, context-aware phrase while a tool call is in flight.
- **Follow_Up_Prompt**: A shorter Filler_Prompt sent when the tool call is still in flight after the initial filler response completes, to fill continued silence.
- **Filler_Orchestrator**: The frontend logic in `VoiceInterface.jsx` responsible for injecting Filler_Prompts, tracking tool call timing, and chaining Follow_Up_Prompts.
- **Tool_Call**: An invocation of a named function (`validate_user` or `forward_to_backend`) routed through the Interceptor during a voice session.
- **Intent**: A classified category of the user's request (e.g., `billing`, `roaming`, `outage`, `wallet`, `tickets`, `policy`, `validation`, `general`) derived from the user's last transcript.
- **Intent_Classifier**: A pure function that maps a user transcript to an Intent category using keyword matching.
- **Processing_Status**: The `processing` state in `VoiceInterface.jsx` that is active from the moment a tool call begins until the agent starts speaking the actual tool result response.
- **Hold_Music**: The synthesized elevator music played by `useHoldMusic.js` during Processing_Status — to be removed by this feature.
- **Filler_Response_Done**: The `response.done` event received after the Voice_Agent finishes speaking a filler phrase, distinct from the `response.done` after the actual tool result response.
- **Interceptor**: The Python/FastAPI middleware layer that handles voice tool calls and communicates with the backend AI agent.

---

## Requirements

### Requirement 1: Filler Prompt Injection via Data Channel

**User Story:** As a caller, I want the voice agent to speak a natural, context-aware phrase in her own voice while looking something up, so that there is no awkward silence and the experience feels like talking to a real person.

#### Acceptance Criteria

1. WHEN `response.function_call_arguments.done` is received and a Tool_Call begins, THE Filler_Orchestrator SHALL immediately inject a Filler_Prompt into the data channel as a `conversation.item.create` message with role `user` and type `input_text`.
2. THE Filler_Prompt SHALL instruct the Voice_Agent to speak a brief, context-aware phrase (1-2 sentences) relevant to the current Intent and tool name, without revealing it is a system instruction.
3. AFTER injecting the Filler_Prompt, THE Filler_Orchestrator SHALL send a `response.create` event to trigger the Voice_Agent to speak the filler immediately.
4. THE Filler_Orchestrator SHALL run the tool call (HTTP request to the Interceptor) in parallel with the filler prompt injection, so that the model speaks while the backend processes.
5. WHEN the tool call result is received, THE Filler_Orchestrator SHALL send the `function_call_output` and a `response.create` to deliver the actual response, which will naturally interrupt or follow the filler.

---

### Requirement 2: Follow-Up Filler for Long Tool Calls

**User Story:** As a caller, I want the agent to continue filling silence naturally if the lookup takes a long time, so that I don't experience dead air.

#### Acceptance Criteria

1. THE Filler_Orchestrator SHALL track whether the tool call result has been received using a ref or flag.
2. WHEN a Filler_Response_Done event is received (the model finished speaking the filler) AND the tool call result has NOT yet been received, THE Filler_Orchestrator SHALL inject a Follow_Up_Prompt into the data channel.
3. THE Follow_Up_Prompt SHALL instruct the Voice_Agent to speak a short reassurance phrase (e.g., "Still looking...", "Almost there...", "Bear with me one sec...") without repeating the previous filler.
4. THE Filler_Orchestrator SHALL send a maximum of 2 Follow_Up_Prompts per tool call to avoid sounding unnatural.
5. THE Filler_Orchestrator SHALL track the follow-up count per tool call and reset it when the tool call completes.

---

### Requirement 3: Intent Classification on the Frontend

**User Story:** As a developer, I want the frontend to classify the user's last spoken message into an Intent category, so that the filler prompts can be contextually relevant.

#### Acceptance Criteria

1. WHEN a user transcript is received via `conversation.item.input_audio_transcription.completed`, THE Intent_Classifier SHALL classify the transcript into one of the defined Intent categories (`billing`, `roaming`, `outage`, `wallet`, `tickets`, `policy`, `validation`, `general`) and store it in a ref.
2. THE Intent_Classifier SHALL use keyword pattern matching against the transcript text to determine the Intent category.
3. IF no keyword pattern matches the transcript, THEN THE Intent_Classifier SHALL assign the `general` Intent category.
4. THE Intent_Classifier SHALL update the stored Intent each time a new user transcript is received, replacing the previous value.
5. THE Intent_Classifier SHALL be implemented as a pure function that accepts a transcript string and returns an Intent category string.

---

### Requirement 4: Context-Aware Filler Prompt Content

**User Story:** As a voice UX designer, I want the filler prompts to vary based on the type of query, so that the agent sounds knowledgeable and specific rather than generic.

#### Acceptance Criteria

1. THE Filler_Orchestrator SHALL construct the Filler_Prompt text dynamically based on the tool name and the current stored Intent.
2. FOR `validate_user` tool calls, THE Filler_Prompt SHALL always instruct the model to speak a validation-related phrase (e.g., about verifying the account), regardless of the stored Intent.
3. FOR `forward_to_backend` tool calls, THE Filler_Prompt SHALL reference the specific Intent category (e.g., "checking billing", "looking into roaming", "checking for outages").
4. THE Filler_Prompt SHALL instruct the model to keep the phrase to 1-2 natural sentences and to not repeat phrases it has already said in this conversation.
5. THE Filler_Prompt SHALL be prefixed with `[System: ...]` to match the existing system message convention used in the codebase (e.g., greeting, silence nudges).

---

### Requirement 5: Filler and Tool Result Coordination

**User Story:** As a developer, I want the filler speech and tool result delivery to be coordinated cleanly, so that the agent doesn't talk over itself or produce garbled output.

#### Acceptance Criteria

1. THE Filler_Orchestrator SHALL use a state flag (`isFillerPhase`) to distinguish between filler `response.done` events and actual tool result `response.done` events.
2. WHEN the tool call result is received and the `function_call_output` is sent, THE Filler_Orchestrator SHALL set the `isFillerPhase` flag to `false` so that subsequent `response.done` events are handled normally.
3. THE Filler_Orchestrator SHALL NOT send any Follow_Up_Prompts after the tool call result has been sent.
4. IF the Voice_Agent is still speaking a filler phrase when the tool result arrives, the `response.create` for the tool result SHALL naturally cause the model to transition to the actual response.
5. THE Filler_Orchestrator SHALL reset all filler-related state (follow-up count, isFillerPhase flag, tool-call-pending flag) when the tool call processing completes.

---

### Requirement 6: Hold Music Removal

**User Story:** As a developer, I want the hold music to be removed and replaced entirely by voice agent filler, so that the audio experience is consistent.

#### Acceptance Criteria

1. THE Voice_Agent frontend SHALL remove the `useHoldMusic` import and all usage of `startMusic` and `stopMusic` from `VoiceInterface.jsx`.
2. THE Voice_Agent frontend SHALL NOT play any synthesized audio during tool call processing — all filler is handled by the Voice_Agent speaking via the data channel.
3. WHEN the voice session disconnects, THE Filler_Orchestrator SHALL reset all filler-related state.
4. THE `useHoldMusic.js` file SHALL be retained in the codebase but no longer imported or used, so it can be removed in a future cleanup pass.
