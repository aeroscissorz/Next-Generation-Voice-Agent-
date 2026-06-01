import { useState, useRef, useEffect, useCallback } from 'react'
import { buildFillerPrompt, buildFollowUpPrompt } from './voiceFillerHelpers'

const INTERCEPTOR_URL =
    import.meta.env.VITE_INTERCEPTOR_URL ||
    import.meta.env.VITE_BACKEND_URL ||
    'http://localhost:8001'

/**
 * Voice Interface Component
 * Connects to OpenAI Realtime API via WebRTC, routes tool calls through
 * the Interceptor layer.
 */
function VoiceInterface({ channel, userId, onResponse, onStatusChange, onOrbColorsChange, onConnectedChange, onMicChange, imperativeRef }) {
    const [status, setStatus] = useState('disconnected') // disconnected | connecting | connected | listening | processing | speaking | error
    const [transcript, setTranscript] = useState('')
    const [assistantText, setAssistantText] = useState('')
    const [error, setError] = useState(null)
    const [isMicOn, setIsMicOn] = useState(false)
    const [debugEvents, setDebugEvents] = useState([])

    const pcRef = useRef(null)
    const dcRef = useRef(null)
    const audioElRef = useRef(null)
    const streamRef = useRef(null)
    const connectedRef = useRef(false)
    const silenceTimerRef = useRef(null)
    const nudgeCountRef = useRef(0)
    const isProcessingToolRef = useRef(false)  // Prevent duplicate tool responses
    const audioContextRef = useRef(null)  // For noise filtering
    const isFillerPhaseRef = useRef(false)        // True while filler is active
    const toolCallPendingRef = useRef(false)      // True while tool call HTTP request is in flight
    const followUpCountRef = useRef(0)            // Follow-up prompts sent for current tool call
    const fillerTimerRef = useRef(null)           // Single managed timer for filler scheduling
    const pendingToolNameRef = useRef(null)       // Tool name for building filler prompts
    const pendingToolResultRef = useRef(null)     // Queued tool result waiting for filler to finish

    const MAX_FOLLOW_UPS = 2
    const FILLER_INITIAL_DELAY = 3000   // 3s before first filler
    const FILLER_FOLLOWUP_DELAY = 8000  // 8s between follow-ups
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
        onOrbColorsChange?.(orbColorsRef.current)
    }, [status])

    // Lift status to parent
    useEffect(() => {
        onStatusChange?.(status)
    }, [status, onStatusChange])

    // Lift isMicOn to parent
    useEffect(() => {
        onMicChange?.(isMicOn)
    }, [isMicOn, onMicChange])

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
     * Clear any pending filler timer.
     */
    const clearFillerTimer = useCallback(() => {
        if (fillerTimerRef.current) {
            clearTimeout(fillerTimerRef.current)
            fillerTimerRef.current = null
        }
    }, [])

    /**
     * Send a filler/follow-up message via the data channel.
     */
    const sendFiller = useCallback((promptText) => {
        const dc = dcRef.current
        if (dc && dc.readyState === 'open') {
            dc.send(JSON.stringify({
                type: 'conversation.item.create',
                item: {
                    type: 'message',
                    role: 'user',
                    content: [{
                        type: 'input_text',
                        text: promptText
                    }]
                }
            }))
            dc.send(JSON.stringify({ type: 'response.create' }))
        }
    }, [])

    /**
     * Forward a tool call to the interceptor and return the result.
     */
    const handleToolCall = useCallback(async (callId, toolName, argsJson) => {
        setStatus('processing')
        logEvent(`Tool Call: ${toolName}`)
        try {
            let args
            try {
                args = JSON.parse(argsJson)
            } catch (parseErr) {
                // OpenAI sometimes sends filler text instead of JSON
                // Return error so the model retries with proper arguments
                console.warn(`Invalid tool args for ${toolName}:`, argsJson)
                return JSON.stringify({ error: `Invalid arguments. Please retry the tool call with proper JSON arguments.` })
            }
            
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
                // Prevent duplicate processing
                if (isProcessingToolRef.current) {
                    console.log('Already processing a tool call, skipping')
                    break
                }
                isProcessingToolRef.current = true

                const callId = data.call_id
                const toolName = data.name
                const argsJson = data.arguments

                console.log(`Tool call: ${toolName}`, argsJson)

                // Set filler state flags — timer starts when the agent's initial
                // narration finishes (response.done), not here
                toolCallPendingRef.current = true
                followUpCountRef.current = 0
                // Store toolName for filler prompt building later
                pendingToolNameRef.current = toolName

                // Run tool call in parallel
                handleToolCall(callId, toolName, argsJson).then((result) => {
                    // Tool result arrived — cancel any pending filler timer
                    clearFillerTimer()
                    toolCallPendingRef.current = false
                    pendingToolNameRef.current = null
                    isFillerPhaseRef.current = false

                    console.log(`Tool result arrived. Storing and attempting cancel.`)

                    // Store the result for response.done to drain
                    pendingToolResultRef.current = { callId, result }

                    const dc = dcRef.current
                    if (dc && dc.readyState === 'open') {
                        // Try to cancel any active response
                        dc.send(JSON.stringify({ type: 'response.cancel' }))

                        // Also set a fallback timer — if cancel fails (no active response)
                        // or response.done doesn't fire, send the result directly
                        setTimeout(() => {
                            if (!pendingToolResultRef.current) return // already drained
                            const pending = pendingToolResultRef.current
                            pendingToolResultRef.current = null
                            console.log('Fallback: sending tool result directly')

                            const dc2 = dcRef.current
                            if (dc2 && dc2.readyState === 'open') {
                                dc2.send(JSON.stringify({
                                    type: 'conversation.item.create',
                                    item: {
                                        type: 'function_call_output',
                                        call_id: pending.callId,
                                        output: pending.result,
                                    }
                                }))
                                dc2.send(JSON.stringify({ type: 'response.create' }))
                            }
                            isProcessingToolRef.current = false
                        }, 300)
                    }
                })

                break;
            }

            case 'response.done':
                console.log('Response done:', data.response?.status,
                    'isFillerPhase=', isFillerPhaseRef.current,
                    'toolCallPending=', toolCallPendingRef.current,
                    'pendingToolResult=', !!pendingToolResultRef.current)

                // --- Queued tool result: filler just finished, tool result waiting ---
                if (pendingToolResultRef.current) {
                    const { callId: queuedCallId, result: queuedResult } = pendingToolResultRef.current
                    pendingToolResultRef.current = null
                    isFillerPhaseRef.current = false
                    clearFillerTimer()
                    console.log('Draining queued tool result after filler finished')

                    const dc = dcRef.current
                    if (dc && dc.readyState === 'open') {
                        dc.send(JSON.stringify({
                            type: 'conversation.item.create',
                            item: {
                                type: 'function_call_output',
                                call_id: queuedCallId,
                                output: queuedResult,
                            }
                        }))
                        dc.send(JSON.stringify({ type: 'response.create' }))
                    }
                    isProcessingToolRef.current = false
                    break
                }

                // --- Filler follow-up logic ---
                if (isFillerPhaseRef.current && toolCallPendingRef.current) {
                    // Filler just finished speaking. Schedule next follow-up if allowed.
                    if (followUpCountRef.current < MAX_FOLLOW_UPS) {
                        clearFillerTimer()
                        fillerTimerRef.current = setTimeout(() => {
                            if (!isFillerPhaseRef.current || !toolCallPendingRef.current) return
                            sendFiller(buildFollowUpPrompt())
                            followUpCountRef.current += 1
                        }, FILLER_FOLLOWUP_DELAY)
                    }
                    // Stay in filler phase — don't reset status
                    break
                }

                // --- Agent's initial narration just finished, tool call still in flight ---
                // Start the filler timer now — first filler fires after FILLER_INITIAL_DELAY
                if (toolCallPendingRef.current && !isFillerPhaseRef.current) {
                    clearFillerTimer()
                    fillerTimerRef.current = setTimeout(() => {
                        if (!toolCallPendingRef.current) return
                        isFillerPhaseRef.current = true
                        sendFiller(buildFillerPrompt(pendingToolNameRef.current))
                    }, FILLER_INITIAL_DELAY)
                    break
                }

                // --- Normal response.done handling (includes tool result response) ---
                isProcessingToolRef.current = false  // Reset tool processing flag

                if (data.response?.status === 'failed') {
                    console.error('Response Failed Details:', JSON.stringify(data.response.status_details, null, 2))
                    logEvent('Response Failed', { details: data.response.status_details })
                    
                    // Retry on server errors - send a retry message
                    const errorType = data.response?.status_details?.error?.type
                    if (errorType === 'server_error') {
                        console.log('Server error detected, retrying...')
                        const dc = dcRef.current
                        if (dc && dc.readyState === 'open') {
                            // Small delay before retry
                            await new Promise(resolve => setTimeout(resolve, 500))
                            dc.send(JSON.stringify({
                                type: 'response.create',
                            }))
                        }
                    }
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

            // 2. Get microphone access with optimized audio settings
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 24000,  // OpenAI Realtime uses 24kHz
                    channelCount: 1
                } 
            })
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

            // 5. Add microphone track directly (browser handles echo/noise cancellation natively)
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
                onConnectedChange?.(true)
                setIsMicOn(true)

                // Force a greeting message by simulating a user saying "Hello"
                // This is more robust than just asking for a response
                const greetingItem = {
                    type: 'conversation.item.create',
                    item: {
                        type: 'message',
                        role: 'user',
                        content: [
                            { type: 'input_text', text: '[System: The call just connected. Say "Hi, this is Jessica from Verizon support", greet the caller warmly as a person, then ask for their User ID.]' }
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
        onConnectedChange?.(false)
        setIsMicOn(false)
        setStatus('disconnected')
        resetSilenceTimer()
        clearFillerTimer()
        nudgeCountRef.current = 0
        isFillerPhaseRef.current = false
        toolCallPendingRef.current = false
        followUpCountRef.current = 0
        pendingToolNameRef.current = null
        pendingToolResultRef.current = null

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
        
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => {})
            audioContextRef.current = null
        }

        if (audioElRef.current) {
            audioElRef.current.pause()
            audioElRef.current.srcObject = null
        }
    }, [resetSilenceTimer, clearFillerTimer])

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

    // Expose imperative API to parent
    useEffect(() => {
        if (imperativeRef) {
            imperativeRef.current = { connect, disconnect, toggleMic }
        }
    }, [imperativeRef, connect, disconnect, toggleMic])

    // Cleanup on unmount
    useEffect(() => {
        return () => disconnect()
    }, [disconnect])

    return <audio ref={audioElRef} autoPlay playsInline style={{ display: 'none' }} />
}

export default VoiceInterface
