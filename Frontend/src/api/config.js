// API Configuration
// Frontend connects to Interceptor Service (not directly to Backend)
const API_BASE_URL = import.meta.env.VITE_INTERCEPTOR_URL || 'http://localhost:8001';

export const API_ENDPOINTS = {
  HEALTH: '/',
  CHAT: '/chat',
  NEW_SESSION: '/new-session',
};

export default API_BASE_URL;
