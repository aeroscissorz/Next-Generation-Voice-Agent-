/**
 * Interceptor Service - Channel-agnostic message processing
 * Handles chat channel formatting
 * Voice/Telephonic channels are handled by ElevenLabs Widget
 */

import { sendChatMessage } from '../api/chatApi'
import { GoogleGenerativeAI } from '@google/generative-ai'

// Initialize Gemini AI for text formatting
const genAI = new GoogleGenerativeAI(import.meta.env.VITE_GOOGLE_API_KEY)
const model = genAI.getGenerativeModel({ model: import.meta.env.VITE_GOOGLE_GENAI_MODEL })

/**
 * Process message through interceptor layer
 * @param {string} channel - 'chat' | 'voice' | 'telephonic'
 * @param {Object} input - Input data (text for chat, voice handled by widget)
 * @param {string} userId - User identifier
 * @param {Object} callbacks - Optional callbacks for events (unused for chat)
 * @param {string} userName - Optional user name for personalization
 * @returns {Promise<Object>} Processed response
 */
export async function processMessage(channel, input, userId, callbacks = {}, userName = null) {
  // Voice/Telephonic channels: Handled entirely by ElevenLabs Widget
  // Widget manages STT, backend calls, TTS, and conversation flow
  // See: eleven_labs_prompts/system.md for widget configuration
  if (channel === 'voice' || channel === 'telephonic') {
    return {
      type: 'voice',
      message: 'Voice channel handled by ElevenLabs Widget',
      handledBy: 'elevenlabs-widget'
    }
  }
  
  // Chat channel processing
  const text = input.text
  
  // Step 1: Send to backend (backend returns pure data)
  const response = await sendChatMessage(text, userId, {
    name: userName
  })
  const responseText = response.reply
  
  // Step 2: Format pure data into structured markdown using Gemini AI
  const formattedResponse = await formatForTextChannel(responseText)
  console.log(formattedResponse)
  
  return {
    type: 'text',
    message: formattedResponse,
    rawData: responseText, // Keep original for reference
    handledBy: 'backend'
  }
}

/**
 * Format pure data for text channel using Gemini AI
 * Converts natural language response into structured markdown
 * @param {string} text - Pure data from backend
 * @returns {Promise<string>} Formatted markdown
 */
async function formatForTextChannel(text) {
  try {
    const prompt = `You are a formatting assistant for a customer service chat interface. Convert the following plain text response into well-formatted markdown.

Rules:
- Use **bold** for important information like amounts, dates, invoice numbers, and statuses
- Use bullet points (*) for lists of items or options
- Use tables (markdown format) when showing multiple invoices, breakdowns, or structured data
- Keep the friendly, conversational tone intact
- Add appropriate line breaks for readability
- Use ✓ checkmarks for confirmations or completed actions
- Do NOT change the content, meaning, or add new information - only format it
- Return ONLY the formatted markdown, no explanations or meta-commentary

Plain text to format:
${text}`;

    const result = await model.generateContent(prompt);
    const response = result.response;
    const formattedText = response.text();
    
    return formattedText;
  } catch (error) {
    console.error('Error formatting with Gemini:', error);
    // Fallback to original text if Gemini fails
    return text;
  }
}
