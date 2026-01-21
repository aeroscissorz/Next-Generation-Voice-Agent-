import { useEffect, useRef } from 'react'

/**
 * CustomScrollbar - A themed scrollbar component
 * @param {Object} props
 * @param {React.ReactNode} props.children - Content to be scrolled
 * @param {string} props.className - Additional classes for the container
 * @param {string} props.height - Height of the scrollable area (default: 'h-full')
 */
function CustomScrollbar({ children, className = '', height = 'h-full' }) {
    const scrollRef = useRef(null)

    useEffect(() => {
        const scrollElement = scrollRef.current
        if (!scrollElement) return

        // Optional: Add smooth scrolling behavior
        scrollElement.style.scrollBehavior = 'smooth'
    }, [])

    return (
        <div
            ref={scrollRef}
            className={`${height} overflow-y-auto custom-scrollbar ${className}`}
        >
            {children}
        </div>
    )
}

export default CustomScrollbar
