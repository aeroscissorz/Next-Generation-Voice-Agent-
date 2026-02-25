import API_BASE_URL, { API_ENDPOINTS } from './config';

/**
 * Send a chat message to the backend agent
 * @param {string} message - The user's message
 * @param {string} userId - The user's email/ID
 * @param {Object} options - Optional parameters
 * @param {string} options.name - User's name for personalization
 * @returns {Promise<{reply: string, user_name: string|null}>} The agent's response
 */
export const sendChatMessage = async (message, userId, options = {}) => {
  try {
    const { name = null } = options;
    
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.CHAT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId,
        name,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

/**
 * Check backend health status
 * @returns {Promise<{status: string}>} Health status
 */
export const checkHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.HEALTH}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
};

/**
 * Create a new session for a user (resets conversation history)
 * @param {string} userId - The user's email/ID
 * @param {string} name - User's name for personalization (optional)
 * @returns {Promise<{status: string, message: string, session_id: string, user_id: string, user_name: string|null}>} Session creation response
 */
export const createNewSession = async (userId, name = null) => {
  try {
    const response = await fetch(`${API_BASE_URL}/new-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        name,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating new session:', error);
    throw error;
  }
};

/**
 * Send a chat message with streaming response
 * @param {string} message - The user's message
 * @param {string} userId - The user's email/ID
 * @param {Object} options - Optional parameters
 * @param {string} options.name - User's name for personalization
 * @param {function} onChunk - Callback for each text chunk
 * @param {function} onDone - Callback when streaming is complete
 * @returns {Promise<void>}
 */
export const sendChatMessageStream = async (message, userId, options = {}, onChunk, onDone) => {
  try {
    const { name = null } = options;
    const requestStart = performance.now();
    
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId,
        name,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let finalText = '';
    let firstChunkLogged = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.error) {
              throw new Error(data.error);
            }
            if (data.status && !data.text) {
              continue;
            }
            if (data.text) {
              if (!firstChunkLogged) {
                firstChunkLogged = true;
                console.log(`⏱️ Response received after ${((performance.now() - requestStart) / 1000).toFixed(2)}s`);
              }
              finalText = data.text;
            }
            if (data.done) {
              onDone(finalText);
              return;
            }
            if (data.text && !data.done) {
              onChunk(finalText);
            }
          } catch (e) {
            if (e.message && !e.message.includes('JSON')) {
              throw e;
            }
          }
        }
      }
    }
    
    onDone(finalText);
  } catch (error) {
    console.error('Error in streaming chat:', error);
    throw error;
  }
};
