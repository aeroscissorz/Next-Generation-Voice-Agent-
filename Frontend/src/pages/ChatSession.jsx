import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Settings as SettingsIcon, Send, Download, LogOut, MessageSquarePlus, Mic, MicOff, PhoneOff } from 'lucide-react'
import Aurora from '../components/Aurora'
import { Orb } from '../components/ui/orb'
import CustomScrollbar from '../components/CustomScrollbar'
import Sidebar from '../components/Sidebar'
import VoiceInterface from '../components/VoiceInterface'
import MessageContent from '../components/MessageContent'
import { processMessageStream } from '../services/interceptor'
import { createNewSession } from '../api/chatApi'

// Task 2: voiceStatusText map (used in Voice_Panel)
const voiceStatusText = {
  disconnected: 'Click mic to start',
  connecting: 'Connecting...',
  connected: 'Connected — ready',
  listening: 'Listening...',
  processing: 'Thinking...',
  speaking: 'Speaking...',
  error: 'Something went wrong',
}

function ThinkingIndicator({ liveStatus }) {
    const phrases = [
        "Thinking...",
        "On it...",
        "Just a moment...",
        "Working on it...",
    ]
    const [idx, setIdx] = useState(0)
    const [visible, setVisible] = useState(true)
    const [show, setShow] = useState(false)

    // Only appear after 2s — avoids flash for fast responses
    useEffect(() => {
        const delay = setTimeout(() => setShow(true), 2000)
        return () => clearTimeout(delay)
    }, [])

    useEffect(() => {
        if (liveStatus) return
        const cycle = setInterval(() => {
            setVisible(false)
            setTimeout(() => {
                setIdx(i => (i + 1) % phrases.length)
                setVisible(true)
            }, 300)
        }, 2000)
        return () => clearInterval(cycle)
    }, [liveStatus])

    const text = liveStatus || phrases[idx]

    return (
        <div className="flex justify-start">
            <div className="max-w-[70%] px-4 py-3 rounded-2xl text-sm bg-white/10 text-white rounded-bl-none">
                <div className="flex items-center gap-2 text-gray-400">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    {show && (
                        <span
                            className="text-xs ml-1 transition-opacity duration-300"
                            style={{ opacity: liveStatus ? 1 : visible ? 1 : 0 }}
                        >
                            {text}
                        </span>
                    )}
                </div>
            </div>
        </div>
    )
}

