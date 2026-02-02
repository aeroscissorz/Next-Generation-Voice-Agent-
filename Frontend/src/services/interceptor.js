/**
 * Interceptor Service - Channel-agnostic message processing
 * Handles chat, voice, and telephonic channels
 */

import { transcribeAudio, synthesizeAudio } from './elevenlabsService'
import { sendChatMessage } from '../api/chatApi'

// Filler phrases for natural conversation during processing
const FILLERS = {
  billing: [
    "Let me pull up your billing information for you",
    "Just checking your account details",
    "One moment while I look at your billing history",
    "Let me see what's going on with your account",
    "Alright, checking your payment information now"
  ],
  support: [
    "Let me look into that for you",
    "Okay, checking your support tickets",
    "Give me just a second to pull up your case",
    "Let me see what I can find out about that",
    "Alright, looking into your issue now"
  ],
  generic: [
    "Just a moment",
    "Let me check on that",
    "Okay, give me one second",
    "Alright, let me see",
    "Hold on just a moment"
  ]
}

/**
 * Get appropriate filler phrase based on message content
 * @param {string} text - User's message
 * @returns {string} Filler phrase
 */
function getFiller(text) {
  const lower = text.toLowerCase()
  
  if (lower.includes('bill') || lower.includes('payment') || lower.includes('charge')) {
    return FILLERS.billing[Math.floor(Math.random() * FILLERS.billing.length)]
  }
  
  if (lower.includes('support') || lower.includes('help') || lower.includes('issue')) {
    return FILLERS.support[Math.floor(Math.random() * FILLERS.support.length)]
  }
  
  return FILLERS.generic[Math.floor(Math.random() * FILLERS.generic.length)]
}

/**
 * Play audio blob
 * @param {Blob} audioBlob - Audio to play
 * @returns {Promise<void>}
 */
function playAudio(audioBlob) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(audioBlob)
    const audio = new Audio(url)
    
    audio.onended = () => {
      URL.revokeObjectURL(url)
      resolve()
    }
    
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      resolve()
    }
    
    audio.play().catch(() => resolve())
  })
}

/**
 * Process message through interceptor layer
 * @param {string} channel - 'chat' | 'voice' | 'telephonic'
 * @param {Object} input - Input data (text or audioBlob)
 * @param {string} userId - User identifier
 * @param {Object} callbacks - Optional callbacks for events
 * @returns {Promise<Object>} Processed response
 */
export async function processMessage(channel, input, userId, callbacks = {}) {
  const { onTranscript, onResponse } = callbacks
  
  let text = ''
  
  // Step 1: Normalize input to text
  if (channel === 'chat') {
    text = input.text
    
  } else if (channel === 'voice' || channel === 'telephonic') {
    // Transcribe audio using ElevenLabs STT
    text = await transcribeAudio(input.audioBlob)
    onTranscript && onTranscript(text)
    
    // Get and play filler while processing (don't show in transcript)
    const fillerText = getFiller(text)
    const style = channel === 'voice' ? 'conversational' : 'formal'
    const fillerAudio = await synthesizeAudio(fillerText, style, true)  // true = isFiller
    
    // Play filler audio (non-blocking) - don't trigger onFiller to avoid showing in UI
    playAudio(fillerAudio)
  }
  
  // Step 2: Send to backend
  const response = await sendChatMessage(text, userId)
  const responseText = response.reply
  
  // Step 3: Format output based on channel
  if (channel === 'chat') {
    return {
      type: 'text',
      message: responseText,
      handledBy: 'backend'
    }
    
  } else if (channel === 'voice' || channel === 'telephonic') {
    // Convert response to speech using ElevenLabs TTS
    const style = channel === 'voice' ? 'conversational' : 'formal'
    const audio = await synthesizeAudio(responseText, style)
    
    if (onResponse) {
      onResponse(responseText, audio)
    }
    
    return {
      type: 'audio',
      audio,
      text: responseText,
      handledBy: 'backend'
    }
  }
}
