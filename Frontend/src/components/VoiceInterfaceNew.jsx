import { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, PhoneOff, Volume2, VolumeX } from 'lucide-react';
import { Orb } from './ui/orb';
import voiceService from '../services/voiceService';

function VoiceInterfaceNew({ userId, userName, onClose }) {
    const [isConnected, setIsConnected] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [agentState, setAgentState] = useState(null); // null, 'listening', 'talking', 'thinking'
    const [error, setError] = useState(null);
    const [statusMessage, setStatusMessage] = useState('Initializing...');
    const orbColorsRef = useRef(["#FF6B6B", "#4ECDC4"]);

    useEffect(() => {
        // Initialize voice service
        const initVoice = async () => {
            try {
                setStatusMessage('Connecting to voice service...');

                // Get interceptor URL from env
                const interceptorUrl = import.meta.env.VITE_INTERCEPTOR_URL || 'ws://localhost:8001';

                // Connect to voice WebSocket
                await voiceService.connect(userId, userName, interceptorUrl);

                setIsConnected(true);
                setStatusMessage('Connected! Start speaking...');

                // Set up state change callback
                voiceService.onStateChange((state) => {
                    setAgentState(state);

                    // Update status message based on state
                    switch (state) {
                        case 'listening':
                            setStatusMessage('Listening...');
                            break;
                        case 'thinking':
                            setStatusMessage('Processing...');
                            break;
                        case 'talking':
                            setStatusMessage('Speaking...');
                            break;
                        default:
                            setStatusMessage('Ready');
                    }
                });

                // Set up error callback
                voiceService.onError((errorMsg) => {
                    setError(errorMsg);
                    setStatusMessage(`Error: ${errorMsg}`);
                });

                // Start listening
                const started = voiceService.startListening();
                if (started) {
                    setIsListening(true);
                } else {
                    setError('Failed to start speech recognition');
                    setStatusMessage('Speech recognition not available');
                }

            } catch (err) {
                console.error('Failed to initialize voice:', err);
                setError('Failed to connect to voice service');
                setStatusMessage('Connection failed. Please try again.');
            }
        };

        initVoice();

        // Cleanup on unmount
        return () => {
            voiceService.endConversation();
        };
    }, [userId, userName]);

    const toggleMute = () => {
        if (isMuted) {
            voiceService.startListening();
            setIsListening(true);
            setIsMuted(false);
        } else {
            voiceService.stopListening();
            setIsListening(false);
            setIsMuted(true);
        }
    };

    const handleInterrupt = () => {
        voiceService.interrupt();
    };

    const handleEndCall = () => {
        voiceService.endConversation();
        if (onClose) {
            onClose();
        }
    };

    return (
        <div className="flex flex-col items-center justify-center h-full w-full">
            {/* Orb Container */}
            <div className="relative w-64 h-64 mb-8">
                <Orb
                    colorsRef={orbColorsRef}
                    agentState={agentState}
                    className="w-full h-full"
                />

                {/* Status Indicator */}
                <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 w-full text-center">
                    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${error
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : isConnected
                                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                        }`}>
                        {isConnected && !error && (
                            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                        )}
                        <span>{statusMessage}</span>
                    </div>
                </div>
            </div>

            {/* User Info */}
            <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-white mb-2">Voice Conversation</h2>
                <p className="text-gray-400">Speaking with AI Assistant</p>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-4">
                {/* Mute/Unmute Button */}
                <button
                    onClick={toggleMute}
                    disabled={!isConnected}
                    className={`p-4 rounded-full transition-all ${isMuted
                            ? 'bg-red-500/20 border-2 border-red-500 text-red-400 hover:bg-red-500/30'
                            : 'bg-green-500/20 border-2 border-green-500 text-green-400 hover:bg-green-500/30'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                    title={isMuted ? 'Unmute' : 'Mute'}
                >
                    {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                </button>

                {/* Interrupt Button */}
                <button
                    onClick={handleInterrupt}
                    disabled={!isConnected || agentState !== 'talking'}
                    className="p-4 rounded-full bg-yellow-500/20 border-2 border-yellow-500 text-yellow-400 hover:bg-yellow-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Interrupt"
                >
                    <VolumeX size={24} />
                </button>

                {/* End Call Button */}
                <button
                    onClick={handleEndCall}
                    className="p-4 rounded-full bg-red-500/20 border-2 border-red-500 text-red-400 hover:bg-red-500/30 transition-all"
                    title="End Call"
                >
                    <PhoneOff size={24} />
                </button>
            </div>

            {/* State Indicators */}
            <div className="mt-8 flex items-center gap-6 text-sm">
                <div className={`flex items-center gap-2 ${isListening ? 'text-green-400' : 'text-gray-500'}`}>
                    <Mic size={16} />
                    <span>{isListening ? 'Listening' : 'Not listening'}</span>
                </div>
                <div className={`flex items-center gap-2 ${agentState === 'talking' ? 'text-blue-400' : 'text-gray-500'}`}>
                    <Volume2 size={16} />
                    <span>{agentState === 'talking' ? 'Agent speaking' : 'Agent silent'}</span>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm max-w-md text-center">
                    {error}
                </div>
            )}

            {/* Browser Compatibility Notice */}
            {!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window) && (
                <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm max-w-md text-center">
                    ⚠️ Speech recognition is not supported in this browser. Please use Chrome or Edge.
                </div>
            )}
        </div>
    );
}

export default VoiceInterfaceNew;
