import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Mic, Phone, Settings as SettingsIcon, Download, LogOut } from 'lucide-react'
import SplitText from '../components/SplitText'
import Aurora from '../components/Aurora'
import { Orb } from '../components/ui/orb'
import Sidebar from '../components/Sidebar'

function Dashboard() {
    const navigate = useNavigate()
    const [userName, setUserName] = useState('')
    const orbColorsRef = useRef(["#FF6B6B", "#4ECDC4"])

    useEffect(() => {
        const userData = localStorage.getItem('user')
        if (userData) {
            const user = JSON.parse(userData)
            setUserName(user.name || 'Guest')
        } else {
            navigate('/login')
        }
    }, [navigate])

    const handleLogout = () => {
        localStorage.removeItem('user')
        navigate('/')
    }

    const handleModeSelect = (mode) => {
        const sessionId = `session_${Date.now()}`
        navigate(`/dashboard/${sessionId}`, {
            state: { mode }
        })
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
            <Sidebar variant="dashboard" />
            {/* Main Content */}
            <main className="flex-1 flex flex-col relative z-10">

                {/* ===== Top Bar ===== */}
                <nav className="relative z-10 flex items-center justify-between px-8 py-6">
                    <div className="text-xl font-bold">NextGen Voice</div>

                    <div className="flex items-center gap-4">
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

                {/* ===== Static Header (Orb + Greeting) ===== */}
                <div className="flex flex-col items-center justify-center flex-1 py-8">
                    <div className="relative mb-6 w-32 h-32">
                        <Orb
                            colorsRef={orbColorsRef}
                            agentState={null}
                            className="w-full h-full"
                        />
                    </div>

                    {userName && (
                        <SplitText
                            text={`Hi ${userName}!`}
                            className="text-2xl font-normal text-gray-300"
                            tag="p"
                            delay={30}
                            duration={1}
                            splitType="chars"
                            from={{ opacity: 0, y: 20 }}
                            to={{ opacity: 1, y: 0 }}
                        />
                    )}

                    <h2 className="text-4xl font-normal mt-2 text-white text-center mb-12">
                        How can we help you today?
                    </h2>

                    {/* Mode Selector Cards */}
                    <div className="flex items-center gap-6 mt-8">
                        {/* Chat Mode */}
                        <button
                            onClick={() => handleModeSelect('chat')}
                            className="group relative w-64 h-48 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/20"
                        >
                            <div className="flex flex-col items-center justify-center h-full">
                                <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <MessageSquare size={32} className="text-white" />
                                </div>
                                <h3 className="text-xl font-medium text-white mb-2">Chat</h3>
                                <p className="text-sm text-gray-400 text-center">Text-based conversation</p>
                            </div>
                        </button>

                        {/* Voice Mode */}
                        <button
                            onClick={() => handleModeSelect('voice')}
                            className="group relative w-64 h-48 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-green-500/20"
                        >
                            <div className="flex flex-col items-center justify-center h-full">
                                <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-500 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <Mic size={32} className="text-white" />
                                </div>
                                <h3 className="text-xl font-medium text-white mb-2">Voice</h3>
                                <p className="text-sm text-gray-400 text-center">Digital voice chat</p>
                            </div>
                        </button>

                        {/* Telephonic Mode */}
                        <button
                            onClick={() => handleModeSelect('telephonic')}
                            className="group relative w-64 h-48 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-blue-500/20"
                        >
                            <div className="flex flex-col items-center justify-center h-full">
                                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <Phone size={32} className="text-white" />
                                </div>
                                <h3 className="text-xl font-medium text-white mb-2">Telephonic</h3>
                                <p className="text-sm text-gray-400 text-center">Formal voice calls</p>
                            </div>
                        </button>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default Dashboard
