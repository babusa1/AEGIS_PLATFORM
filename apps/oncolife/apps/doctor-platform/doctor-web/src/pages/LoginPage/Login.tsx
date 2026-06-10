import React, { useState } from 'react';
import { Mail, Lock } from 'lucide-react';
import { Card, Title, Subtitle, InputPassword } from '@oncolife/ui-components';
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
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { authenticateLogin } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setError(null);
    try {
      const result = await authenticateLogin(email, password);
      if (result?.data?.requiresPasswordChange) {
        // Doctor portal might have different password reset flow
        navigate('/reset-password');
      }
      if (result?.data?.user_status === 'CONFIRMED') {
        // Navigate to doctor dashboard instead of chat
        navigate('/dashboard');
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
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLogin();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleLogin();
    }
  };

  return (
    <Card>
      <Title>Welcome to OncoLife AI Doctor Portal <span role="img" aria-label="stethoscope">🩺</span></Title>
      <Subtitle>Please enter your credentials to access the doctor dashboard</Subtitle>
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
              placeholder="Doctor Email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </StyledInputGroup>
        </div>
        <InputPassword
          value={password}
          onChange={setPassword}
          className="mb-1"
          label="Password"
          placeholder="Password"
          onKeyDown={handleKeyDown}
        />
        <ForgotPassword href="#">Forgot Password?</ForgotPassword>
        <StyledButton variant="primary" type="submit">
          Sign In to Doctor Portal
        </StyledButton>
      </StyledForm>
      <Divider>Secure Doctor Access</Divider>
      <SocialRow>
        <SocialIcon src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/google/google-original.svg" alt="Google" />
      </SocialRow>
    </Card>
  );
};

export default Login;
