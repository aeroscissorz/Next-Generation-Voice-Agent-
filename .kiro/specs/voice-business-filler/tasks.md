# Implementation Plan: Voice Business Filler

## Overview

Replace hold music with context-aware spoken filler phrases injected via the WebRTC data channel during tool call processing. All changes are in the Frontend, primarily `VoiceInterface.jsx`. Pure helper functions (`classifyIntent`, `buildFillerPrompt`, `buildFollowUpPrompt`) are extracted into a co-located module for testability. The existing `useHoldMusic` hook is disconnected but the file is retained.

## Tasks

- [x] 1. Create filler helper module with pure functions
  - [x] 1.1 Create `Frontend/src/components/voiceFillerHelpers.js` with `classifyIntent`, `buildFillerPrompt`, and `buildFollowUpPrompt`
    - Implement `classifyIntent(transcript)` with keyword matching for 8 intent categories (`billing`, `roaming`, `outage`, `wallet`, `tickets`, `policy`, `validation`, `general`), defaulting to `general`
    - Implement `buildFillerPrompt(toolName, intent)` returning `[System: ...]` formatted strings — validation-themed for `validate_user`, intent-specific for `forward_to_backend`
    - Implement `buildFollowUpPrompt()` returning a `[System: ...]` formatted short reassurance prompt
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 2.3_

  - [ ]* 1.2 Write property test: Intent classifier always returns valid category (Property 1)
    - **Property 1: Intent classifier always returns a valid category and defaults to general**
    - Use fast-check to generate arbitrary strings, verify return is one of 8 categories, verify no-keyword strings return `general`, verify determinism (same input → same output)
    - **Validates: Requirements 3.1, 3.3, 3.5**

  - [ ]* 1.3 Write property test: Filler prompt format and context-awareness (Property 2)
    - **Property 2: Filler prompt format and context-awareness**
    - Use fast-check to generate all `(toolName, intent)` combinations, verify output starts with `[System:` and ends with `]`, is non-empty, `validate_user` always produces verification language, `forward_to_backend` references intent-specific language
    - **Validates: Requirements 1.2, 4.1, 4.2, 4.3, 4.5**

  - [ ]* 1.4 Write unit tests for helper functions
    - Test `classifyIntent("what's my bill")` → `billing`, `classifyIntent("is there an outage")` → `outage`, `classifyIntent("hello there")` → `general`
    - Test `buildFillerPrompt('validate_user', 'billing')` contains verification language
    - Test `buildFillerPrompt('forward_to_backend', 'billing')` contains billing language
    - Test `buildFollowUpPrompt()` returns `[System: ...]` formatted string
    - _Requirements: 3.1, 3.2, 3.3, 4.2, 4.3, 2.3_

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Integrate filler orchestrator into VoiceInterface.jsx
  - [x] 3.1 Add filler refs and import helpers into `VoiceInterface.jsx`
    - Import `classifyIntent`, `buildFillerPrompt`, `buildFollowUpPrompt` from `voiceFillerHelpers.js`
    - Add new refs: `intentRef` (default `'general'`), `isFillerPhaseRef` (default `false`), `toolCallPendingRef` (default `false`), `followUpCountRef` (default `0`)
    - Define `MAX_FOLLOW_UPS = 2` constant
    - _Requirements: 2.1, 2.4, 3.4, 5.1_

  - [x] 3.2 Update transcript handler to classify intent
    - In the `conversation.item.input_audio_transcription.completed` case, call `classifyIntent(data.transcript)` and store result in `intentRef.current`
    - _Requirements: 3.1, 3.4_

  - [x] 3.3 Rewrite `response.function_call_arguments.done` handler for parallel filler + tool call
    - Set `toolCallPendingRef.current = true`, `isFillerPhaseRef.current = true`, `followUpCountRef.current = 0`
    - Inject filler prompt via `conversation.item.create` + `response.create` using `buildFillerPrompt(toolName, intentRef.current)`
    - Run `handleToolCall` in parallel (do not await before injecting filler)
    - When tool result resolves: set `toolCallPendingRef.current = false`, `isFillerPhaseRef.current = false`, send `function_call_output` + `response.create`, reset `isProcessingToolRef`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.2, 5.5_

  - [x] 3.4 Update `response.done` handler for follow-up filler logic
    - When `response.done` fires and `isFillerPhaseRef.current === true` and `toolCallPendingRef.current === true` and `followUpCountRef.current < MAX_FOLLOW_UPS`: inject follow-up prompt via `buildFollowUpPrompt()`, increment `followUpCountRef`, send `conversation.item.create` + `response.create`
    - When `isFillerPhaseRef.current === false`, handle normally (existing behavior)
    - Do NOT send follow-up prompts after tool result has been delivered
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 5.1, 5.3_

  - [ ]* 3.5 Write property test: Follow-up count cap and post-result silence (Property 3)
    - **Property 3: Follow-up count cap and post-result silence**
    - Use fast-check to generate random sequences of `response.done` events (N from 0 to 10), simulate filler orchestrator logic, verify follow-up count ≤ 2. Simulate tool result delivery and verify no further follow-ups
    - **Validates: Requirements 2.4, 5.3**

- [x] 4. Remove hold music usage from VoiceInterface.jsx
  - [x] 4.1 Remove `useHoldMusic` import and all `startMusic`/`stopMusic` calls
    - Remove `import useHoldMusic from './useHoldMusic'` line
    - Remove `const { startMusic, stopMusic } = useHoldMusic(0.12)` line
    - Remove `stopMusic()` call in `response.audio_transcript.delta` handler
    - Remove `stopMusic()` call in `disconnect` function
    - Remove `stopMusic` from `disconnect` useCallback dependency array
    - Retain `useHoldMusic.js` file in the codebase (do not delete)
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 4.2 Reset filler state on disconnect
    - In the `disconnect` function, reset `isFillerPhaseRef.current = false`, `toolCallPendingRef.current = false`, `followUpCountRef.current = 0`
    - _Requirements: 5.5, 6.3_

  - [ ]* 4.3 Write unit tests for hold music removal and filler state reset
    - Verify `useHoldMusic` is not imported in `VoiceInterface.jsx`
    - Verify no `startMusic`/`stopMusic` calls exist in `VoiceInterface.jsx`
    - Verify `useHoldMusic.js` file still exists in the codebase
    - Verify all filler state resets on disconnect
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design using fast-check
- All changes are frontend-only — no Interceptor or Backend modifications needed
- `useHoldMusic.js` is retained but disconnected for future cleanup
