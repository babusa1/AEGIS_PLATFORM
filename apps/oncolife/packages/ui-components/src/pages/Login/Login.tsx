import React, { useState } from 'react';
import { Mail, Lock } from 'lucide-react';
import { Card, Title, Subtitle } from '../../styles/GlobalStyles';
import {
  StyledForm,
  ForgotPassword,
  Divider,
  SocialRow,
  SocialIcon,
  StyledInputGroup,
  StyledInput,
  InputIcon,
  StyledButton
} from './LoginPage.styles';

interface LoginProps {
  onLogin?: (email: string, password: string) => Promise<void>;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    setError(null);
    setIsLoading(true);
    
    try {
      if (onLogin) {
        await onLogin(email, password);
      } else {
        // Default behavior - just log the attempt
        console.log('Login attempt:', { email });
      }
    } catch (err: any) {
      let message = 'Login failed';
      if (err.message === 'AUTHENTICATION_FAILED') {
        message = 'Failed Authentication';
      } else if (err.message === 'INVALID_CREDENTIALS') {
        message = 'Invalid Credentials';
      } else {
        message = 'Failed Authentication';
      }
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLogin();
  };

  return (
    <Card>
      <Title>Welcome Back to OncoLife AI <span role="img" aria-label="wave">👋🏻</span></Title>
      <Subtitle>Please enter your details to sign in to your account</Subtitle>
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <StyledForm onSubmit={handleSubmit}>
        <div className="mb-3">
          <label>Email</label>
          <StyledInputGroup>
            <InputIcon>
              <Mail size={20} />
            </InputIcon>
            <StyledInput
              type="email"
              placeholder="Your Email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </StyledInputGroup>
        </div>
        <div className="mb-1">
          <label>Password</label>
          <StyledInputGroup>
            <InputIcon>
              <Lock size={20} />
            </InputIcon>
            <StyledInput
              type="password"
              placeholder="Password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </StyledInputGroup>
        </div>
        <ForgotPassword href="#">Forgot Password?</ForgotPassword>
        <StyledButton variant="primary" type="submit" disabled={isLoading}>
          {isLoading ? 'Signing In...' : 'Sign In'}
        </StyledButton>
      </StyledForm>
      <Divider>Or continue with</Divider>
      <SocialRow>
        <SocialIcon src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/google/google-original.svg" alt="Google" />
      </SocialRow>
    </Card>
  );
};

export default Login; 