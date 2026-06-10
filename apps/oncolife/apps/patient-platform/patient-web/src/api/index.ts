/**
 * API Module Index
 * =================
 * 
 * Main entry point for all API-related exports.
 * 
 * Usage:
 *   import { authApi, chatApi, api, ApiClientError } from '@/api';
 */

// Re-export all services
export * from './services';

// Export core client and utilities
export { api, tokenManager, ApiClientError, NetworkError, AuthenticationError } from './client';

// Export all types
export type * from './types';





