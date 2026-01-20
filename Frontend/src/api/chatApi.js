import API_BASE_URL, { API_ENDPOINTS } from './config';

/**
 * Send a chat message to the backend agent
 * @param {string} message - The user's message
 * @param {string} userId - The user's email/ID
 * @returns {Promise<{reply: string}>} The agent's response
 */
export const sendChatMessage = async (message, userId) => {
  try {
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.CHAT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id: userId,
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
