/**
 * Voice Service - WebSocket-based voice communication
 * Handles connection to Interceptor voice WebSocket
 */

class VoiceService {
  constructor() {
    this.ws = null;
    this.isConnected = false;
    this.recognition = null;
    this.audioContext = null;
    this.audioQueue = [];
    this.isPlaying = false;
    this.onAudioCallback = null;
    this.onErrorCallback = null;
    this.onStateChangeCallback = null;
    this.currentState = null; // null, 'listening', 'talking', 'thinking'
  }

  /**
   * Connect to voice WebSocket
   */
  connect(userId, userName, interceptorUrl = 'ws://localhost:8001') {
    return new Promise((resolve, reject) => {
      try {
        // Close existing connection if any
        if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
          console.log('🔌 Closing existing connection...');
          this.ws.close();
          this.ws = null;
        }

        // Wait a bit before creating new connection
        setTimeout(() => {
          this.ws = new WebSocket(`${interceptorUrl}/ws/voice`);

          this.ws.onopen = () => {
            console.log('✓ Voice WebSocket connected');
            this.isConnected = true;

            // Send initialization message
            this.ws.send(JSON.stringify({
              user_id: userId,
              user_name: userName
            }));

            this.setState('listening');
            resolve();
          };

          this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
          };

          this.ws.onerror = (error) => {
            console.error('✗ Voice WebSocket error:', error);
            if (this.onErrorCallback) {
              this.onErrorCallback('Connection error');
            }
            reject(error);
          };

          this.ws.onclose = () => {
            console.log('🔌 Voice WebSocket disconnected');
            this.isConnected = false;
            this.setState(null);
          };
        }, 100); // Small delay to ensure clean connection
        
      } catch (error) {
        console.error('✗ Failed to connect:', error);
        reject(error);
      }
    });
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(data) {
    switch (data.type) {
      case 'audio':
        // Received audio chunk from agent
        this.playAudioChunk(data.audio);
        this.setState('talking');
        break;

      case 'audio_complete':
        // Agent finished speaking
        console.log('✓ Audio playback complete');
        this.setState('listening');
        break;

      case 'error':
        console.error('✗ Server error:', data.message);
        if (this.onErrorCallback) {
          this.onErrorCallback(data.message);
        }
        break;

      default:
        console.log('📨 Received:', data);
    }
  }

  /**
   * Set current state and notify callback
   */
  setState(state) {
    this.currentState = state;
    if (this.onStateChangeCallback) {
      this.onStateChangeCallback(state);
    }
  }

  /**
   * Initialize speech recognition (Web Speech API)
   */
  initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.error('✗ Speech recognition not supported');
      return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';
    this.recognition.isRunning = false;

    this.recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1];
      const transcript = result[0].transcript;

      if (result.isFinal) {
        console.log('👤 User said:', transcript);
        this.sendUserSpeech(transcript);
      }
    };

    this.recognition.onerror = (event) => {
      console.error('✗ Speech recognition error:', event.error);
      
      // Don't restart on certain errors
      if (event.error === 'aborted' || event.error === 'not-allowed') {
        if (this.recognition) {
          this.recognition.isRunning = false;
        }
        return;
      }
      
      // Auto-restart on other errors
      if (event.error === 'no-speech' && this.isConnected) {
        setTimeout(() => {
          if (this.isConnected && this.recognition && !this.recognition.isRunning) {
            this.startListening();
          }
        }, 1000);
      }
    };

    this.recognition.onend = () => {
      // Check if recognition still exists and is not null before accessing it
      if (this.recognition && this.recognition !== null) {
        this.recognition.isRunning = false;
        
        // Auto-restart recognition if still connected
        if (this.isConnected) {
          setTimeout(() => {
            if (this.isConnected && this.recognition && this.recognition !== null && !this.recognition.isRunning) {
              this.startListening();
            }
          }, 500);
        }
      }
    };

    console.log('✓ Speech recognition initialized');
    return true;
  }

  /**
   * Start listening to user speech
   */
  startListening() {
    if (!this.recognition) {
      if (!this.initSpeechRecognition()) {
        if (this.onErrorCallback) {
          this.onErrorCallback('Speech recognition not supported in this browser');
        }
        return false;
      }
    }

    try {
      // Check if already running
      if (this.recognition.isRunning) {
        console.log('🎤 Recognition already running');
        return true;
      }
      
      this.recognition.start();
      this.recognition.isRunning = true;
      this.setState('listening');
      console.log('🎤 Started listening');
      return true;
    } catch (error) {
      // If error is "already started", ignore it
      if (error.message && error.message.includes('already started')) {
        console.log('🎤 Recognition already active');
        this.recognition.isRunning = true;
        return true;
      }
      console.error('✗ Failed to start listening:', error);
      return false;
    }
  }

  /**
   * Stop listening to user speech
   */
  stopListening() {
    if (this.recognition) {
      try {
        this.recognition.stop();
        this.recognition.isRunning = false;
        console.log('🔇 Stopped listening');
      } catch (error) {
        console.error('✗ Error stopping recognition:', error);
      }
    }
  }

  /**
   * Send user speech text to server
   */
  sendUserSpeech(text) {
    if (!this.isConnected || !this.ws) {
      console.error('✗ Not connected to voice service');
      return;
    }

    this.setState('thinking');

    this.ws.send(JSON.stringify({
      type: 'user_speech',
      text: text
    }));

    console.log('📤 Sent user speech:', text);
  }

  /**
   * Interrupt agent speech
   */
  interrupt() {
    if (!this.isConnected || !this.ws) {
      return;
    }

    this.ws.send(JSON.stringify({
      type: 'interrupt'
    }));

    // Stop current audio playback
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.audioQueue = [];
    this.isPlaying = false;

    this.setState('listening');
    console.log('⚠️  Interrupted agent');
  }

  /**
   * Play audio chunk (base64 encoded)
   */
  async playAudioChunk(base64Audio) {
    try {
      console.log('🔊 Attempting to play audio chunk, length:', base64Audio.length);
      
      // Initialize audio context if needed
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('✓ Audio context initialized');
      }

      // Resume audio context if suspended (browser autoplay policy)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
        console.log('✓ Audio context resumed');
      }

      // Decode base64 to array buffer
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      console.log('✓ Decoded audio data, size:', bytes.length, 'bytes');

      // Decode audio data
      const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
      console.log('✓ Audio buffer decoded, duration:', audioBuffer.duration, 'seconds');

      // Create source and play
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);
      source.start();

      console.log('✓ Audio playback started');
    } catch (error) {
      console.error('✗ Error playing audio:', error);
      console.error('   Error details:', error.message);
      console.error('   Audio context state:', this.audioContext?.state);
    }
  }

  /**
   * End conversation
   */
  endConversation() {
    if (this.isConnected && this.ws) {
      this.ws.send(JSON.stringify({
        type: 'end_conversation'
      }));
    }

    this.stopListening();
    this.disconnect();
  }

  /**
   * Disconnect from voice service
   */
  disconnect() {
    console.log('🔌 Disconnecting from voice service...');
    
    // Set isConnected to false first to prevent auto-restart
    this.isConnected = false;
    
    // Stop and clear recognition
    if (this.recognition) {
      try {
        // Remove event handlers to prevent them from firing during cleanup
        this.recognition.onend = null;
        this.recognition.onerror = null;
        this.recognition.onresult = null;
        
        // Stop recognition if running
        if (this.recognition.isRunning) {
          this.recognition.stop();
        }
        
        // Clear the reference
        this.recognition = null;
      } catch (error) {
        console.error('✗ Error stopping recognition:', error);
        // Force clear even on error
        this.recognition = null;
      }
    }

    // Close audio context
    if (this.audioContext) {
      try {
        this.audioContext.close();
        this.audioContext = null;
      } catch (error) {
        console.error('✗ Error closing audio context:', error);
        this.audioContext = null;
      }
    }

    // Close WebSocket
    if (this.ws) {
      try {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.close();
        }
        this.ws = null;
      } catch (error) {
        console.error('✗ Error closing WebSocket:', error);
        this.ws = null;
      }
    }

    this.setState(null);
    console.log('👋 Disconnected from voice service');
  }

  /**
   * Set callback for state changes
   */
  onStateChange(callback) {
    this.onStateChangeCallback = callback;
  }

  /**
   * Set callback for errors
   */
  onError(callback) {
    this.onErrorCallback = callback;
  }

  /**
   * Get current state
   */
  getState() {
    return this.currentState;
  }
}

// Export singleton instance
export const voiceService = new VoiceService();
export default voiceService;
