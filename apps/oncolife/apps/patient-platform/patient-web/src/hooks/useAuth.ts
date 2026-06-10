/**
 * useAuth Hook
 * =============
 * 
 * Authentication hook for managing user authentication state.
 * 
 * Features:
 * - Login/logout functionality
 * - Token management
 * - User profile loading
 * - Protected route checks
 */

import { useState, useCallback, useEffect } from 'react';
import { authApi, profileApi, tokenManager } from '../api';
import type { PatientProfile, LoginRequest, SignupRequest, CompletePasswordRequest } from '../api/types';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: PatientProfile | null;
  error: string | null;
  needsPasswordChange: boolean;
  session: string | null;
}

interface UseAuthReturn extends AuthState {
  login: (credentials: LoginRequest) => Promise<boolean>;
  signup: (data: SignupRequest) => Promise<boolean>;
  completeNewPassword: (data: CompletePasswordRequest) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

export function useAuth(): UseAuthReturn {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: tokenManager.isAuthenticated(),
    isLoading: true,
    user: null,
    error: null,
    needsPasswordChange: false,
    session: null,
  });

  // Load user profile on mount if authenticated
  useEffect(() => {
    const loadUser = async () => {
      if (tokenManager.isAuthenticated()) {
        try {
          const profile = await profileApi.getProfile();
          setState(prev => ({
            ...prev,
            isAuthenticated: true,
            isLoading: false,
            user: profile,
          }));
        } catch (error) {
          // Token might be expired
          tokenManager.clearTokens();
          setState(prev => ({
            ...prev,
            isAuthenticated: false,
            isLoading: false,
            user: null,
          }));
        }
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    loadUser();
  }, []);

  const login = useCallback(async (credentials: LoginRequest): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await authApi.login(credentials);

      if (response.user_status === 'NEW_PASSWORD_REQUIRED') {
        setState(prev => ({
          ...prev,
          isLoading: false,
          needsPasswordChange: true,
          session: response.session || null,
        }));
        return false;
      }

      if (response.tokens) {
        // Load user profile after successful login
        const profile = await profileApi.getProfile();
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          isLoading: false,
          user: profile,
          needsPasswordChange: false,
        }));
        return true;
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: response.message || 'Login failed',
      }));
      return false;

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, []);

  const signup = useCallback(async (data: SignupRequest): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await authApi.signup(data);
      setState(prev => ({ ...prev, isLoading: false }));
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Signup failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, []);

  const completeNewPassword = useCallback(async (data: CompletePasswordRequest): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await authApi.completeNewPassword(data);
      
      // Load user profile after successful password change
      const profile = await profileApi.getProfile();
      setState(prev => ({
        ...prev,
        isAuthenticated: true,
        isLoading: false,
        user: profile,
        needsPasswordChange: false,
        session: null,
      }));
      return true;

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Password change failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return false;
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authApi.logout();
    } finally {
      setState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        needsPasswordChange: false,
        session: null,
      });
    }
  }, []);

  const refreshUser = useCallback(async (): Promise<void> => {
    if (!tokenManager.isAuthenticated()) return;

    try {
      const profile = await profileApi.getProfile();
      setState(prev => ({ ...prev, user: profile }));
    } catch (error) {
      // Ignore errors during refresh
    }
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    login,
    signup,
    completeNewPassword,
    logout,
    refreshUser,
    clearError,
  };
}

export default useAuth;





