/**
 * Interceptor Service - Channel-agnostic message processing with AI routing
 * Handles chat, voice, and telephonic channels
 */

import { transcribeAudio, synthesizeAudio } from './elevenlabsService'
import { sendChatMessage } from '../api/chatApi'
import { GoogleGenerativeAI } from '@google/generative-ai'

const GEMINI_API_KEY = import.meta.env.VITE_GOOGLE_API_KEY
const genAI = new GoogleGenerativeAI(GEMINI_API_KEY)

// Filler phrases for natural conversation during processing
const FILLERS = {
  billing: [
    "Let me check your billing information",
    "Looking up your account",
    "Checking your current bill"
  ],
  support: [
    "Checking your support tickets",
    "Looking into that for you",
    "Let me pull up your case"
  ],
  generic: [
    "One moment please",
    "Let me check that for you",
    "Just a second"
  ]
}

/**
 * Analyze message intent using Gemini API with streaming
 * @param {string} text - User's message
 * @returns {Promise<{needsBackend: boolean, category: string, response?: string}>}
 */
async function analyzeIntent(text) {
  try {
    const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash-exp' })
    
    const prompt = 
      `You are an intelligent message router for a customer support system.

      Analyze this user message and determine:
      1. Does it need backend processing (billing/support queries)?
      2. Or can you handle it directly (greetings, jokes, casual chat)?

      User message: "${text}"

      Respond in JSON format:
      {
        "needsBackend": true/false,
        "category": "billing" | "support" | "casual",
        "response": "your response if casual, otherwise null"
      }

      Rules:
      - needsBackend=true for: billing questions, payment issues, account queries, support tickets, technical problems
      - needsBackend=false for: greetings (hi, hello, how are you), jokes, casual chat, general questions
      - If needsBackend=false, provide a friendly, helpful response
      - Keep responses concise and natural`

    const result = await model.generateContent(prompt)
    const response = await result.response
    const textResponse = response.text()
    
    // Extract JSON from response (handle markdown code blocks)
    const jsonMatch = textResponse.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0])
    }
    
    // Fallback: assume needs backend
    return { needsBackend: true, category: 'generic' }
    
  } catch (error) {
    console.error('Error analyzing intent:', error)
    // On error, route to backend to be safe
    return { needsBackend: true, category: 'generic' }
  }
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
 * Process message through interceptor layer with AI routing
 * @param {string} channel - 'chat' | 'voice' | 'telephonic'
 * @param {Object} input - Input data (text or audioBlob)
 * @param {string} userId - User identifier
 * @param {Object} callbacks - Optional callbacks for events
 * @returns {Promise<Object>} Processed response
 */
export async function processMessage(channel, input, userId, callbacks = {}) {
  const { onFiller, onTranscript, onResponse, onAnalyzing } = callbacks
  
  let text = ''
  
  // Step 1: Normalize input to text
  if (channel === 'chat') {
    text = input.text
    
  } else if (channel === 'voice' || channel === 'telephonic') {
    // Transcribe audio using ElevenLabs STT
    text = await transcribeAudio(input.audioBlob)
    onTranscript && onTranscript(text)
    
    // Get and play filler while processing
    const fillerText = getFiller(text)
    const fillerAudio = await synthesizeAudio(fillerText, 'conversational')
    
    if (onFiller) {
      onFiller(fillerText, fillerAudio)
    }
    
    // Play filler audio (non-blocking)
    playAudio(fillerAudio)
  }
  
  // Step 2: Analyze intent with Gemini
  onAnalyzing && onAnalyzing(true)
  const intent = await analyzeIntent(text)
  onAnalyzing && onAnalyzing(false)
  
  let responseText = ''
  
  // Step 3: Route based on intent
  if (intent.needsBackend) {
    // Route to backend for billing/support
    const response = await sendChatMessage(text, userId)
    responseText = response.reply
  } else {
    // Handle directly with Gemini's response
    responseText = intent.response || "I'm here to help! How can I assist you today?"
  }
  
  // Step 4: Format output based on channel
  if (channel === 'chat') {
    return {
      type: 'text',
      message: responseText,
      handledBy: intent.needsBackend ? 'backend' : 'interceptor'
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
      handledBy: intent.needsBackend ? 'backend' : 'interceptor'
    }
  }
}
