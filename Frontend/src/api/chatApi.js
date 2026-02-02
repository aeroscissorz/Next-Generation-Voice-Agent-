import API_BASE_URL, { API_ENDPOINTS } from './config';

/**
 * Send a chat message to the backend agent
 * @param {string} message - The user's message
 * @param {string} userId - The user's email/ID
 * @param {Object} options - Optional parameters
 * @param {string} options.name - User's name for personalization
 * @param {string} options.channelType - Channel type: 'text' or 'voice' (default: 'text')
 * @returns {Promise<{reply: string, channel_type: string, user_name: string|null}>} The agent's response
 */
export const sendChatMessage = async (message, userId, options = {}) => {
  try {
    const { name = null, channelType = 'text' } = options;
    
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.CHAT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId,
        name,
        channel_type: channelType,
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
