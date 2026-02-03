import { useMemo } from 'react'

/**
 * MessageContent Component
 * Renders agent messages with markdown support including tables, lists, and formatting
 */
function MessageContent({ content }) {
    // Parse and render markdown content
    const renderedContent = useMemo(() => {
        return parseMarkdown(content)
    }, [content])

    return <div className="markdown-content">{renderedContent}</div>
}

/**
 * Simple markdown parser for common elements
 * Supports: tables, bold, bullet lists, numbered lists, checkmarks
 */
function parseMarkdown(text) {
    const elements = []
    const lines = text.split('\n')
    let i = 0

    while (i < lines.length) {
        const line = lines[i]

        // Check for table
        if (line.includes('|') && i + 1 < lines.length && lines[i + 1].includes('|')) {
            const tableLines = []
            while (i < lines.length && lines[i].includes('|')) {
                tableLines.push(lines[i])
                i++
            }
            elements.push(renderTable(tableLines))
            continue
        }

        // Check for bullet list
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            const listItems = []
            while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
                listItems.push(lines[i].trim().substring(2))
                i++
            }
            elements.push(renderBulletList(listItems))
            continue
        }

        // Check for numbered list
        if (/^\d+\.\s/.test(line.trim())) {
            const listItems = []
            while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
                listItems.push(lines[i].trim().replace(/^\d+\.\s/, ''))
                i++
            }
            elements.push(renderNumberedList(listItems))
            continue
        }

        // Regular paragraph
        if (line.trim()) {
            elements.push(renderParagraph(line))
        } else {
            elements.push(<br key={`br-${i}`} />)
        }

        i++
    }

    return elements
}

/**
 * Render a markdown table
 */
function renderTable(lines) {
    if (lines.length < 2) return null

    // Parse header
    const headerCells = lines[0]
        .split('|')
        .map(cell => cell.trim())
        .filter(cell => cell)

    // Skip separator line (line 1)
    // Parse body rows
    const bodyRows = lines.slice(2).map(line =>
        line
            .split('|')
            .map(cell => cell.trim())
            .filter(cell => cell)
    )

    return (
        <div key={`table-${Math.random()}`} className="my-3 overflow-x-auto">
            <table className="w-full border-collapse bg-white/5 rounded-lg overflow-hidden">
                <thead>
                    <tr className="bg-white/10">
                        {headerCells.map((cell, idx) => (
                            <th
                                key={idx}
                                className="px-4 py-2 text-left text-xs font-semibold text-gray-300 border-b border-white/10"
                            >
                                {renderInlineFormatting(cell)}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {bodyRows.map((row, rowIdx) => (
                        <tr key={rowIdx} className="border-b border-white/5 hover:bg-white/5">
                            {row.map((cell, cellIdx) => (
                                <td
                                    key={cellIdx}
                                    className="px-4 py-2 text-sm text-gray-200"
                                >
                                    {renderInlineFormatting(cell)}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

/**
 * Render a bullet list
 */
function renderBulletList(items) {
    return (
        <ul key={`ul-${Math.random()}`} className="my-2 ml-4 space-y-1">
            {items.map((item, idx) => (
                <li key={idx} className="text-sm text-gray-200 flex items-start">
                    <span className="mr-2 text-green-400">•</span>
                    <span>{renderInlineFormatting(item)}</span>
                </li>
            ))}
        </ul>
    )
}

/**
 * Render a numbered list
 */
function renderNumberedList(items) {
    return (
        <ol key={`ol-${Math.random()}`} className="my-2 ml-4 space-y-1 list-decimal list-inside">
            {items.map((item, idx) => (
                <li key={idx} className="text-sm text-gray-200">
                    {renderInlineFormatting(item)}
                </li>
            ))}
        </ol>
    )
}

/**
 * Render a paragraph with inline formatting
 */
function renderParagraph(text) {
    return (
        <p key={`p-${Math.random()}`} className="my-2 text-sm text-gray-200">
            {renderInlineFormatting(text)}
        </p>
    )
}

/**
 * Render inline formatting (bold, checkmarks, currency)
 */
function renderInlineFormatting(text) {
    const parts = []
    let currentText = text
    let key = 0

    // Replace checkmarks
    currentText = currentText.replace(/✓/g, '✓')
    currentText = currentText.replace(/✔/g, '✓')

    // Split by bold markers
    const boldRegex = /\*\*(.+?)\*\*/g
    let lastIndex = 0
    let match

    while ((match = boldRegex.exec(currentText)) !== null) {
        // Add text before bold
        if (match.index > lastIndex) {
            parts.push(
                <span key={key++}>{currentText.substring(lastIndex, match.index)}</span>
            )
        }

        // Add bold text
        parts.push(
            <strong key={key++} className="font-bold text-white">
                {match[1]}
            </strong>
        )

        lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < currentText.length) {
        parts.push(<span key={key++}>{currentText.substring(lastIndex)}</span>)
    }

    return parts.length > 0 ? parts : text
}

export default MessageContent
