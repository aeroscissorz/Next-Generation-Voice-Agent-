# Design Document

## Overview

Refactor `ChatSession.jsx` to render a unified layout where the Chat_Panel and Voice_Panel coexist in the same viewport at all times. The current conditional rendering that swaps between a full-screen voice view and a chat view is replaced with a persistent split layout. `VoiceInterface.jsx` is refactored to expose its internals (orb, status, controls) as props so the parent can embed them inline rather than rendering the full self-contained component.

---

## Architecture

### Current Architecture

```
ChatSession
├── mode === 'chat'  → Chat transcript + text input
└── mode === 'voice' → VoiceInterface (full-screen, owns orb + controls)
```

### Target Architecture

```
ChatSession (unified layout)
├── Chat_Panel (always visible, flex-1, scrollable)
│   └── message list + ThinkingIndicator
├── Voice_Panel (always visible, fixed height strip)
│   └── Orb + status label + mic/disconnect buttons
└── Input_Toolbar (always visible, bottom)
    ├── mode === 'chat' → textarea + send button
    ├── mode === 'voice' → mic toggle button (primary)
    └── Mode_Toggle (always present)
```

---

## Component Design

### ChatSession.jsx changes

**Layout structure:**

```jsx
<div className="flex h-screen ...">
  <Aurora />
  <Sidebar />
  <main className="flex-1 flex flex-col">
    <nav>...</nav>                    {/* existing top bar */}
    <Chat_Panel />                    {/* flex-1, always visible */}
    <Voice_Panel />                   {/* fixed height, always visible */}
    <Input_Toolbar />                 {/* bottom bar with mode toggle */}
  </main>
</div>
```

**State additions:**

| State | Type | Purpose |
|---|---|---|
| `activeInputMode` | `'chat' \| 'voice'` | Which input is active in the toolbar |
| `voiceStatus` | string | Lifted from VoiceInterface via callback |
| `voiceOrbColorsRef` | ref | Lifted from VoiceInterface via callback |
| `voiceConnected` | boolean | Whether WebRTC session is active |
| `voiceMicOn` | boolean | Mic enabled state, lifted from VoiceInterface |

**Callbacks passed to VoiceInterface (new props):**

| Prop | Type | Purpose |
|---|---|---|
| `onStatusChange` | `(status: string) => void` | Lifts voice status up to parent |
| `onOrbColorsChange` | `(colors: string[]) => void` | Lifts orb colors up to parent |
| `onConnectedChange` | `(connected: boolean) => void` | Lifts connection state up |
| `onMicChange` | `(micOn: boolean) => void` | Lifts mic state up |
| `imperativeRef` | ref | Exposes `connect`, `disconnect`, `toggleMic` to parent |

**Initialization:** `activeInputMode` defaults to `'chat'`. The voice session is not auto-started; the user must click the mic button or toggle to voice mode.

---

### VoiceInterface.jsx changes

VoiceInterface becomes a **headless logic component** — it renders only the hidden `<audio>` element and exposes its state upward via callbacks and an imperative ref.

**New props:**

```js
{
  channel,          // existing
  userId,           // existing
  onResponse,       // existing
  onStatusChange,   // new — called whenever status changes
  onOrbColorsChange,// new — called whenever orb colors change
  onConnectedChange,// new — called whenever connectedRef changes
  onMicChange,      // new — called whenever isMicOn changes
  imperativeRef,    // new — ref assigned { connect, disconnect, toggleMic }
}
```

**Removed from VoiceInterface render output:**
- The outer `<div>` container
- The `<Orb>` component
- The title / status text
- The mic and disconnect buttons

**Kept in VoiceInterface render output:**
- `<audio ref={audioElRef} autoPlay style={{ display: 'none' }} />`

All logic (WebRTC, tool calls, silence timer, event handling) stays in VoiceInterface unchanged.

---

### Voice_Panel (inline in ChatSession)

Rendered directly in ChatSession using state lifted from VoiceInterface:

```jsx
<div className="flex items-center justify-center gap-6 py-4 border-t border-white/10">
  <div className="w-16 h-16">
    <Orb colorsRef={voiceOrbColorsRef} agentState={...} />
  </div>
  <p className="text-sm text-gray-400">{statusText[voiceStatus]}</p>
  {/* mic + disconnect buttons rendered here using imperativeRef */}
</div>
```

Height: fixed at ~96px so it never pushes the chat panel off screen.

---

### Input_Toolbar (inline in ChatSession)

```jsx
<div className="px-6 pb-4">
  <div className="max-w-4xl mx-auto bg-white/5 ... rounded-2xl p-4">
    {activeInputMode === 'chat' && <textarea ... />}
    {activeInputMode === 'voice' && <MicButton ... />}
    <ModeToggle activeMode={activeInputMode} onToggle={setActiveInputMode} />
    {activeInputMode === 'chat' && <SendButton ... />}
  </div>
</div>
```

**Mode_Toggle:** A pair of icon buttons (MessageSquare / Mic) that highlight the active mode. Switching mode does NOT disconnect the voice session.

---

## Data Flow

```
VoiceInterface (logic only)
  │  onStatusChange(status)
  │  onOrbColorsChange(colors)
  │  onConnectedChange(bool)
  │  onMicChange(bool)
  ▼
ChatSession state
  │  voiceStatus, voiceOrbColorsRef, voiceConnected, voiceMicOn
  ▼
Voice_Panel (renders Orb + status + controls)
Input_Toolbar (renders mode-appropriate input + Mode_Toggle)
```

`onResponse` callback path is unchanged — voice transcripts still flow into the shared `responses` array.

---

## Key Design Decisions

1. **Lift state, don't duplicate logic** — All WebRTC/audio logic stays in VoiceInterface. Only presentation state is lifted.
2. **imperativeRef for controls** — Parent calls `imperativeRef.current.toggleMic()` and `imperativeRef.current.disconnect()` so button handlers live in ChatSession without duplicating logic.
3. **Voice_Panel always rendered** — Even when `voiceStatus === 'disconnected'`, the panel shows the orb in its idle state and a "Click mic to start" label. This satisfies the requirement that both panels are always visible.
4. **No route changes** — The unified layout lives entirely within the existing `/dashboard/:sessionId` route and `ChatSession.jsx`.
5. **Backward compatibility** — The `mode` prop from `location.state` is repurposed to set the initial `activeInputMode` so existing navigation from Dashboard still works.
