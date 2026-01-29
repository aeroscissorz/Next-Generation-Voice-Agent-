import { useState, useRef } from 'react'
import { processMessage } from '../services/interceptor'
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

    const mediaRecorderRef = useRef(null)
    const audioChunksRef = useRef([])

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

            // Process through interceptor
            const result = await processMessage(
                channel,
                { audioBlob },
                userId,
                {
                    onTranscript: (text) => {
                        setTranscript(text)
                        setStatus('Transcribed: ' + text)
                    },
                    onFiller: (text) => {
                        setStatus(text)
                    },
                    onResponse: (text) => {
                        setStatus('Playing response...')
                        setAgentState('talking')
                        onResponse && onResponse(text)
                    },
                    onAnalyzing: (analyzing) => {
                        if (analyzing) {
                            setStatus('Analyzing...')
                            setAgentState('thinking')
                        }
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
        <div className="flex flex-col items-center justify-center gap-6 p-6 min-h-[350px]">
            {/* Animated Orb */}
            <div
                className="w-25 h-25 cursor-pointer transition-transform hover:scale-105"
                onClick={isRecording ? stopRecording : startRecording}
            >
                <Orb
                    agentState={agentState}
                    colors={channel === 'telephonic' ? ['#60A5FA', '#3B82F6'] : ['#A78BFA', '#8B5CF6']}
                    className="w-full h-full"
                />
            </div>

            {/* Status Text */}
            {status && (
                <div className="text-center">
                    <p className={`text-sm ${status.includes('Error') ? 'text-red-400' : 'text-purple-400'
                        } animate-pulse`}>
                        {status}
                    </p>
                </div>
            )}

            {/* Transcript */}
            {transcript && (
                <div className="max-w-md p-4 bg-white/5 rounded-lg border border-white/10">
                    <p className="text-xs text-gray-400 mb-1">You said:</p>
                    <p className="text-sm text-white">{transcript}</p>
                </div>
            )}

            {/* Instructions */}
            {!isRecording && !isProcessing && (
                <p className="text-xs text-gray-500 text-center max-w-xs">
                    {channel === 'telephonic'
                        ? 'Click the orb to start telephonic call (formal tone)'
                        : 'Click the orb to start voice conversation'}
                </p>
            )}
        </div>
    )
}

export default VoiceInterface
