import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { Settings as SettingsIcon, Send, Download, LogOut, MessageSquarePlus } from 'lucide-react'
import Aurora from '../components/Aurora'
import { Orb } from '../components/ui/orb'
import CustomScrollbar from '../components/CustomScrollbar'
import Sidebar from '../components/Sidebar'
import VoiceInterface from '../components/VoiceInterface'
import MessageContent from '../components/MessageContent'
import { processMessage, processMessageStream } from '../services/interceptor'
import { createNewSession } from '../api/chatApi'

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
    const [mode, setMode] = useState(location.state?.mode || 'chat') // Get mode from navigation state
    const chatEndRef = useRef(null)
    const orbColorsRef = useRef(["#FF6B6B", "#4ECDC4"])

    // Determine orb size based on mode
    const orbSize = mode === 'voice' || mode === 'telephonic' ? 'w-20 h-20' : 'w-12 h-12'

    useEffect(() => {
        // Get user data from localStorage
        const userData = localStorage.getItem('user')
        if (!userData) {
            navigate('/login')
            return
        }

        const user = JSON.parse(userData)
        const name = user.name || user.email?.split('@')[0] || 'there'

        // Get initial message from location state
        const initialMessage = location.state?.initialMessage
        const initialResponse = location.state?.initialResponse

        if (initialMessage && initialResponse) {
            setResponses([
                { role: "user", text: initialMessage },
                { role: "agent", text: initialResponse }
            ])
        } else {
            // AI speaks first
            setResponses([
                { role: "agent", text: `Hi ${name}! I'm your NextGen support assistant. How can I help you today?` }
            ])
        }
    }, [navigate, location.state])

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

            // Call backend to create new session
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
            // Add user message immediately
            setResponses(prev => [
                ...prev,
                { role: "user", text: message }
            ])

            // Clear input and set loading
            const currentMessage = message
            setMessage("")
            setIsLoading(true)
            setStatusMsg('')

            // Process message with streaming
            await processMessageStream(
                'chat',
                { text: currentMessage },
                user.user_id,
                // onChunk - intermediate text updates (partial streaming)
                (text) => {
                    setResponses(prev => {
                        const newResponses = [...prev]
                        const lastIdx = newResponses.length - 1
                        // Update existing streaming message or add new one
                        if (lastIdx >= 0 && newResponses[lastIdx].isStreaming) {
                            newResponses[lastIdx] = { role: 'agent', text, isStreaming: true }
                        } else {
                            newResponses.push({ role: 'agent', text, isStreaming: true })
                        }
                        return newResponses
                    })
                },
                // onDone - final response
                (finalText) => {
                    setStatusMsg('')
                    setResponses(prev => {
                        const newResponses = [...prev]
                        const lastIdx = newResponses.length - 1
                        // Replace streaming message or add final message
                        if (lastIdx >= 0 && newResponses[lastIdx].isStreaming) {
                            newResponses[lastIdx] = { role: 'agent', text: finalText, isStreaming: false }
                        } else {
                            newResponses.push({ role: 'agent', text: finalText, isStreaming: false })
                        }
                        return newResponses
                    })
                },
                user.name || user.email.split('@')[0],
                // onStatus - live tool activity
                (status) => setStatusMsg(status)
            )
        } catch (error) {
            console.error("Error sending message:", error)
            setResponses(prev => {
                // Remove the streaming message and add error
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
            <main className="flex-1 flex flex-col relative z-10">
                {/* Top Bar - Same as Dashboard */}
                <nav className="relative z-10 flex items-center justify-between px-8 py-6">
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

                {/* Compact Header with Small Orb - Only show in chat mode */}
                {mode === 'chat' && (
                    <div className="flex items-center justify-center py-4">
                        <div className={`relative ${orbSize} mr-3 transition-all duration-300`}>
                            <Orb
                                colorsRef={orbColorsRef}
                                agentState={null}
                                className="w-full h-full"
                            />
                        </div>
                        <div>
                            <p className="text-sm text-gray-400">Chatting with</p>
                            <h2 className="text-lg font-medium text-white">NextGen AI Assistant</h2>
                        </div>
                    </div>
                )}

                {/* Scrollable Chat Area - Only show in chat mode */}
                {mode === 'chat' && (
                    <CustomScrollbar className="flex-1 px-6 py-4">
                        <div className="max-w-4xl mx-auto space-y-4">
                            {responses.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"
                                        }`}
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
                            )}                            <div ref={chatEndRef} />
                        </div>
                    </CustomScrollbar>
                )}

                {/* Bottom Input Area or Voice Interface */}
                <div className={`${mode === 'chat' ? 'px-6 pb-4' : 'flex-1 flex items-center justify-center'}`}>
                    {mode === 'chat' ? (
                        // Chat Input
                        <div className="max-w-4xl mx-auto">
                            <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl">
                                <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent rounded-2xl pointer-events-none"></div>

                                {/* Input Field */}
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

                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={sendMessage}
                                            className="w-9 h-9 flex items-center justify-center bg-gradient-to-br from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-full transition shadow-lg shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                                            title="Send Message"
                                            disabled={isLoading}
                                        >
                                            {isLoading ? (
                                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                            ) : (
                                                <Send size={16} />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        // Voice Interface - Full screen centered
                        <div className="w-full h-full flex items-center justify-center">
                            <VoiceInterface
                                channel={mode}
                                userId={JSON.parse(localStorage.getItem('user'))?.user_id}
                                onResponse={(data) => {
                                    if (typeof data === 'string') {
                                        setResponses(prev => [
                                            ...prev,
                                            { role: 'agent', text: data }
                                        ])
                                    } else if (data?.user && data?.agent) {
                                        setResponses(prev => [
                                            ...prev,
                                            { role: 'user', text: data.user },
                                            { role: 'agent', text: data.agent }
                                        ])
                                    }
                                }}
                            />
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}

export default ChatSession
