"""
Test script for Voice Handler
Run this to test the voice WebSocket connection
"""

import asyncio
import websockets
import json
import sys

async def test_voice_connection():
    """Test voice WebSocket connection"""
    uri = "ws://localhost:8001/ws/voice"
    
    print("🔌 Connecting to voice WebSocket...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected!")
            
            # Send initialization
            init_message = {
                "user_id": "test@example.com",
                "user_name": "Test User"
            }
            await websocket.send(json.dumps(init_message))
            print(f"📤 Sent init: {init_message}")
            
            # Listen for initial greeting
            print("\n🎧 Listening for messages...")
            
            # Receive a few messages
            for i in range(5):
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=5.0
                    )
                    data = json.loads(message)
                    print(f"\n📨 Received message {i+1}:")
                    print(f"   Type: {data.get('type')}")
                    
                    if data.get('type') == 'audio':
                        audio_len = len(data.get('audio', ''))
                        print(f"   Audio length: {audio_len} chars")
                        print(f"   Context: {data.get('context_id')}")
                    elif data.get('type') == 'audio_complete':
                        print(f"   Context completed: {data.get('context_id')}")
                        break
                    elif data.get('type') == 'error':
                        print(f"   Error: {data.get('message')}")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏱️  Timeout waiting for message")
                    break
            
            # Test sending user speech
            print("\n📤 Sending test user speech...")
            user_speech = {
                "type": "user_speech",
                "text": "What's my account balance?"
            }
            await websocket.send(json.dumps(user_speech))
            print(f"   Sent: {user_speech['text']}")
            
            # Listen for response
            print("\n🎧 Listening for agent response...")
            for i in range(10):
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=10.0
                    )
                    data = json.loads(message)
                    
                    if data.get('type') == 'audio':
                        print(f"   📊 Received audio chunk {i+1}")
                    elif data.get('type') == 'audio_complete':
                        print(f"   ✓ Response complete!")
                        break
                    elif data.get('type') == 'error':
                        print(f"   ✗ Error: {data.get('message')}")
                        break
                        
                except asyncio.TimeoutError:
                    print("   ⏱️  Timeout - response may be complete")
                    break
            
            # End conversation
            print("\n👋 Ending conversation...")
            await websocket.send(json.dumps({"type": "end_conversation"}))
            
            print("\n✓ Test completed successfully!")
            
    except ConnectionRefusedError:
        print("✗ Connection refused. Is the Interceptor service running?")
        print("   Run: cd Interceptor && python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Voice WebSocket Test")
    print("=" * 60)
    print()
    
    asyncio.run(test_voice_connection())
