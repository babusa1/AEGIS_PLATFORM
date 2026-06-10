/**
 * Type-Safe API Client
 * ====================
 * 
 * A robust, type-safe HTTP client for all API interactions.
 * Features:
 * - Automatic token handling
 * - Request/response interceptors
 * - Error handling with custom error types
 * - Request cancellation support
 * - Retry logic for transient failures
 */

import { API_CONFIG, buildUrl } from '../config/api';
import type { ApiError, ApiResponse } from './types';

// =============================================================================
// Configuration
// =============================================================================

const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

// =============================================================================
// Error Classes
// =============================================================================

export class ApiClientError extends Error {
  public status: number;
  public code?: string;
  public detail?: string;

  constructor(message: string, status: number, code?: string, detail?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }

  static fromResponse(response: Response, body?: ApiError): ApiClientError {
    const message = body?.message || body?.detail || response.statusText || 'Unknown error';
    return new ApiClientError(message, response.status, body?.code, body?.detail);
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network error occurred') {
    super(message);
    this.name = 'NetworkError';
  }
}

export class AuthenticationError extends ApiClientError {
  constructor(message: string = 'Authentication required') {
    super(message, 401, 'UNAUTHENTICATED');
    this.name = 'AuthenticationError';
  }
}

// =============================================================================
// Token Management
// =============================================================================

const TOKEN_KEY = 'authToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

export const tokenManager = {
  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
  },

  setToken: (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
  },

  getRefreshToken: (): string | null => {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setRefreshToken: (token: string): void => {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },

  clearTokens: (): void => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  isAuthenticated: (): boolean => {
    return !!localStorage.getItem(TOKEN_KEY);
  },
};

// =============================================================================
// Request Helpers
// =============================================================================

interface RequestConfig extends RequestInit {
  timeout?: number;
  retries?: number;
  skipAuth?: boolean;
}

const buildHeaders = (config: RequestConfig = {}): Headers => {
  const headers = new Headers(config.headers);

  // Set default content type for JSON
  if (!headers.has('Content-Type') && config.body) {
    headers.set('Content-Type', 'application/json');
  }

  // Add auth token if available and not skipped
  if (!config.skipAuth) {
    const token = tokenManager.getToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  return headers;
};

const sleep = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

const shouldRetry = (error: unknown, attempt: number, maxRetries: number): boolean => {
  if (attempt >= maxRetries) return false;
  
  // Retry on network errors
  if (error instanceof NetworkError) return true;
  
  // Retry on 5xx errors (server errors)
  if (error instanceof ApiClientError && error.status >= 500) return true;
  
  return false;
};

// =============================================================================
// Core Request Function
// =============================================================================

async function request<T>(
  endpoint: string,
  config: RequestConfig = {}
): Promise<T> {
  const url = buildUrl(endpoint);
  const { timeout = DEFAULT_TIMEOUT, retries = MAX_RETRIES, ...fetchConfig } = config;
  
  let lastError: Error | null = null;
  
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) {
      await sleep(RETRY_DELAY * attempt);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...fetchConfig,
        headers: buildHeaders(fetchConfig),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle no content responses
      if (response.status === 204) {
        return undefined as T;
      }

      // Parse response body
      let body: T | ApiError;
      const contentType = response.headers.get('content-type');
      
      if (contentType?.includes('application/json')) {
        body = await response.json();
      } else {
        body = await response.text() as T;
      }

      // Handle error responses
      if (!response.ok) {
        // Handle authentication errors
        if (response.status === 401) {
          tokenManager.clearTokens();
          throw new AuthenticationError();
        }

        throw ApiClientError.fromResponse(response, body as ApiError);
      }

      return body as T;

    } catch (error) {
      clearTimeout(timeoutId);
      
      // Handle abort errors (timeout)
      if (error instanceof Error && error.name === 'AbortError') {
        lastError = new NetworkError('Request timeout');
      }
      // Handle fetch errors (network issues)
      else if (error instanceof TypeError) {
        lastError = new NetworkError(error.message);
      }
      // Keep API errors as-is
      else if (error instanceof ApiClientError) {
        lastError = error;
      }
      else {
        lastError = error as Error;
      }

      // Check if we should retry
      if (!shouldRetry(lastError, attempt, retries)) {
        throw lastError;
      }
    }
  }

  throw lastError || new Error('Request failed');
}

// =============================================================================
// HTTP Method Helpers
// =============================================================================

export const api = {
  /**
   * GET request
   */
  get: <T>(endpoint: string, config?: RequestConfig): Promise<T> => {
    return request<T>(endpoint, { ...config, method: 'GET' });
  },

  /**
   * POST request with JSON body
   */
  post: <T>(endpoint: string, data?: unknown, config?: RequestConfig): Promise<T> => {
    return request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  /**
   * PUT request with JSON body
   */
  put: <T>(endpoint: string, data?: unknown, config?: RequestConfig): Promise<T> => {
    return request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  /**
   * PATCH request with JSON body
   */
  patch: <T>(endpoint: string, data?: unknown, config?: RequestConfig): Promise<T> => {
    return request<T>(endpoint, {
      ...config,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  /**
   * DELETE request
   */
  delete: <T>(endpoint: string, config?: RequestConfig): Promise<T> => {
    return request<T>(endpoint, { ...config, method: 'DELETE' });
  },
};

export default api;





