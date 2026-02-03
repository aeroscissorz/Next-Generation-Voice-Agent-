import { useRef, useEffect } from 'react'

/**
 * Voice Interface Component
 * Handles voice and telephonic channel interactions with ElevenLabs widget
 */
function VoiceInterface({ channel }) {
    const widgetContainerRef = useRef(null)

    // Initialize ElevenLabs widget when component mounts
    useEffect(() => {
        // Create and append the widget element
        const widgetElement = document.createElement('elevenlabs-convai')

        // Use different agent IDs based on channel
        const agentId = channel === 'telephonic'
            ? 'agent_3501kgf1jzb1fg2936y8e2fy4j2s'  // Telephonic agent
            : 'agent_2501kgfq7nnvffgbd2yhwy9egb2a'  // Voice agent

        widgetElement.setAttribute('agent-id', agentId)

        // Optional: Customize widget appearance based on channel
        // if (channel === 'telephonic') {
        //     widgetElement.setAttribute('avatar-orb-color-1', '#60A5FA')
        //     widgetElement.setAttribute('avatar-orb-color-2', '#3B82F6')
        // } else {
        //     widgetElement.setAttribute('avatar-orb-color-1', '#A78BFA')
        //     widgetElement.setAttribute('avatar-orb-color-2', '#8B5CF6')
        // }

        if (widgetContainerRef.current) {
            widgetContainerRef.current.appendChild(widgetElement)
        }

        // Cleanup: remove widget when component unmounts
        return () => {
            if (widgetElement && widgetElement.parentNode) {
                widgetElement.parentNode.removeChild(widgetElement)
            }
        }
    }, [channel])

    return (
        <div className="flex flex-col items-center justify-center gap-6 p-6 min-h-[500px]">
            {/* ElevenLabs Widget Container */}
            <div ref={widgetContainerRef}></div>

            {/* Instructions */}
            <div className="text-center max-w-md">
                <h2 className="text-2xl font-semibold text-gray-200 mb-2">
                    {channel === 'telephonic' ? 'Phone Support' : 'Voice Assistant'}
                </h2>
                <p className="text-sm text-gray-400">
                    Click the widget button to start a voice conversation
                </p>
            </div>
        </div>
    )
}

export default VoiceInterface
