import React, { useState } from 'react';
import { Form } from 'react-bootstrap';
import { Mail } from 'lucide-react';
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
        navigate('/reset-password');
      }
      if (result?.data?.user_status === 'CONFIRMED') {
        navigate('/chat');
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
      <Title>Welcome Back to OncoLife AI <span role="img" aria-label="wave">👋🏻</span></Title>
      <Subtitle>Please enter your details to sign in to your account</Subtitle>
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      <StyledForm onSubmit={handleSubmit}>
        <Form.Group className="mb-3" controlId="formEmail">
          <Form.Label>Email</Form.Label>
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
              onKeyDown={handleKeyDown}
            />
          </StyledInputGroup>
        </Form.Group>
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
          Sign In
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