import { createContext, useContext, useState } from 'react'

const SidebarContext = createContext()

export function SidebarProvider({ children }) {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const [conversations, setConversations] = useState([
        { id: 1, title: 'Billing Inquiry - Invoice #1234', date: '2 hours ago' },
        { id: 2, title: 'Account Balance Check', date: 'Yesterday' },
        { id: 3, title: 'Technical Support - Login Issue', date: '2 days ago' },
        { id: 4, title: 'Payment Method Update', date: '3 days ago' },
    ])

    const toggleSidebar = () => {
        setIsSidebarOpen(prev => !prev)
    }

    const addConversation = (conversation) => {
        setConversations(prev => [conversation, ...prev])
    }

    const removeConversation = (id) => {
        setConversations(prev => prev.filter(conv => conv.id !== id))
    }

    const value = {
        isSidebarOpen,
        setIsSidebarOpen,
        toggleSidebar,
        conversations,
        setConversations,
        addConversation,
        removeConversation,
    }

    return (
        <SidebarContext.Provider value={value}>
            {children}
        </SidebarContext.Provider>
    )
}

export function useSidebar() {
    const context = useContext(SidebarContext)
    if (!context) {
        throw new Error('useSidebar must be used within a SidebarProvider')
    }
    return context
}
