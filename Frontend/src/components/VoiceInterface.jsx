import { useState, useRef, useEffect } from 'react'
import { processMessage } from '../services/interceptor'
import { synthesizeAudio } from '../services/elevenlabsService'
import { Orb } from './ui/orb'

/**
 * Voice Interface Component
 * Handles voice and telephonic channel interactions with animated Orb
 */
function VoiceInterface({ channel, userId, onResponse }) {
    const [isRecording, setIsRecording] = useState(false)
    const [isProcessing, setIsProcessing] = useState(false)
    const [agentState, setAgentState] = useState(null) // null | 'listening' | 'thinking' | 'talking'
    const [status, setStatus] = useState('')
    const [transcript, setTranscript] = useState('')
    const [hasGreeted, setHasGreeted] = useState(false)

    const mediaRecorderRef = useRef(null)
    const audioChunksRef = useRef([])

    // Play initial greeting when component mounts
    useEffect(() => {
        let isMounted = true

        const playGreeting = async () => {
            if (hasGreeted || !isMounted) return

            // Set hasGreeted immediately to prevent double execution
            setHasGreeted(true)

            try {
                // Get user name from localStorage
                const user = JSON.parse(localStorage.getItem('user'))
                const userName = user?.name || user?.email?.split('@')[0] || 'there'

                // Create greeting based on channel
                const greeting = channel === 'telephonic'
                    ? `Hello ${userName}, thank you for calling. How may I assist you today?`
                    : `Hey ${userName}, how are you? I'm here to help!`

                setStatus('Agent greeting...')
                setAgentState('talking')

                // Synthesize greeting audio
                const style = channel === 'telephonic' ? 'formal' : 'conversational'
                const audioBlob = await synthesizeAudio(greeting, style)

                if (!isMounted) return

                // Play greeting
                const url = URL.createObjectURL(audioBlob)
                const audio = new Audio(url)

                audio.onended = () => {
                    URL.revokeObjectURL(url)
                    if (isMounted) {
                        setStatus('Click the orb to speak')
                        setAgentState(null)
                    }
                }

                audio.onerror = () => {
                    URL.revokeObjectURL(url)
                    if (isMounted) {
                        setStatus('Click the orb to speak')
                        setAgentState(null)
                    }
                }

                await audio.play()

                // Add greeting to chat history
                if (onResponse && isMounted) {
                    onResponse(greeting)
                }

            } catch (error) {
                console.error('Error playing greeting:', error)
                if (isMounted) {
                    setStatus('Click the orb to speak')
                    setAgentState(null)
                }
            }
        }

        playGreeting()

        return () => {
            isMounted = false
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []) // Empty dependency array - only run once on mount

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const mediaRecorder = new MediaRecorder(stream)

            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                audioChunksRef.current.push(event.data)
            }

            mediaRecorder.onstop = handleRecordingStop

            mediaRecorder.start()
            setIsRecording(true)
            setAgentState('listening')
            setStatus('Listening...')

        } catch (error) {
            console.error('Error accessing microphone:', error)
            setStatus('Microphone access denied')
            setAgentState(null)
        }
    }

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop()
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
            setIsRecording(false)
            setAgentState('thinking')
            setStatus('Processing...')
        }
    }

    const handleRecordingStop = async () => {
        setIsProcessing(true)
        setAgentState('thinking')

        try {
            // Create audio blob from recorded chunks
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })

            let userTranscript = ''

            // Process through interceptor
            const result = await processMessage(
                channel,
                { audioBlob },
                userId,
                {
                    onTranscript: (text) => {
                        userTranscript = text
                        setTranscript(text)
                        setStatus('Transcribed: ' + text)
                    },
                    onResponse: (text) => {
                        setStatus('Playing response...')
                        setAgentState('talking')
                        // Send both user transcript and agent response
                        onResponse && onResponse({ user: userTranscript, agent: text })
                    }
                }
            )

            // Play response audio
            setAgentState('talking')
            const url = URL.createObjectURL(result.audio)
            const audio = new Audio(url)

            audio.onended = () => {
                URL.revokeObjectURL(url)
                setStatus('')
                setTranscript('')
                setAgentState(null)
            }

            audio.play()

        } catch (error) {
            console.error('Error processing voice:', error)
            setStatus('Error: ' + error.message)
            setAgentState(null)
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="flex flex-col items-center justify-center gap-6 p-6 min-h-[500px]">
            {/* Large Animated Orb - Centered */}
            <div
                className="w-96 h-96 cursor-pointer transition-transform hover:scale-105"
                onClick={isRecording ? stopRecording : startRecording}
            >
                <Orb
                    agentState={agentState}
                    colors={channel === 'telephonic' ? ['#60A5FA', '#3B82F6'] : ['#A78BFA', '#8B5CF6']}
                    className="w-full h-full"
                />
            </div>

            {/* Status Text - Below orb */}
            {status && (
                <div className="text-center">
                    <p className={`text-base ${status.includes('Error') ? 'text-red-400' : 'text-gray-300'
                        }`}>
                        {status}
                    </p>
                </div>
            )}

            {/* Instructions - Only when idle */}
            {!isRecording && !isProcessing && !agentState && (
                <p className="text-sm text-gray-500 text-center max-w-xs">
                    {channel === 'telephonic'
                        ? 'Click the orb to speak'
                        : 'Click the orb to start talking'}
                </p>
            )}
        </div>
    )
}

export default VoiceInterface
