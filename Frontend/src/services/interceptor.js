/**
 * Interceptor Service - Channel-agnostic message processing
 * Handles chat channel formatting
 * Voice/Telephonic channels are handled by OpenAI Realtime via VoiceInterface
 *
 * NOTE: Gemini formatting is done SERVER-SIDE in the Interceptor (port 8001).
 * The /chat endpoint already returns formatted markdown — no client-side
 * Gemini call is needed.
 */

import { sendChatMessage } from '../api/chatApi'

/**
 * Process message through interceptor layer
 * @param {string} channel - 'chat' | 'voice' | 'telephonic'
 * @param {Object} input - Input data (text for chat, voice handled by VoiceInterface)
 * @param {string} userId - User identifier
 * @param {Object} callbacks - Optional callbacks for events (unused for chat)
 * @param {string} userName - Optional user name for personalization
 * @returns {Promise<Object>} Processed response
 */
export async function processMessage(channel, input, userId, callbacks = {}, userName = null) {
  // Voice/Telephonic channels: Handled by VoiceInterface component
  // via OpenAI Realtime WebRTC + Interceptor tool calls
  if (channel === 'voice' || channel === 'telephonic') {
    return {
      type: 'voice',
      message: 'Voice channel handled by VoiceInterface',
      handledBy: 'openai-realtime'
    }
  }

  // Chat channel processing
  const text = input.text

  // Send to Interceptor → Backend. The Interceptor already formats
  // the response into clean markdown via Gemini before returning it.
  const response = await sendChatMessage(text, userId, {
    name: userName
  })
  const formattedReply = response.reply

  return {
    type: 'text',
    message: formattedReply,
    rawData: response.raw_reply || formattedReply,
    handledBy: 'backend'
  }
}
