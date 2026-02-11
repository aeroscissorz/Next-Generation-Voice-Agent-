import { useState, useRef, useEffect, useCallback } from 'react'
import { Mic, MicOff, PhoneOff } from 'lucide-react'
import { Orb } from './ui/orb'
import useHoldMusic from './useHoldMusic'

const INTERCEPTOR_URL =
    import.meta.env.VITE_INTERCEPTOR_URL ||
    import.meta.env.VITE_BACKEND_URL ||
    'http://localhost:8001'

/**
 * Voice Interface Component
 * Connects to OpenAI Realtime API via WebRTC, routes tool calls through
 * the Interceptor layer.
 */
function VoiceInterface({ channel, userId, onResponse }) {
    const [status, setStatus] = useState('disconnected') // disconnected | connecting | connected | listening | processing | speaking | error
    const [transcript, setTranscript] = useState('')
    const [assistantText, setAssistantText] = useState('')
    const [error, setError] = useState(null)
    const [isMicOn, setIsMicOn] = useState(false)
    const [debugEvents, setDebugEvents] = useState([])

    // Hold music — plays during tool call processing
    const { startMusic, stopMusic } = useHoldMusic(0.12)

    const pcRef = useRef(null)
    const dcRef = useRef(null)
    const audioElRef = useRef(null)
    const streamRef = useRef(null)
    const connectedRef = useRef(false)
    const silenceTimerRef = useRef(null)
    const nudgeCountRef = useRef(0)

    const SILENCE_TIMEOUT_MS = 20000 // 20 seconds of silence before nudge
    const MAX_NUDGES = 2 // Max nudges before staying quiet

    // Orb color based on status
    const orbColorsRef = useRef(["#6B7280", "#9CA3AF"]) // default gray
    useEffect(() => {
        switch (status) {
            case 'listening':
                orbColorsRef.current = ["#22C55E", "#16A34A"] // green
                break
            case 'processing':
                orbColorsRef.current = ["#F59E0B", "#D97706"] // amber
                break
            case 'speaking':
                orbColorsRef.current = ["#A855F7", "#7C3AED"] // purple
                break
            case 'connected':
                orbColorsRef.current = ["#3B82F6", "#2563EB"] // blue
                break
            case 'error':
                orbColorsRef.current = ["#EF4444", "#DC2626"] // red
                break
            default:
                orbColorsRef.current = ["#6B7280", "#9CA3AF"] // gray
        }
    }, [status])

    /**
     * Add event to debug log
     */
    const logEvent = useCallback((type, data = {}) => {
        const time = new Date().toLocaleTimeString().split(' ')[0]
        setDebugEvents(prev => [{ time, type, data }, ...prev].slice(0, 50))
    }, [])

    /**
     * Reset the silence timer. Called whenever there's activity.
     */
    const resetSilenceTimer = useCallback(() => {
        if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current)
            silenceTimerRef.current = null
        }
    }, [])

    /**
     * Start the silence timer. After SILENCE_TIMEOUT_MS, send a nudge.
     */
    const startSilenceTimer = useCallback(() => {
        resetSilenceTimer()

        // Only nudge if connected and haven't exceeded max nudges
        if (!connectedRef.current || nudgeCountRef.current >= MAX_NUDGES) return

        silenceTimerRef.current = setTimeout(() => {
            const dc = dcRef.current
            if (dc && dc.readyState === 'open' && nudgeCountRef.current < MAX_NUDGES) {
                nudgeCountRef.current += 1
                logEvent(`Silence nudge #${nudgeCountRef.current}`)

                // Send a subtle nudge as a user message the model will respond to
                dc.send(JSON.stringify({
                    type: 'conversation.item.create',
                    item: {
                        type: 'message',
                        role: 'user',
                        content: [{
                            type: 'input_text',
                            text: '[System: The user has been silent for a while. Gently check in with a brief, warm phrase. Do not repeat previous check-ins.]'
                        }]
                    }
                }))

                dc.send(JSON.stringify({ type: 'response.create' }))
            }
        }, SILENCE_TIMEOUT_MS)
    }, [resetSilenceTimer, logEvent])

    /**
     * Forward a tool call to the interceptor and return the result.
     */
    const handleToolCall = useCallback(async (callId, toolName, argsJson) => {
        setStatus('processing')
        logEvent(`Tool Call: ${toolName}`)
        try {
            const args = JSON.parse(argsJson)
            const response = await fetch(`${INTERCEPTOR_URL}/voice/tool-call`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tool_name: toolName,
                    arguments: args,
                    user_id: userId,
                    call_id: callId,
                }),
            })

            if (!response.ok) {
                throw new Error(`Tool call failed: ${response.status}`)
            }

            const data = await response.json()
            return data.result || JSON.stringify({ error: 'No result' })
        } catch (err) {
            console.error('Tool call error:', err)
            logEvent(`Tool Error: ${err.message}`)
            return JSON.stringify({ error: err.message })
        }
    }, [userId, logEvent])

    /**
     * Handle incoming data channel messages from OpenAI Realtime.
     */
    const handleRealtimeEvent = useCallback(async (event) => {
        const data = JSON.parse(event.data)
        // Log interesting events, skip high-frequency audio deltas to avoid spam
        if (data.type !== 'response.audio_transcript.delta' && data.type !== 'input_audio_buffer.append') {
            logEvent(data.type)
        }

        switch (data.type) {
            case 'session.created':
            case 'session.updated':
                console.log('Session event:', data.type, data.session)
                logEvent(data.type, data.session) // Log to debug box too
                break

            case 'input_audio_buffer.speech_started':
                setStatus('listening')
                resetSilenceTimer()
                nudgeCountRef.current = 0 // Reset nudge count on new speech
                break

            case 'input_audio_buffer.speech_stopped':
                setStatus('processing')
                resetSilenceTimer()
                break

            case 'conversation.item.input_audio_transcription.completed':
                if (data.transcript) {
                    setTranscript(data.transcript)
                    onResponse?.({ user: data.transcript, agent: '' })
                    logEvent('User Transcript', { text: data.transcript })
                }
                break

            case 'response.audio_transcript.delta':
            case 'response.text.delta':
                if (data.delta) {
                    stopMusic() // Agent is speaking — stop hold music
                    setAssistantText(prev => prev + data.delta)
                    setStatus('speaking')
                }
                break

            case 'response.audio_transcript.done':
            case 'response.text.done':
                const textContent = data.transcript || data.text
                if (textContent) {
                    setAssistantText(textContent)
                    onResponse?.({ user: transcript, agent: textContent })
                    logEvent('Agent Transcript', { text: textContent })
                }
                break

            case 'response.function_call_arguments.done': {
                const callId = data.call_id
                const toolName = data.name
                const argsJson = data.arguments

                console.log(`Tool call: ${toolName}`, argsJson)

                // Start hold music while we wait for the backend
                startMusic()

                // Forward to interceptor
                const result = await handleToolCall(callId, toolName, argsJson)

                // Stop hold music — we have the result
                stopMusic()

                // Send tool result back to OpenAI
                const dc = dcRef.current
                if (dc && dc.readyState === 'open') {
                    // Create the function call output
                    dc.send(JSON.stringify({
                        type: 'conversation.item.create',
                        item: {
                            type: 'function_call_output',
                            call_id: callId,
                            output: result,
                        }
                    }))

                    // Trigger the model to continue responding
                    dc.send(JSON.stringify({
                        type: 'response.create',
                    }))
                }
                break;
            }

            case 'response.done':
                console.log('Response done:', data.response)

                if (data.response?.status === 'failed') {
                    console.error('Response Failed Details:', JSON.stringify(data.response.status_details, null, 2))
                    logEvent('Response Failed', { details: data.response.status_details })
                } else {
                    logEvent('Response Done', { status: data.response?.status })
                }

                setStatus('listening')
                setAssistantText('')
                startSilenceTimer() // Start silence timer after agent finishes speaking
                break

            case 'error':
                console.error('Realtime error:', data.error)
                setError(data.error?.message || 'An error occurred')
                setStatus('error')
                break

            default:
                // Ignore other events
                break
        }
    }, [handleToolCall, onResponse, transcript, resetSilenceTimer, startSilenceTimer])

    /**
     * Connect to OpenAI Realtime via WebRTC.
     */
    const connect = useCallback(async () => {
        if (connectedRef.current) return

        setStatus('connecting')
        setError(null)

        try {
            // 1. Get ephemeral token from interceptor
            const tokenRes = await fetch(
                `${INTERCEPTOR_URL}/voice/token?user_id=${encodeURIComponent(userId)}`
            )
            if (!tokenRes.ok) {
                throw new Error(`Failed to get voice token: ${tokenRes.status}`)
            }
            const tokenData = await tokenRes.json()
            const ephemeralToken = tokenData.ephemeral_token

            // 2. Get microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            streamRef.current = stream

            // 3. Create RTCPeerConnection
            const pc = new RTCPeerConnection()
            pcRef.current = pc

            // 4. Use existing audio element from ref
            const audioEl = audioElRef.current
            if (!audioEl) {
                throw new Error('Audio element not found')
            }

            pc.ontrack = (e) => {
                console.log('Got remote audio track', e.streams[0])
                audioEl.srcObject = e.streams[0]
                audioEl.play().catch(err => {
                    console.warn('Audio autoplay blocked, will retry on next interaction:', err)
                })
            }

            // 5. Add microphone track
            stream.getTracks().forEach(track => {
                pc.addTrack(track, stream)
            })

            // 6. Create data channel for events
            const dc = pc.createDataChannel('oai-events')
            dcRef.current = dc

            dc.onopen = () => {
                console.log('Data channel open — session active')
                setStatus('listening')
                connectedRef.current = true
                setIsMicOn(true)

                // Force a greeting message by simulating a user saying "Hello"
                // This is more robust than just asking for a response
                const greetingItem = {
                    type: 'conversation.item.create',
                    item: {
                        type: 'message',
                        role: 'user',
                        content: [
                            { type: 'input_text', text: 'Hello! Please greet me and ask for my User ID.' }
                        ]
                    }
                }
                dc.send(JSON.stringify(greetingItem))

                // Trigger the model to respond to the greeting immediately
                dc.send(JSON.stringify({
                    type: 'response.create',
                }))
            }

            dc.onmessage = handleRealtimeEvent

            dc.onclose = () => {
                console.log('Data channel closed')
                if (connectedRef.current) {
                    disconnect()
                }
            }

            // 7. Create and set local SDP offer
            const offer = await pc.createOffer()
            await pc.setLocalDescription(offer)

            // 8. Send offer to OpenAI and get answer
            const sdpResponse = await fetch(
                `https://api.openai.com/v1/realtime?model=${tokenData.model}`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${ephemeralToken}`,
                        'Content-Type': 'application/sdp',
                    },
                    body: offer.sdp,
                }
            )

            if (!sdpResponse.ok) {
                throw new Error(`WebRTC SDP exchange failed: ${sdpResponse.status}`)
            }

            const answerSdp = await sdpResponse.text()
            await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })

            setStatus('listening')
        } catch (err) {
            console.error('Connection error:', err)
            setError(err.message)
            setStatus('error')
            disconnect()
        }
    }, [userId, handleRealtimeEvent])

    /**
     * Disconnect and clean up.
     */
    const disconnect = useCallback(() => {
        connectedRef.current = false
        setIsMicOn(false)
        setStatus('disconnected')
        resetSilenceTimer()
        stopMusic() // Ensure hold music stops on disconnect
        nudgeCountRef.current = 0

        if (dcRef.current) {
            dcRef.current.close()
            dcRef.current = null
        }

        if (pcRef.current) {
            pcRef.current.close()
            pcRef.current = null
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(t => t.stop())
            streamRef.current = null
        }

        if (audioElRef.current) {
            audioElRef.current.srcObject = null
            // Do NOT remove from DOM, it's rendered by React
        }
    }, [resetSilenceTimer, stopMusic])

    /**
     * Toggle the microphone on/off.
     */
    const toggleMic = useCallback(() => {
        if (!connectedRef.current) {
            connect()
            return
        }

        const stream = streamRef.current
        if (!stream) return

        const audioTrack = stream.getAudioTracks()[0]
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled
            setIsMicOn(audioTrack.enabled)
            setStatus(audioTrack.enabled ? 'listening' : 'connected')
        }
    }, [connect])

    // Cleanup on unmount
    useEffect(() => {
        return () => disconnect()
    }, [disconnect])

    const statusText = {
        disconnected: 'Click the mic to start',
        connecting: 'Connecting...',
        connected: 'Connected — ready',
        listening: 'Listening...',
        processing: 'Thinking...',
        speaking: 'Speaking...',
        error: error || 'Something went wrong',
    }

    return (
        <div className="flex flex-col items-center justify-center gap-8 p-6 min-h-[500px]">
            {/* Orb */}
            <div className="relative w-40 h-40">
                <Orb
                    colorsRef={orbColorsRef}
                    agentState={status === 'speaking' ? 'speaking' : status === 'listening' ? 'listening' : null}
                    className="w-full h-full"
                />
            </div>

            {/* Title */}
            <div className="text-center max-w-md">
                <h2 className="text-2xl font-semibold text-gray-200 mb-1">
                    {channel === 'telephonic' ? 'Phone Support' : 'Voice Assistant'}
                </h2>
                <p className={`text-sm ${status === 'error' ? 'text-red-400' : 'text-gray-400'}`}>
                    {statusText[status]}
                </p>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-4">
                {/* Mic Button */}
                <button
                    onClick={toggleMic}
                    disabled={status === 'connecting'}
                    className={`w-16 h-16 flex items-center justify-center rounded-full transition-all duration-300 shadow-lg
                        ${isMicOn
                            ? 'bg-gradient-to-br from-green-500 to-emerald-600 shadow-green-500/30 hover:shadow-green-500/50 hover:scale-105'
                            : 'bg-gradient-to-br from-gray-600 to-gray-700 shadow-gray-500/20 hover:shadow-gray-500/40 hover:scale-105'
                        }
                        ${status === 'connecting' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    `}
                    title={isMicOn ? 'Mute microphone' : 'Start voice session'}
                >
                    {status === 'connecting' ? (
                        <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : isMicOn ? (
                        <Mic size={28} className="text-white" />
                    ) : (
                        <MicOff size={28} className="text-white" />
                    )}
                </button>

                {/* Disconnect Button (only when connected) */}
                {connectedRef.current && (
                    <button
                        onClick={disconnect}
                        className="w-14 h-14 flex items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/30 hover:shadow-red-500/50 hover:scale-105 transition-all duration-300"
                        title="End voice session"
                    >
                        <PhoneOff size={24} className="text-white" />
                    </button>
                )}
            </div>

            {/* Hidden Audio Element for WebRTC */}
            <audio ref={audioElRef} autoPlay style={{ display: 'none' }} />
        </div>
    )
}

export default VoiceInterface