function ChatSession() {
    const navigate = useNavigate()
    const location = useLocation()
    const [message, setMessage] = useState('')
    const [responses, setResponses] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [statusMsg, setStatusMsg] = useState('')
    const chatEndRef = useRef(null)

    // Task 2: Unified layout state
    const [voiceStatus, setVoiceStatus] = useState('disconnected')
    const [voiceConnected, setVoiceConnected] = useState(false)
    const [voiceMicOn, setVoiceMicOn] = useState(false)
    const voiceOrbColorsRef = useRef(["#6B7280", "#9CA3AF"])
    const voiceImperativeRef = useRef(null)

    useEffect(() => {
        const userData = localStorage.getItem('user')
        if (!userData) {
            navigate('/login')
            return
        }

        const user = JSON.parse(userData)
        const name = user.name || user.email?.split('@')[0] || 'there'

        const initialMessage = location.state?.initialMessage
        const initialResponse = location.state?.initialResponse

        if (initialMessage && initialResponse) {
            setResponses([
                { role: "user", text: initialMessage },
                { role: "agent", text: initialResponse }
            ])
        } else {
            setResponses([
                { role: "agent", text: `Hi ${name}! I'm your NextGen support assistant. How can I help you today?` }
            ])
        }
    }, [navigate, location.state])

    // Task 6: Auto-scroll fires whenever responses updates (including voice-originated)
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [responses])

    const handleLogout = () => {
        localStorage.removeItem('user')
        navigate('/')
    }

    const handleNewConversation = async () => {
        const user = JSON.parse(localStorage.getItem("user"))
        const name = user.name || user.email?.split('@')[0] || 'there'

        try {
            setIsLoading(true)
            await createNewSession(
                user.user_id,
                user.name || user.email.split('@')[0]
            )
            setResponses([])
            setMessage('')
            setResponses([
                { role: "agent", text: `Hi ${name}! Starting fresh — what can I help you with?` }
            ])
        } catch (error) {
            console.error("Error creating new session:", error)
            setResponses([
                { role: "agent", text: "Sorry, there was an error starting a new conversation. Please try again." }
            ])
        } finally {
            setIsLoading(false)
        }
    }

    const sendMessage = async () => {
        if (!message.trim() || isLoading) return

        const user = JSON.parse(localStorage.getItem("user"))

        try {
            setResponses(prev => [...prev, { role: "user", text: message }])
            const currentMessage = message
            setMessage("")
            setIsLoading(true)
            setStatusMsg('')

            await processMessageStream(
                'chat',
                { text: currentMessage },
                user.user_id,
                (text) => {
                    setResponses(prev => {
                        const newResponses = [...prev]
                        const lastIdx = newResponses.length - 1
                        if (lastIdx >= 0 && newResponses[lastIdx].isStreaming) {
                            newResponses[lastIdx] = { role: 'agent', text, isStreaming: true }
                        } else {
                            newResponses.push({ role: 'agent', text, isStreaming: true })
                        }
                        return newResponses
                    })
                },
                (finalText) => {
                    setStatusMsg('')
                    setResponses(prev => {
                        const newResponses = [...prev]
                        const lastIdx = newResponses.length - 1
                        if (lastIdx >= 0 && newResponses[lastIdx].isStreaming) {
                            newResponses[lastIdx] = { role: 'agent', text: finalText, isStreaming: false }
                        } else {
                            newResponses.push({ role: 'agent', text: finalText, isStreaming: false })
                        }
                        return newResponses
                    })
                },
                user.name || user.email.split('@')[0],
                (status) => setStatusMsg(status)
            )
        } catch (error) {
            console.error("Error sending message:", error)
            setResponses(prev => {
                const filtered = prev.filter(m => !m.isStreaming)
                return [
                    ...filtered,
                    { role: "agent", text: "Sorry, there was an error processing your message. Please try again." }
                ]
            })
        } finally {
            setIsLoading(false)
        }
    }

    // Task 3: Derive agentState for Orb
    const agentState = voiceStatus === 'speaking' ? 'speaking'
        : voiceStatus === 'listening' ? 'listening'
        : null

    return (
        <div className="flex h-screen bg-black text-white overflow-hidden relative">
            {/* Aurora Background */}
            <div className="fixed inset-0 w-full h-full">
                <Aurora
                    colorStops={["#3A29FF", "#FF94B4", "#FF3232"]}
                    blend={0.5}
                    amplitude={1.0}
                    speed={0.5}
                />
            </div>

            {/* Sidebar */}
            <Sidebar collapsed={true} variant="chat" />

            {/* Main Content */}
            <main className="flex-1 flex flex-col relative z-10 min-h-0">
                {/* Task 5: nav — top bar unchanged */}
                <nav className="relative z-10 flex items-center justify-between px-8 py-6 flex-shrink-0">
                    <div className="text-xl font-bold">NextGen Voice</div>

                    <div className="flex items-center gap-4">
                        <button
                            onClick={handleNewConversation}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-green-500/10 border border-green-500/30 hover:bg-green-500/20 hover:border-green-500/50 rounded-full transition text-green-400"
                            disabled={isLoading}
                        >
                            <MessageSquarePlus size={16} />
                            <span>Start New Conversation</span>
                        </button>

                        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium border border-gray-700 hover:border-gray-500 rounded-full transition">
                            <SettingsIcon size={16} />
                            <span>Configuration</span>
                        </button>

                        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium border border-gray-700 hover:border-gray-500 rounded-full transition">
                            <Download size={16} />
                            <span>Export</span>
                        </button>

                        <button
                            onClick={handleLogout}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 hover:border-red-500/50 rounded-full transition text-red-400"
                        >
                            <LogOut size={16} />
                            <span>Logout</span>
                        </button>
                    </div>
                </nav>

                {/* Task 5: Chat_Panel — always visible, flex-1 */}
                <CustomScrollbar className="flex-1 px-6 py-4 min-h-0">
                    <div className="max-w-4xl mx-auto space-y-4">
                        {responses.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                <div
                                    className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm
                                        ${msg.role === "user"
                                            ? "bg-green-500 text-black rounded-br-none"
                                            : "bg-white/10 text-white rounded-bl-none"
                                        }`}
                                >
                                    {msg.role === "user" ? (
                                        msg.text
                                    ) : (
                                        <MessageContent content={msg.text} />
                                    )}
                                </div>
                            </div>
                        ))}
                        {isLoading && !responses.some(m => m.isStreaming) && (
                            <ThinkingIndicator liveStatus={statusMsg} />
                        )}
                        <div ref={chatEndRef} />
                    </div>
                </CustomScrollbar>

                {/* Task 3: Voice_Panel — always visible, fixed height strip */}
                <div className="flex-shrink-0 border-t border-white/10 bg-black/20 px-6 py-3">
                    <div className="max-w-4xl mx-auto flex items-center gap-4">
                        {/* Orb */}
                        <div className="w-14 h-14 flex-shrink-0">
                            <Orb
                                colorsRef={voiceOrbColorsRef}
                                agentState={agentState}
                                className="w-full h-full"
                            />
                        </div>

                        {/* Status text */}
                        <p className="text-sm text-gray-400 flex-1">
                            {voiceStatusText[voiceStatus] ?? voiceStatus}
                        </p>

                        {/* Error message */}
                        {voiceStatus === 'error' && (
                            <p className="text-xs text-red-400">Connection error — please try again</p>
                        )}

                        {/* Mic button */}
                        <button
                            onClick={() => voiceImperativeRef.current?.toggleMic()}
                            disabled={voiceStatus === 'connecting'}
                            className={`w-10 h-10 flex items-center justify-center rounded-full transition
                                ${voiceMicOn
                                    ? 'bg-green-500 hover:bg-green-600 text-white'
                                    : 'bg-gray-600 hover:bg-gray-500 text-white'
                                }
                                disabled:opacity-50 disabled:cursor-not-allowed`}
                            title={voiceMicOn ? 'Mute mic' : 'Unmute mic'}
                        >
                            {voiceStatus === 'connecting' ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : voiceMicOn ? (
                                <Mic size={16} />
                            ) : (
                                <MicOff size={16} />
                            )}
                        </button>

                        {/* Disconnect button — only when connected */}
                        {voiceConnected && (
                            <button
                                onClick={() => voiceImperativeRef.current?.disconnect()}
                                className="w-10 h-10 flex items-center justify-center rounded-full bg-red-500 hover:bg-red-600 text-white transition"
                                title="Disconnect voice"
                            >
                                <PhoneOff size={16} />
                            </button>
                        )}
                    </div>
                </div>

                {/* Input_Toolbar — chat input always visible */}
                <div className="flex-shrink-0 px-6 pb-4 pt-2">
                    <div className="max-w-4xl mx-auto">
                        <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl">
                            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent rounded-2xl pointer-events-none" />

                            <div className="relative flex items-center gap-3">
                                <textarea
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey && !isLoading) {
                                            e.preventDefault()
                                            sendMessage()
                                        }
                                    }}
                                    placeholder={isLoading ? "Waiting for response..." : "Type your message..."}
                                    className="flex-1 bg-transparent border-none outline-none resize-none text-sm placeholder-gray-400 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                                    rows={2}
                                    disabled={isLoading}
                                />
                                <button
                                    onClick={sendMessage}
                                    className="w-9 h-9 flex items-center justify-center bg-gradient-to-br from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-full transition shadow-lg shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                                    title="Send Message"
                                    disabled={isLoading}
                                >
                                    {isLoading ? (
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                        <Send size={16} />
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Task 5: VoiceInterface — headless, just before closing main */}
                <VoiceInterface
                    channel="voice"
                    userId={JSON.parse(localStorage.getItem('user'))?.user_id}
                    onResponse={undefined}
                    onStatusChange={setVoiceStatus}
                    onOrbColorsChange={(colors) => { voiceOrbColorsRef.current = colors }}
                    onConnectedChange={setVoiceConnected}
                    onMicChange={setVoiceMicOn}
                    imperativeRef={voiceImperativeRef}
                />
            </main>
        </div>
    )
}

export default ChatSession
