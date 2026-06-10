/**
 * Error Boundary Component
 * ========================
 * 
 * React Error Boundary for graceful error handling.
 * Catches JavaScript errors anywhere in the child component tree.
 * 
 * Features:
 * - Custom fallback UI
 * - Error logging
 * - Retry functionality
 * - Different error types (network, auth, generic)
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ApiClientError, NetworkError, AuthenticationError } from '../../api/client';
import './ErrorBoundary.css';

// =============================================================================
// Types
// =============================================================================

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onRetry?: () => void;
  showDetails?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorType: 'network' | 'auth' | 'api' | 'generic';
}

// =============================================================================
// Error Boundary Component
// =============================================================================

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorType: 'generic',
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Determine error type for appropriate UI
    let errorType: ErrorBoundaryState['errorType'] = 'generic';
    
    if (error instanceof NetworkError) {
      errorType = 'network';
    } else if (error instanceof AuthenticationError) {
      errorType = 'auth';
    } else if (error instanceof ApiClientError) {
      errorType = 'api';
    }

    return {
      hasError: true,
      error,
      errorType,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console (in production, send to error tracking service)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Call optional error handler
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorType: 'generic',
    });
    
    this.props.onRetry?.();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  handleLogin = () => {
    window.location.href = '/login';
  };

  render() {
    const { hasError, error, errorType } = this.state;
    const { children, fallback, showDetails } = this.props;

    if (hasError) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Render appropriate error UI based on error type
      return (
        <div className="error-boundary">
          <div className="error-boundary__content">
            {errorType === 'network' && (
              <>
                <div className="error-boundary__icon error-boundary__icon--network">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 1l22 22M8.59 8.59A2 2 0 0 0 12 12.41M5 12a7 7 0 0 1 1.41-4.24M1.77 7.77A10.93 10.93 0 0 1 5 5.5M12.91 2.91a10.93 10.93 0 0 1 8.32 4.86M19 12a7 7 0 0 0-1.41-4.24" />
                  </svg>
                </div>
                <h2 className="error-boundary__title">Connection Problem</h2>
                <p className="error-boundary__message">
                  We couldn't connect to our servers. Please check your internet connection and try again.
                </p>
              </>
            )}

            {errorType === 'auth' && (
              <>
                <div className="error-boundary__icon error-boundary__icon--auth">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <h2 className="error-boundary__title">Session Expired</h2>
                <p className="error-boundary__message">
                  Your session has expired. Please log in again to continue.
                </p>
              </>
            )}

            {errorType === 'api' && (
              <>
                <div className="error-boundary__icon error-boundary__icon--api">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
                <h2 className="error-boundary__title">Something Went Wrong</h2>
                <p className="error-boundary__message">
                  We encountered an issue processing your request. Please try again.
                </p>
              </>
            )}

            {errorType === 'generic' && (
              <>
                <div className="error-boundary__icon error-boundary__icon--generic">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <h2 className="error-boundary__title">Unexpected Error</h2>
                <p className="error-boundary__message">
                  Something unexpected happened. We're sorry for the inconvenience.
                </p>
              </>
            )}

            {showDetails && error && (
              <details className="error-boundary__details">
                <summary>Technical Details</summary>
                <pre>{error.message}</pre>
                {error instanceof ApiClientError && (
                  <pre>Status: {error.status}</pre>
                )}
              </details>
            )}

            <div className="error-boundary__actions">
              {errorType === 'auth' ? (
                <button 
                  className="error-boundary__button error-boundary__button--primary"
                  onClick={this.handleLogin}
                >
                  Log In
                </button>
              ) : (
                <button 
                  className="error-boundary__button error-boundary__button--primary"
                  onClick={this.handleRetry}
                >
                  Try Again
                </button>
              )}
              <button 
                className="error-boundary__button error-boundary__button--secondary"
                onClick={this.handleGoHome}
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

// =============================================================================
// Async Error Boundary (for Suspense)
// =============================================================================

interface AsyncBoundaryProps {
  children: ReactNode;
  loading?: ReactNode;
  error?: ReactNode;
}

export const AsyncBoundary: React.FC<AsyncBoundaryProps> = ({
  children,
  loading,
  error,
}) => {
  return (
    <ErrorBoundary fallback={error}>
      <React.Suspense fallback={loading || <DefaultLoader />}>
        {children}
      </React.Suspense>
    </ErrorBoundary>
  );
};

// =============================================================================
// Default Loader
// =============================================================================

const DefaultLoader: React.FC = () => (
  <div className="error-boundary__loader">
    <div className="error-boundary__spinner" />
    <p>Loading...</p>
  </div>
);

export default ErrorBoundary;





