const axios = require('axios');

// Use environment variable with fallback for local development
// Sanitize by trimming to avoid 'Invalid URL' when env has trailing spaces/newlines
const rawApiBase = process.env.API_BASE;
const sanitizedApiBase = (typeof rawApiBase === 'string' ? rawApiBase.trim() : '') || 'http://localhost:8000';

// Optional: basic validation so we can see what's wrong in logs
try {
  // Throws if not a valid absolute URL
  new URL(sanitizedApiBase);
} catch (e) {
  console.error(`Invalid API_BASE provided: ${JSON.stringify(rawApiBase)} → using sanitized: ${JSON.stringify(sanitizedApiBase)}`);
}

const apiClient = axios.create({
  baseURL: sanitizedApiBase,
  timeout: 10000, // 10 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`🚀 ${config.method?.toUpperCase()} ${config.url} (base: ${sanitizedApiBase})`);
    }
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`✅ ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
    }
    return response;
  },
  (error) => {
    if (error.response) {
      console.error(`❌ ${error.response.status} ${error.config?.method?.toUpperCase()} ${error.config?.url}:`, error.response.data);
      
      switch (error.response.status) {
        case 401:
          console.error('Unauthorized - Authentication required');
          break;
        case 403:
          console.error('Forbidden - Access denied');
          break;
        case 404:
          console.error('Not Found - Resource not available');
          break;
        case 500:
          console.error('Internal Server Error - Backend issue');
          break;
        default:
          console.error(`HTTP Error ${error.response.status}`);
      }
    } else if (error.request) {
      console.error('❌ Network Error - No response received:', error.message);
    } else {
      console.error('❌ Request Setup Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

module.exports = {
  apiClient
};