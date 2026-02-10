import API_BASE_URL, { API_ENDPOINTS } from './config';

/**
 * Send a chat message to the interceptor service
 * @param {string} message - The user's message
 * @param {string} userId - The user's email/ID
 * @param {Object} options - Optional parameters
 * @param {string} options.name - User's name for personalization
 * @param {string} options.channel - Channel type: 'chat', 'voice', 'telephonic'
 * @returns {Promise<{reply: string, user_name: string|null, channel: string, formatted: boolean}>} The formatted response
 */
export const sendChatMessage = async (message, userId, options = {}) => {
  try {
    const { name = null, channel = 'chat' } = options;
    
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.CHAT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId,
        name,
        channel,
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
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.NEW_SESSION}`, {
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
