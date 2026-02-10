// API Configuration
const API_BASE_URL =
  import.meta.env.VITE_INTERCEPTOR_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  'http://localhost:8001';

export const API_ENDPOINTS = {
  HEALTH: '/',
  CHAT: '/chat',
};

export default API_BASE_URL;
