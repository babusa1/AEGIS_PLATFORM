/**
 * Auth Context
 * =============
 * 
 * Global authentication context for the application.
 * Provides authentication state and methods to all components.
 * 
 * Usage:
 *   import { useAuthContext } from '@/context/AuthContext';
 *   
 *   const { user, login, logout } = useAuthContext();
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import type { PatientProfile, LoginRequest, SignupRequest, CompletePasswordRequest } from '../api/types';

// =============================================================================
// Types
// =============================================================================

interface AuthContextValue {
  // State
  isAuthenticated: boolean;
  isLoading: boolean;
  user: PatientProfile | null;
  error: string | null;
  needsPasswordChange: boolean;
  session: string | null;
  
  // Methods
  login: (credentials: LoginRequest) => Promise<boolean>;
  signup: (data: SignupRequest) => Promise<boolean>;
  completeNewPassword: (data: CompletePasswordRequest) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

// =============================================================================
// Context
// =============================================================================

const AuthContext = createContext<AuthContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const auth = useAuth();

  return (
    <AuthContext.Provider value={auth}>
      {children}
    </AuthContext.Provider>
  );
};

// =============================================================================
// Hook
// =============================================================================

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);
  
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  
  return context;
}

// =============================================================================
// Higher-Order Component
// =============================================================================

export function withAuth<P extends object>(
  Component: React.ComponentType<P & { auth: AuthContextValue }>
): React.FC<P> {
  return function WithAuthComponent(props: P) {
    const auth = useAuthContext();
    return <Component {...props} auth={auth} />;
  };
}

export default AuthContext;





