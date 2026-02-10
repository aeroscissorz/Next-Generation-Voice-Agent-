# API Module

This folder contains all API-related functions for communicating with the interceptor and external services.

## Structure

```
api/
├── config.js       # API configuration and endpoints
├── chatApi.js      # Chat/messaging related API calls
├── authApi.js      # Authentication related API calls
└── index.js        # Central export file
```

## Usage

### Chat API

```javascript
import { sendChatMessage, checkHealth } from '../api';

// Send a chat message
const response = await sendChatMessage('Hello!', 'user@example.com');
console.log(response.reply);

// Check backend health
const health = await checkHealth();
console.log(health.status);
```

### Auth API

```javascript
import { loginUser, registerUser, checkUserExists } from '../api';

// Login
const result = await loginUser('user@example.com', 'password123');
if (result.success) {
  console.log('User data:', result.data);
}

// Register
const registerResult = await registerUser('user@example.com', 'John Doe', 'password123');
if (registerResult.success) {
  console.log('Registration successful');
}

// Check if user exists
const exists = await checkUserExists('user@example.com');
console.log('User exists:', exists.exists);
```

## Configuration

The API base URL is configured in `config.js` and reads from the environment variable:

```
VITE_INTERCEPTOR_URL=http://localhost:8001
```

## Error Handling

All API functions include try-catch blocks and return structured responses:

```javascript
{
  success: boolean,
  data?: object,
  error?: string
}
```

## Adding New API Functions

1. Create a new file in the `api/` folder (e.g., `userApi.js`)
2. Import necessary dependencies
3. Export your API functions
4. Add exports to `index.js`

Example:

```javascript
// userApi.js
import API_BASE_URL from './config';

export const getUserProfile = async (userId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/users/${userId}`);
    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};
```

```javascript
// index.js
export * from './userApi';
```
