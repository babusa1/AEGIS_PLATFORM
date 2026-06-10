/**
 * OncoLife Ruby - Patient Login Page
 * "Compassionate Care, Intelligent Triage"
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import {
  LoginContainer,
  BrandPanel,
  BrandContent,
  LogoContainer,
  BrandTitle,
  BrandSubtitle,
  BrandTagline,
  LoginPanel,
  LoginCard,
  LoginTitle,
  LoginSubtitle,
  FormGroup,
  FormLabel,
  InputWrapper,
  InputIcon,
  StyledInput,
  PasswordToggle,
  ForgotPasswordLink,
  SubmitButton,
  ErrorMessage,
  SignUpLink,
  Footer,
} from './LoginPage.styles';

// Check if demo mode should be shown
// Shows on: 1) Local dev (localhost), 2) When VITE_DEMO_MODE=true (e.g., Vercel demo)
const showDemoButton = 
  import.meta.env.VITE_DEMO_MODE === 'true' || 
  (import.meta.env.DEV && window.location.hostname === 'localhost');

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const { authenticateLogin } = useAuth();
  const navigate = useNavigate();

  // Dev mode auto-login function
  const handleDevLogin = () => {
    // Set a fake token for local development
    localStorage.setItem('authToken', 'dev-mode-token-11111111-1111-1111-1111-111111111111');
    navigate('/chat');
    window.location.reload(); // Refresh to pick up the new token
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const result = await authenticateLogin(email, password);
      if (result?.data?.requiresPasswordChange) {
        navigate('/reset-password');
      } else if (result?.data?.user_status === 'CONFIRMED') {
        navigate('/chat');
      }
    } catch (err: any) {
      let message = 'Unable to sign in. Please try again.';
      if (err.message === 'AUTHENTICATION_FAILED' || err.message === 'INVALID_CREDENTIALS') {
        message = 'Invalid email or password. Please check your credentials.';
      }
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <LoginContainer>
      {/* Left Brand Panel */}
      <BrandPanel>
        <BrandContent>
          <LogoContainer>💎</LogoContainer>
          <BrandTitle>OncoLife</BrandTitle>
          <BrandSubtitle>Ruby</BrandSubtitle>
          <BrandTagline>"Compassionate Care, Intelligent Triage"</BrandTagline>
        </BrandContent>
      </BrandPanel>

      {/* Right Login Panel */}
      <LoginPanel>
        <LoginCard>
          <LoginTitle>Welcome Back 👋</LoginTitle>
          <LoginSubtitle>
            Sign in to access your personalized symptom tracker and care resources
          </LoginSubtitle>

          {error && (
            <ErrorMessage>
              <AlertCircle size={18} />
              {error}
            </ErrorMessage>
          )}

          <form onSubmit={handleSubmit}>
            <FormGroup>
              <FormLabel htmlFor="email">Email Address</FormLabel>
              <InputWrapper>
                <InputIcon>
                  <Mail size={20} />
                </InputIcon>
                <StyledInput
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoComplete="email"
                  required
                />
              </InputWrapper>
            </FormGroup>

            <FormGroup>
              <FormLabel htmlFor="password">Password</FormLabel>
              <InputWrapper>
                <InputIcon>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                </InputIcon>
                <StyledInput
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoComplete="current-password"
                  required
                />
                <PasswordToggle
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </PasswordToggle>
              </InputWrapper>
            </FormGroup>

            <ForgotPasswordLink href="#">
              Forgot password?
            </ForgotPasswordLink>

            <SubmitButton type="submit" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </SubmitButton>
          </form>

          <SignUpLink>
            Don't have an account?
            <Link to="/signup">Sign up</Link>
          </SignUpLink>

          {/* Demo Mode Quick Login - Shows in local dev or when VITE_DEMO_MODE=true */}
          {showDemoButton && (
            <div style={{ 
              marginTop: '20px', 
              padding: '15px', 
              background: '#fff3cd', 
              borderRadius: '8px',
              border: '1px solid #ffc107'
            }}>
              <div style={{ fontSize: '14px', color: '#856404', marginBottom: '10px' }}>
                🛠️ <strong>Local Development Mode</strong>
              </div>
              <button
                onClick={handleDevLogin}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: 'bold'
                }}
              >
                🚀 Quick Dev Login (No Password)
              </button>
            </div>
          )}

          <Footer>
            © 2025 HealthAI - OncoLife. All rights reserved.
          </Footer>
        </LoginCard>
      </LoginPanel>
    </LoginContainer>
  );
};

export default LoginPage;
