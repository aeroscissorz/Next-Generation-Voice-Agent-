"""
Voice Handler for ElevenLabs WebSocket Integration
Handles bidirectional voice communication with context management
"""

import os
import json
import asyncio
import websockets
import httpx
import logging
from typing import Optional, Dict, Any
import base64

logger = logging.getLogger("VoiceHandler")


class VoiceHandler:
    """
    Manages voice conversation flow:
    1. Receives audio from frontend
    2. Converts speech to text (STT)
    3. Sends text to backend agent
    4. Streams agent response to ElevenLabs TTS
    5. Sends audio back to frontend
    """
    
    def __init__(self, backend_url: str, elevenlabs_api_key: str, voice_id: str):
        self.backend_url = backend_url
        self.elevenlabs_api_key = elevenlabs_api_key
        self.voice_id = voice_id
        self.model_id = "eleven_flash_v2_5"
        self.context_counter = 0
        self.current_context_id = None
        self.elevenlabs_ws = None
        
    async def connect_to_elevenlabs(self):
        """Establish WebSocket connection to ElevenLabs TTS"""
        # Use stream-input endpoint (not multi-stream-input)
        websocket_uri = (
            f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/"
            f"stream-input?model_id={self.model_id}"
        )
        
        logger.info(f"🔗 Connecting to ElevenLabs: {websocket_uri}")
        
        try:
            self.elevenlabs_ws = await websockets.connect(
                websocket_uri,
                max_size=16 * 1024 * 1024
            )
            
            # Send initial configuration with API key
            await self.elevenlabs_ws.send(json.dumps({
                "text": " ",  # Initial empty text
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8,
                    "use_speaker_boost": False
                },
                "generation_config": {
                    "chunk_length_schedule": [50, 120, 160, 250]  # Lower first threshold for faster response
                },
                "xi_api_key": self.elevenlabs_api_key
            }))
            
            logger.info("✓ Connected to ElevenLabs WebSocket and sent configuration")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to ElevenLabs: {e}")
            return False
    
    async def disconnect_from_elevenlabs(self):
        """Close ElevenLabs WebSocket connection"""
        if self.elevenlabs_ws:
            try:
                # Send empty string to indicate end of text sequence
                await self.elevenlabs_ws.send(json.dumps({"text": ""}))
                await self.elevenlabs_ws.close()
                logger.info("✓ Disconnected from ElevenLabs")
            except Exception as e:
                logger.error(f"✗ Error disconnecting from ElevenLabs: {e}")
    
    def get_next_context_id(self) -> str:
        """Generate unique context ID for each conversation turn"""
        self.context_counter += 1
        return f"context_{self.context_counter}"
    
    async def send_text_to_elevenlabs(
        self, 
        text: str, 
        context_id: str, 
        voice_settings: Optional[Dict] = None
    ):
        """Send text to ElevenLabs for TTS conversion"""
        if not self.elevenlabs_ws:
            logger.error("✗ ElevenLabs WebSocket not connected")
            return
        
        # Simple stream-input format
        message = {
            "text": text,
            "flush": True  # Force immediate generation
        }
        
        try:
            message_json = json.dumps(message)
            logger.info(f"📤 Sending to ElevenLabs: {message_json[:200]}")
            await self.elevenlabs_ws.send(message_json)
            logger.info(f"✓ Sent text to ElevenLabs (context: {context_id})")
            logger.info(f"   Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        except Exception as e:
            logger.error(f"✗ Error sending to ElevenLabs: {e}")
    
    async def flush_context(self, context_id: str):
        """Force generation of buffered audio"""
        if not self.elevenlabs_ws:
            return
        
        try:
            await self.elevenlabs_ws.send(json.dumps({
                "context_id": context_id,
                "flush": True
            }))
            logger.info(f"🔄 Flushed context: {context_id}")
        except Exception as e:
            logger.error(f"✗ Error flushing context: {e}")
    
    async def close_context(self, context_id: str):
        """Close a specific context"""
        if not self.elevenlabs_ws:
            return
        
        try:
            await self.elevenlabs_ws.send(json.dumps({
                "context_id": context_id,
                "close_context": True
            }))
            logger.info(f"🔒 Closed context: {context_id}")
        except Exception as e:
            logger.error(f"✗ Error closing context: {e}")
    
    async def handle_interruption(self, old_context_id: str, new_text: str):
        """Handle user interruption during agent response"""
        logger.info(f"⚠️  User interrupted context: {old_context_id}")
        
        # Close interrupted context
        await self.close_context(old_context_id)
        
        # Start new context
        new_context_id = self.get_next_context_id()
        await self.send_text_to_elevenlabs(new_text, new_context_id)
        
        return new_context_id
    
    async def receive_audio_from_elevenlabs(self, frontend_ws):
        """
        Receive audio chunks from ElevenLabs and forward to frontend
        """
        logger.info("🎧 Started listening for audio from ElevenLabs...")
        try:
            async for message in self.elevenlabs_ws:
                logger.info(f"📨 Received message from ElevenLabs")
                data = json.loads(message)
                context_id = data.get("contextId", "unknown")
                
                logger.info(f"   Message keys: {list(data.keys())}")
                
                # Log the actual audio field value
                audio_field = data.get("audio")
                logger.info(f"   Audio field type: {type(audio_field)}")
                logger.info(f"   Audio field value: {str(audio_field)[:100] if audio_field else 'None/Empty'}")
                
                # Check if audio exists and is not empty
                if audio_field and len(str(audio_field)) > 0:
                    audio_data = audio_field
                    logger.info(f"   Audio data length: {len(audio_data)}")
                    
                    try:
                        await frontend_ws.send_json({
                            "type": "audio",
                            "audio": audio_data,
                            "context_id": context_id
                        })
                        logger.info(f"🔊 Forwarded audio chunk (context: {context_id}, size: {len(audio_data)} chars)")
                    except Exception as send_error:
                        logger.error(f"✗ Error sending audio to frontend: {send_error}")
                else:
                    logger.warning(f"⚠️  No audio data in message (audio field is empty or None)")
                    # Log the entire message for debugging
                    logger.info(f"   Full message: {json.dumps(data, indent=2)[:500]}")
                
                # Check both isFinal and is_final for compatibility
                if data.get("isFinal") or data.get("is_final"):
                    logger.info(f"✓ Context completed: {context_id}")
                    try:
                        await frontend_ws.send_json({
                            "type": "audio_complete",
                            "context_id": context_id
                        })
                    except Exception as send_error:
                        logger.error(f"✗ Error sending completion to frontend: {send_error}")
                    
        except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError) as e:
            logger.info(f"Audio receiving stopped: {e}")
        except Exception as e:
            logger.error(f"✗ Error receiving audio: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def process_voice_message(
        self, 
        user_text: str, 
        user_id: str, 
        user_name: Optional[str] = None
    ) -> str:
        """
        Send user message to backend agent and get response
        """
        logger.info(f"🤖 Processing voice message for user: {user_id}")
        logger.info(f"   Message: {user_text}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.backend_url}/chat",
                    json={
                        "message": user_text,
                        "user_id": user_id,
                        "name": user_name
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    agent_response = data.get("reply", "")
                    logger.info(f"✓ Got agent response (length: {len(agent_response)} chars)")
                    return agent_response
                else:
                    logger.error(f"✗ Backend error: {response.status_code}")
                    return "I'm sorry, I'm having trouble processing your request right now."
                    
        except Exception as e:
            logger.error(f"✗ Error calling backend: {e}")
            return "I apologize, but I encountered an error. Please try again."
    
    async def handle_voice_conversation(
        self,
        frontend_ws,
        user_id: str,
        user_name: Optional[str] = None
    ):
        """
        Main conversation loop for voice interaction
        Handles the full flow: STT → Backend → TTS → Frontend
        """
        logger.info(f"🎤 Starting voice conversation for user: {user_id}")
        
        # Connect to ElevenLabs
        if not await self.connect_to_elevenlabs():
            await frontend_ws.send_json({
                "type": "error",
                "message": "Failed to connect to voice service"
            })
            return
        
        # Start audio receiving task
        audio_task = asyncio.create_task(
            self.receive_audio_from_elevenlabs(frontend_ws)
        )
        
        try:
            # Send initial greeting (flush is included in send_text_to_elevenlabs)
            greeting_context = self.get_next_context_id()
            greeting = "Hello! I'm your AI assistant. How can I help you today?"
            await self.send_text_to_elevenlabs(greeting, greeting_context)
            
            # Main conversation loop
            async for message in frontend_ws.iter_json():
                msg_type = message.get("type")
                
                if msg_type == "user_speech":
                    # User spoke - text from STT
                    user_text = message.get("text", "")
                    logger.info(f"👤 User said: {user_text}")
                    
                    # Get agent response
                    agent_response = await self.process_voice_message(
                        user_text, user_id, user_name
                    )
                    
                    # Send to TTS (with flush included)
                    response_context = self.get_next_context_id()
                    self.current_context_id = response_context
                    
                    await self.send_text_to_elevenlabs(
                        agent_response, 
                        response_context
                    )
                    # No need for separate flush - it's included in send_text_to_elevenlabs
                
                elif msg_type == "interrupt":
                    # User interrupted - stop current speech
                    if self.current_context_id:
                        await self.close_context(self.current_context_id)
                        logger.info("⚠️  User interrupted agent speech")
                
                elif msg_type == "end_conversation":
                    # User ended conversation
                    logger.info("👋 User ended conversation")
                    break
                    
        except Exception as e:
            logger.error(f"✗ Error in voice conversation: {e}")
        finally:
            # Cleanup
            audio_task.cancel()
            try:
                await audio_task
            except asyncio.CancelledError:
                pass
            
            await self.disconnect_from_elevenlabs()
            logger.info("✓ Voice conversation ended")


async def create_voice_handler(backend_url: str) -> VoiceHandler:
    """Factory function to create VoiceHandler with environment config"""
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice
    
    if not elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment")
    
    return VoiceHandler(backend_url, elevenlabs_api_key, voice_id)
