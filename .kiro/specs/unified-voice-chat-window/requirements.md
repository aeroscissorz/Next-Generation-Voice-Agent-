# Requirements Document

## Introduction

Currently, the Frontend presents voice and chat as separate interaction modes that render in entirely different UI layouts within the same `ChatSession` page — chat shows a scrollable message thread with a text input, while voice takes over the full screen with just the orb and mic controls. The user wants a single unified window where both voice and chat coexist simultaneously: the chat transcript is always visible, the voice orb and controls are always accessible, and switching between input modes feels seamless rather than like navigating between two different views.

## Glossary

- **Unified_Window**: The single `ChatSession` page layout that displays both the chat transcript panel and the voice control panel at the same time.
- **Chat_Panel**: The scrollable message transcript area showing the conversation history between the user and the AI assistant.
- **Voice_Panel**: The section of the Unified_Window containing the orb visualizer, voice status indicator, and microphone/disconnect controls.
- **Input_Toolbar**: The bottom bar of the Unified_Window that contains the text input field, send button, and a mode toggle to switch the active input method.
- **Active_Input_Mode**: The currently selected input method — either `chat` (text) or `voice` — that determines which input control is active in the Input_Toolbar.
- **VoiceInterface**: The existing `VoiceInterface.jsx` component responsible for WebRTC connection, microphone management, and real-time voice event handling.
- **ChatSession**: The existing `ChatSession.jsx` page component that owns conversation state and renders the session UI.
- **Orb**: The animated visual indicator (`Orb` component) that reflects the current voice agent state (listening, speaking, processing, etc.).
- **Mode_Toggle**: A UI control within the Input_Toolbar that allows the user to switch the Active_Input_Mode between `chat` and `voice`.

---

## Requirements

### Requirement 1: Unified Layout

**User Story:** As a user, I want to see the chat transcript and voice controls in the same window, so that I do not have to choose between a chat view and a voice view — both are always present.

#### Acceptance Criteria

1. THE Unified_Window SHALL display the Chat_Panel and the Voice_Panel simultaneously within a single viewport without requiring navigation or page transitions.
2. THE Chat_Panel SHALL occupy the primary vertical space of the Unified_Window and remain visible regardless of the Active_Input_Mode.
3. THE Voice_Panel SHALL be persistently visible within the Unified_Window and SHALL NOT replace or hide the Chat_Panel.
4. WHEN the user navigates to `/dashboard/:sessionId`, THE Unified_Window SHALL render with both the Chat_Panel and Voice_Panel visible by default.

---

### Requirement 2: Voice Panel Integration

**User Story:** As a user, I want the voice orb and mic controls to be embedded in the unified window, so that I can see the voice agent's state while also reading the chat transcript.

#### Acceptance Criteria

1. THE Voice_Panel SHALL contain the Orb visualizer, a voice status text label, and the microphone toggle button.
2. WHEN the VoiceInterface status changes (e.g., `listening`, `speaking`, `processing`, `error`), THE Orb SHALL update its color and animation state to reflect the current status.
3. WHEN the VoiceInterface is connected and the user clicks the disconnect button, THE Voice_Panel SHALL display the disconnect button alongside the microphone toggle button.
4. THE Voice_Panel SHALL be sized to fit within the Unified_Window without requiring the user to scroll to access voice controls.
5. IF the VoiceInterface encounters a connection error, THEN THE Voice_Panel SHALL display the error message within the Voice_Panel without disrupting the Chat_Panel.

---

### Requirement 3: Chat Panel Always Visible

**User Story:** As a user, I want the conversation transcript to always be visible, so that I can read previous messages while using voice input.

#### Acceptance Criteria

1. THE Chat_Panel SHALL display all messages in the `responses` state array, including messages generated from voice interactions.
2. WHEN a voice interaction produces a user transcript or agent response, THE ChatSession SHALL append the transcript and response as messages to the Chat_Panel.
3. WHEN new messages are added to the Chat_Panel, THE Chat_Panel SHALL auto-scroll to the most recent message.
4. WHILE the VoiceInterface is in `speaking` or `processing` status, THE Chat_Panel SHALL remain scrollable and interactive.
5. THE Chat_Panel SHALL display the `ThinkingIndicator` component WHEN the chat Active_Input_Mode is loading and no streaming message is present.

---

### Requirement 4: Mode Toggle in Input Toolbar

**User Story:** As a user, I want a toggle in the input area to switch between typing and speaking, so that I can choose my preferred input method at any time without losing context.

#### Acceptance Criteria

1. THE Input_Toolbar SHALL contain a Mode_Toggle control that switches the Active_Input_Mode between `chat` and `voice`.
2. WHEN the Active_Input_Mode is `chat`, THE Input_Toolbar SHALL display the text input field and send button as the primary input controls.
3. WHEN the Active_Input_Mode is `voice`, THE Input_Toolbar SHALL display the microphone toggle button as the primary input control and SHALL hide the text input field.
4. WHEN the user activates the Mode_Toggle to switch to `voice`, THE ChatSession SHALL NOT disconnect or reset any existing VoiceInterface session.
5. WHEN the user activates the Mode_Toggle to switch to `chat`, THE ChatSession SHALL NOT disconnect or reset any existing VoiceInterface session.
6. THE Mode_Toggle SHALL visually indicate the currently active mode at all times.

---

### Requirement 5: Shared Conversation State

**User Story:** As a user, I want voice and chat messages to appear in the same transcript, so that the full conversation history is in one place regardless of which input mode I used.

#### Acceptance Criteria

1. THE ChatSession SHALL maintain a single `responses` state array that stores messages from both chat and voice interactions.
2. WHEN the VoiceInterface `onResponse` callback is invoked with a user transcript and agent response, THE ChatSession SHALL append both as separate entries to the `responses` array.
3. WHEN the VoiceInterface `onResponse` callback is invoked with only an agent response string, THE ChatSession SHALL append it as an agent message to the `responses` array.
4. THE Chat_Panel SHALL render all entries in the `responses` array using consistent message bubble styling for both chat-originated and voice-originated messages.

---

### Requirement 6: Responsive Layout Preservation

**User Story:** As a developer, I want the unified layout to work within the existing page structure, so that the Sidebar, top navigation bar, and Aurora background are preserved without modification.

#### Acceptance Criteria

1. THE Unified_Window SHALL preserve the existing `Sidebar` component, top navigation bar, and `Aurora` background without structural changes to those components.
2. THE Unified_Window SHALL use a layout that fills the available space between the Sidebar and the viewport edge.
3. WHEN the Sidebar is collapsed or expanded, THE Unified_Window SHALL adapt its width responsively using the existing flex layout.
4. THE Unified_Window SHALL NOT introduce horizontal scrollbars at standard desktop viewport widths (1280px and above).
