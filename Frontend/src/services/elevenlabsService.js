/**
 * ElevenLabs Service - Speech-to-Text (STT) and Text-to-Speech (TTS)
 */

const ELEVENLABS_API_KEY = import.meta.env.VITE_ELEVENLABS_API_KEY

/**
 * Transcribe audio to text using ElevenLabs STT
 * @param {Blob} audioBlob - Audio blob to transcribe
 * @returns {Promise<string>} Transcribed text
 */
export async function transcribeAudio(audioBlob) {
  const formData = new FormData()
  formData.append('file', audioBlob, 'recording.webm')
  formData.append('model_id', 'scribe_v1')
  
  const response = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
    method: 'POST',
    headers: {
      'xi-api-key': ELEVENLABS_API_KEY
    },
    body: formData
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(`ElevenLabs STT error: ${response.status} - ${JSON.stringify(error)}`)
  }
  
  const data = await response.json()
  return data.text
}

/**
 * Convert text to speech using ElevenLabs TTS
 * @param {string} text - Text to synthesize
 * @param {string} style - 'conversational' or 'formal' (kept for compatibility, but uses same settings)
 * @param {boolean} isFiller - Whether this is a filler phrase (slower, calmer pacing)
 * @returns {Promise<Blob>} Audio blob
 */
export async function synthesizeAudio(text, style = 'conversational', isFiller = false) {
  // Always use Bella's voice - natural and conversational
  const voiceId = 'EXAVITQu4vr4xnSDxMaL'  // Bella
  
  // Adjust settings for fillers to sound more natural and slower
  const stability = isFiller ? 0.5 : 0.25  // Higher for fillers = slower, calmer
  const styleValue = isFiller ? 0.5 : 0.9  // Less expressive for fillers
  
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
    {
      method: 'POST',
      headers: {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': ELEVENLABS_API_KEY
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_turbo_v2_5',  // Latest model with most natural speech
        voice_settings: {
          stability: stability,
          similarity_boost: 0.9,  // Higher = more authentic voice character
          style: styleValue,
          use_speaker_boost: true
        }
      })
    }
  )
  
  if (!response.ok) {
    throw new Error(`ElevenLabs TTS error: ${response.status}`)
  }
  
  const audioBlob = await response.blob()
  return audioBlob
}
