import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Archive, Library, Headphones, CreditCard, Mic, Paperclip, Settings as SettingsIcon, Send, Plus, Download, LogOut, Sparkles, DollarSign, Menu, X } from 'lucide-react'
import SplitText from '../components/SplitText'
import Aurora from '../components/Aurora'

function Dashboard() {
    const navigate = useNavigate()
    const [message, setMessage] = useState('')
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [userName, setUserName] = useState('')
    const [conversations, setConversations] = useState([
        { id: 1, title: 'Billing Inquiry - Invoice #1234', date: '2 hours ago' },
        { id: 2, title: 'Account Balance Check', date: 'Yesterday' },
        { id: 3, title: 'Technical Support - Login Issue', date: '2 days ago' },
        { id: 4, title: 'Payment Method Update', date: '3 days ago' },
    ])

    useEffect(() => {
        // Get user data from localStorage
        const userData = localStorage.getItem('user')
        if (userData) {
            const user = JSON.parse(userData)
            setUserName(user.name || 'Guest')
        } else {
            // If no user data, redirect to login
            navigate('/login')
        }
    }, [navigate])

    const handleLogout = () => {
        localStorage.removeItem('user')
        navigate('/')
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
            <aside className={`${isSidebarOpen ? 'w-64' : 'w-16'} bg-gray-900/50 backdrop-blur-sm border-r border-gray-800 flex flex-col relative z-10 transition-all duration-300`}>
                {/* Hamburger Icon */}
                <div className="p-4 flex items-center justify-center border-b border-gray-800">
                    <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="p-2 hover:bg-gray-800 rounded-lg transition"
                    >
                        {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="p-4">
                    <button className={`w-full flex items-center ${isSidebarOpen ? 'gap-2 px-4' : 'justify-center px-0'} py-2.5 bg-green-500 hover:bg-green-600 rounded-lg transition text-sm font-medium shadow-lg shadow-green-500/20`}>
                        <Plus size={18} />
                        {isSidebarOpen && <span>New Conversation</span>}
                    </button>
                </div>

                {/* Features Section */}
                <div className="px-4 pb-2">
                    {isSidebarOpen && <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Features</p>}
                    <nav className="space-y-1">
                        <button className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`} title="Chat Support">
                            <MessageSquare size={18} className="text-green-500" />
                            {isSidebarOpen && <span>Chat Support</span>}
                        </button>
                        <button className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`} title="Voice Support">
                            <Headphones size={18} className="text-green-500" />
                            {isSidebarOpen && <span>Voice Support</span>}
                        </button>
                        <button className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`} title="Archived">
                            <Archive size={18} className="text-green-500" />
                            {isSidebarOpen && <span>Archived</span>}
                        </button>
                        <button className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`} title="History">
                            <Library size={18} className="text-green-500" />
                            {isSidebarOpen && <span>History</span>}
                        </button>
                    </nav>
                </div>

                {/* Workspaces Section */}
                {isSidebarOpen && (
                    <div className="px-4 py-2 flex-1 overflow-y-auto">
                        <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Recent Conversations</p>
                        <nav className="space-y-1">
                            {conversations.map((conv) => (
                                <button
                                    key={conv.id}
                                    className="w-full flex items-start gap-3 px-3 py-2 hover:bg-gray-800 rounded-lg transition text-sm text-left"
                                >
                                    <MessageSquare size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="truncate">{conv.title}</p>
                                        <p className="text-xs text-gray-500">{conv.date}</p>
                                    </div>
                                </button>
                            ))}
                        </nav>
                    </div>
                )}
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col relative z-10">
                {/* Top Bar - Simple buttons only */}
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

                {/* Center Content - Orb */}
                <div className="flex-1 flex flex-col items-center justify-center px-6 py-8">
                    {/* Animated Orb */}
                    <div className="relative mb-8">
                        {/* Main orb */}
                        <div className="w-40 h-40 rounded-full bg-gradient-to-br from-green-400 via-emerald-500 to-teal-500 animate-pulse shadow-2xl shadow-green-500/50 relative overflow-hidden">
                            {/* Inner glow effect */}
                            <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-white/20 to-transparent"></div>
                        </div>
                        {/* Outer glow layers */}
                        <div className="absolute inset-0 w-40 h-40 rounded-full bg-gradient-to-br from-green-400 via-emerald-500 to-teal-500 blur-2xl opacity-60 animate-pulse"></div>
                        <div className="absolute inset-[-20px] rounded-full bg-gradient-to-br from-green-500/30 via-emerald-500/30 to-teal-500/30 blur-3xl animate-pulse"></div>
                    </div>

                    {/* Greeting with SplitText */}
                    {userName && (
                        <div className="mb-2">
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
                        </div>
                    )}

                    <h2 className="text-3xl font-normal mb-8 text-center text-white">How can we help you today?</h2>

                    {/* Quick Actions */}
                    <div className="flex items-center gap-4 mb-8">
                        <button className="flex items-center gap-2 px-4 py-2 border border-gray-700 hover:border-green-500 rounded-lg transition text-sm">
                            <CreditCard size={16} />
                            <span>Billing Inquiry</span>
                        </button>
                        <button className="flex items-center gap-2 px-4 py-2 border border-gray-700 hover:border-green-500 rounded-lg transition text-sm">
                            <Headphones size={16} />
                            <span>Technical Support</span>
                        </button>
                        <button className="flex items-center gap-2 px-4 py-2 border border-gray-700 hover:border-green-500 rounded-lg transition text-sm">
                            <DollarSign size={16} />
                            <span>Payment Issue</span>
                        </button>
                    </div>
                </div>

                {/* Bottom Input Area */}
                <div className="px-6 pb-6">
                    <div className="max-w-4xl mx-auto">
                        <div className="relative bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-6 shadow-2xl">
                            {/* Subtle gradient overlay for depth */}
                            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent rounded-3xl pointer-events-none"></div>

                            {/* Input Field */}
                            <div className="relative flex items-start gap-3 mb-4">
                                <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-500 rounded-lg flex items-center justify-center flex-shrink-0">
                                    <Sparkles size={16} />
                                </div>
                                <textarea
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder="Ask Anything..."
                                    className="flex-1 bg-transparent border-none outline-none resize-none text-base placeholder-gray-400 text-white"
                                    rows={3}
                                />
                            </div>

                            {/* Bottom Actions */}
                            <div className="relative flex items-center justify-between pt-4 border-t border-white/10">
                                <div className="flex items-center gap-4">
                                    <button className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-lg transition text-sm text-gray-400 hover:text-white">
                                        <Paperclip size={18} />
                                        <span>Attach</span>
                                    </button>
                                    <button className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-lg transition text-sm text-gray-400 hover:text-white">
                                        <SettingsIcon size={18} />
                                        <span>Settings</span>
                                    </button>
                                    <button className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 rounded-lg transition text-sm text-gray-400 hover:text-white">
                                        <SettingsIcon size={18} />
                                        <span>Options</span>
                                    </button>
                                </div>

                                <div className="flex items-center gap-3">
                                    <button className="w-11 h-11 flex items-center justify-center bg-white/5 hover:bg-white/10 border border-white/10 rounded-full transition" title="Voice Input">
                                        <Mic size={20} />
                                    </button>
                                    <button className="w-11 h-11 flex items-center justify-center bg-gradient-to-br from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-full transition shadow-lg shadow-purple-500/30" title="Send Message">
                                        <Send size={20} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default Dashboard
