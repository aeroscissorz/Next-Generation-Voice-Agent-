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
  formData.append('model_id', 'eleven_multilingual_v2')
  
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
 * @param {string} style - 'conversational' or 'formal'
 * @returns {Promise<Blob>} Audio blob
 */
export async function synthesizeAudio(text, style = 'conversational') {
  // Choose voice based on style
  const voiceId = style === 'formal' 
    ? 'pNInz6obpgDQGcFmaJgB'  // Adam - formal, professional
    : '21m00Tcm4TlvDq8ikWAM'  // Rachel - conversational, friendly
  
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
        model_id: 'eleven_turbo_v2',  // Fastest model
        voice_settings: {
          stability: style === 'formal' ? 0.7 : 0.5,
          similarity_boost: 0.75,
          style: style === 'formal' ? 0.3 : 0.5,
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
