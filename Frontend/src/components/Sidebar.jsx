import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { MessageSquare, Archive, Library, Headphones, Plus, Menu, X, ChevronLeft, ChevronRight, SkipBackIcon, LucideSkipBack, PresentationIcon, SendToBack, LayoutDashboardIcon } from 'lucide-react'
import { useSidebar } from '../context/SidebarContext'
import CustomScrollbar from './CustomScrollbar'
import { BackSide } from 'three'

/**
 * Sidebar Component
 * @param {Object} props
 * @param {boolean} props.collapsed - Whether sidebar should start collapsed (default: false)
 * @param {string} props.variant - 'dashboard' or 'chat' (affects toggle icon)
 */
function Sidebar({ collapsed = false, variant = 'dashboard' }) {
    const navigate = useNavigate()
    const { isSidebarOpen, setIsSidebarOpen, toggleSidebar, conversations } = useSidebar()

    // Set initial state based on collapsed prop only once on mount
    useEffect(() => {
        if (collapsed) {
            setIsSidebarOpen(false)
        } else {
            setIsSidebarOpen(true)
        }
    }, []) // Empty dependency array - only run on mount

    const handleNewConversation = () => {
        navigate('/dashboard')
    }

    const handleConversationClick = (conv) => {
        // Navigate to specific conversation
        console.log('Navigate to conversation:', conv.id)
    }

    return (
        <aside className={`${isSidebarOpen ? 'w-64' : 'w-16'} bg-gray-900/50 backdrop-blur-sm border-r border-gray-800 flex flex-col relative z-10 transition-all duration-300`}>
            {/* Toggle Button */}
            <div className="p-4 flex items-center justify-center border-b border-gray-800">
                <button
                    onClick={toggleSidebar}
                    className="p-2 hover:bg-gray-800 rounded-lg transition"
                    title={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
                >
                    {variant === 'chat' ? (
                        isSidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />
                    ) : (
                        isSidebarOpen ? <X size={20} /> : <Menu size={20} />
                    )}
                </button>
            </div>

            {/* New Chat Button */}
            <div className="p-4">
                <button
                    onClick={handleNewConversation}
                    className={`w-full flex items-center ${isSidebarOpen ? 'gap-2 px-4' : 'justify-center px-0'} py-2.5 bg-green-500 hover:bg-green-600 rounded-lg transition text-sm font-medium shadow-lg shadow-green-500/20`}
                    title="New Conversation"
                >
                    <LayoutDashboardIcon size={18} />
                    {isSidebarOpen && <span>Go to Dashboard</span>}
                </button>
            </div>

            {/* Features Section */}
            {/* <div className="px-4 pb-2">
                {isSidebarOpen && <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Features</p>}
                <nav className="space-y-1">
                    <button
                        className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`}
                        title="Chat Support"
                    >
                        <MessageSquare size={18} className="text-green-500" />
                        {isSidebarOpen && <span>Chat Support</span>}
                    </button>
                    <button
                        className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`}
                        title="Voice Support"
                    >
                        <Headphones size={18} className="text-green-500" />
                        {isSidebarOpen && <span>Voice Support</span>}
                    </button>
                    <button
                        className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`}
                        title="Archived"
                    >
                        <Archive size={18} className="text-green-500" />
                        {isSidebarOpen && <span>Archived</span>}
                    </button>
                    <button
                        className={`w-full flex items-center ${isSidebarOpen ? 'gap-3 px-3' : 'justify-center px-0'} py-2 hover:bg-gray-800 rounded-lg transition text-sm`}
                        title="History"
                    >
                        <Library size={18} className="text-green-500" />
                        {isSidebarOpen && <span>History</span>}
                    </button>
                </nav>
            </div> */}

            {/* Conversations Section */}
            {isSidebarOpen && (
                <CustomScrollbar className="px-4 py-2 flex-1">
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Recent Conversations</p>
                    <nav className="space-y-1">
                        {conversations.map((conv) => (
                            <button
                                key={conv.id}
                                onClick={() => handleConversationClick(conv)}
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
                </CustomScrollbar>
            )}
        </aside>
    )
}

export default Sidebar
