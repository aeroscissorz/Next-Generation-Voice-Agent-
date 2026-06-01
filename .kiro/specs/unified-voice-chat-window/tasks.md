# Implementation Tasks

## Tasks

- [x] 1. Refactor VoiceInterface into a headless logic component
  - [x] 1.1 Add `onStatusChange`, `onOrbColorsChange`, `onConnectedChange`, `onMicChange` props and call them whenever the corresponding state changes
  - [x] 1.2 Add `imperativeRef` prop and assign `{ connect, disconnect, toggleMic }` to it via `useImperativeHandle` or a `useEffect`
  - [x] 1.3 Remove the outer container div, Orb, title, status text, and control buttons from the render output — keep only the hidden `<audio>` element

- [x] 2. Add unified layout state to ChatSession
  - [x] 2.1 Replace the `mode` state with `activeInputMode` (`'chat' | 'voice'`), initialised from `location.state?.mode` (defaulting to `'chat'`)
  - [x] 2.2 Add `voiceStatus`, `voiceConnected`, `voiceMicOn` state variables and a `voiceOrbColorsRef` ref
  - [x] 2.3 Create the `voiceImperativeRef` ref that will be passed to VoiceInterface

- [x] 3. Build the Voice_Panel inside ChatSession
  - [x] 3.1 Render the `Orb` component using `voiceOrbColorsRef` and derive `agentState` from `voiceStatus`
  - [x] 3.2 Render the status label using a `statusText` map keyed on `voiceStatus`
  - [x] 3.3 Render the mic toggle button that calls `voiceImperativeRef.current.toggleMic()`
  - [x] 3.4 Conditionally render the disconnect button when `voiceConnected` is true, calling `voiceImperativeRef.current.disconnect()`
  - [x] 3.5 Display any voice error message within the Voice_Panel when `voiceStatus === 'error'`

- [x] 4. Build the Input_Toolbar with Mode_Toggle inside ChatSession
  - [x] 4.1 Render the existing textarea and send button only when `activeInputMode === 'chat'`
  - [x] 4.2 Render a mic toggle button as the primary control when `activeInputMode === 'voice'`
  - [x] 4.3 Add the Mode_Toggle control (chat / voice icon buttons) that updates `activeInputMode` without disconnecting the voice session
  - [x] 4.4 Ensure the Mode_Toggle visually highlights the currently active mode

- [x] 5. Wire up the unified layout structure in ChatSession
  - [x] 5.1 Make the Chat_Panel (`CustomScrollbar` + message list) always visible with `flex-1` so it fills available vertical space
  - [x] 5.2 Place the Voice_Panel below the Chat_Panel with a fixed height (~96px) and a top border separator
  - [x] 5.3 Place the Input_Toolbar at the bottom, always visible regardless of `activeInputMode`
  - [x] 5.4 Remove the old conditional rendering that swapped between full-screen voice and chat layouts
  - [x] 5.5 Pass the new callback props and `imperativeRef` to the `VoiceInterface` component instance

- [x] 6. Ensure shared conversation state works correctly
  - [x] 6.1 Verify the existing `onResponse` handler in ChatSession appends both user transcript and agent response to `responses` when both are present
  - [x] 6.2 Verify the handler appends only an agent message when `onResponse` is called with a plain string
  - [x] 6.3 Confirm the `chatEndRef` auto-scroll fires whenever `responses` updates, including voice-originated messages
