/**
 * OncoLife Error Boundary Component
 * Gracefully handles React errors with branded styling
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import styled from 'styled-components';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

// Styled components
const ErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 48px 24px;
  text-align: center;
  background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
  border-radius: 16px;
  margin: 24px;
  
  @media (max-width: 576px) {
    padding: 32px 16px;
    margin: 16px;
    min-height: 300px;
  }
`;

const ErrorIcon = styled.div`
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
  
  svg {
    color: white;
  }
  
  @media (max-width: 576px) {
    width: 64px;
    height: 64px;
  }
`;

const ErrorTitle = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: #991B1B;
  margin: 0 0 12px 0;
  
  @media (max-width: 576px) {
    font-size: 1.25rem;
  }
`;

const ErrorMessage = styled.p`
  font-size: 1rem;
  color: #7F1D1D;
  margin: 0 0 24px 0;
  max-width: 500px;
  line-height: 1.6;
  
  @media (max-width: 576px) {
    font-size: 0.875rem;
  }
`;

const ErrorDetails = styled.details`
  width: 100%;
  max-width: 600px;
  text-align: left;
  margin-top: 16px;
  
  summary {
    font-size: 0.875rem;
    color: #B91C1C;
    cursor: pointer;
    padding: 8px;
    user-select: none;
    
    &:hover {
      text-decoration: underline;
    }
  }
`;

const ErrorStack = styled.pre`
  background: #1E293B;
  color: #F1F5F9;
  padding: 16px;
  border-radius: 8px;
  font-size: 0.75rem;
  overflow-x: auto;
  margin-top: 8px;
  max-height: 200px;
  
  @media (max-width: 576px) {
    font-size: 0.625rem;
  }
`;

const RetryButton = styled.button`
  padding: 14px 32px;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
  }
  
  &:active {
    transform: translateY(0);
  }
`;

const HomeLink = styled.a`
  margin-top: 16px;
  font-size: 0.875rem;
  color: #B91C1C;
  text-decoration: none;
  
  &:hover {
    text-decoration: underline;
  }
`;

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorContainer>
          <ErrorIcon>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </ErrorIcon>
          
          <ErrorTitle>Something went wrong</ErrorTitle>
          <ErrorMessage>
            We're sorry, but something unexpected happened. Please try again or return to the home page.
          </ErrorMessage>
          
          <RetryButton onClick={this.handleRetry}>
            Try Again
          </RetryButton>
          
          <HomeLink href="/">
            Return to Home
          </HomeLink>
          
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <ErrorDetails>
              <summary>Error Details (Development Only)</summary>
              <ErrorStack>
                {this.state.error.toString()}
                {'\n\n'}
                {this.state.error.stack}
              </ErrorStack>
            </ErrorDetails>
          )}
        </ErrorContainer>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;



