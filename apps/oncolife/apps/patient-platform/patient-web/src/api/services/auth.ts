/**
 * Authentication API Service
 * ==========================
 * 
 * Type-safe authentication API calls.
 */

import { api, tokenManager } from '../client';
import { API_CONFIG } from '../../config/api';
import type {
  LoginRequest,
  LoginResponse,
  SignupRequest,
  SignupResponse,
  CompletePasswordRequest,
  CompletePasswordResponse,
} from '../types';

const { ENDPOINTS } = API_CONFIG;

export const authApi = {
  /**
   * Login with email and password
   */
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>(
      ENDPOINTS.AUTH.LOGIN,
      credentials,
      { skipAuth: true }
    );

    // Store tokens if login was successful
    if (response.tokens) {
      tokenManager.setToken(response.tokens.access_token);
      tokenManager.setRefreshToken(response.tokens.refresh_token);
    }

    return response;
  },

  /**
   * Register a new patient
   */
  signup: async (data: SignupRequest): Promise<SignupResponse> => {
    return api.post<SignupResponse>(
      ENDPOINTS.AUTH.SIGNUP,
      data,
      { skipAuth: true }
    );
  },

  /**
   * Complete new password setup (after first login with temp password)
   */
  completeNewPassword: async (data: CompletePasswordRequest): Promise<CompletePasswordResponse> => {
    const response = await api.post<CompletePasswordResponse>(
      ENDPOINTS.AUTH.COMPLETE_NEW_PASSWORD,
      data,
      { skipAuth: true }
    );

    // Store tokens after password is set
    if (response.tokens) {
      tokenManager.setToken(response.tokens.access_token);
      tokenManager.setRefreshToken(response.tokens.refresh_token);
    }

    return response;
  },

  /**
   * Logout the current user
   */
  logout: async (): Promise<void> => {
    try {
      await api.post(ENDPOINTS.AUTH.LOGOUT);
    } finally {
      // Always clear tokens, even if API call fails
      tokenManager.clearTokens();
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated: (): boolean => {
    return tokenManager.isAuthenticated();
  },

  /**
   * Get current auth token
   */
  getToken: (): string | null => {
    return tokenManager.getToken();
  },
};

export default authApi;





