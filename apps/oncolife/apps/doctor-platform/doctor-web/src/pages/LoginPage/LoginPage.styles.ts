/**
 * OncoLife - Doctor Portal Login Page Styles
 * Brand: Clinical Navy + Medical Blue
 */

import styled from 'styled-components';

// Theme colors (Doctor)
const colors = {
  primary: '#1E3A5F',      // Clinical Navy
  primaryLight: '#2E5077',
  primaryDark: '#0F2942',
  secondary: '#2563EB',    // Medical Blue
  secondaryLight: '#3B82F6',
  background: '#F8FAFC',
  paper: '#FFFFFF',
  text: '#0F172A',
  textSecondary: '#475569',
  border: '#E2E8F0',
  error: '#EF4444',
  success: '#10B981',
  accent: '#0D9488',       // Teal accent
};

export const LoginContainer = styled.div`
  min-height: 100vh;
  display: flex;
  background: linear-gradient(135deg, ${colors.primary}05 0%, ${colors.secondary}05 100%);
  
  @media (max-width: 768px) {
    flex-direction: column;
  }
`;

export const BrandPanel = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px;
  background: linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%);
  color: white;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: -30%;
    right: -20%;
    width: 60%;
    height: 60%;
    background: radial-gradient(circle, ${colors.secondary}25 0%, transparent 70%);
    pointer-events: none;
  }
  
  &::after {
    content: '';
    position: absolute;
    bottom: -20%;
    left: -20%;
    width: 60%;
    height: 60%;
    background: radial-gradient(circle, ${colors.accent}15 0%, transparent 60%);
    pointer-events: none;
  }
  
  @media (max-width: 768px) {
    flex: 0;
    padding: 32px 24px;
    min-height: 180px;
  }
`;

export const BrandContent = styled.div`
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 400px;
`;

export const LogoContainer = styled.div`
  width: 72px;
  height: 72px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  
  svg {
    color: white;
  }
  
  @media (max-width: 768px) {
    width: 56px;
    height: 56px;
    margin-bottom: 12px;
  }
`;

export const BrandTitle = styled.h1`
  font-size: 2.25rem;
  font-weight: 700;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
  
  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`;

export const BrandSubtitle = styled.p`
  font-size: 1rem;
  opacity: 0.85;
  margin: 0 0 24px 0;
  font-weight: 500;
  
  @media (max-width: 768px) {
    font-size: 0.875rem;
    margin-bottom: 0;
  }
`;

export const BrandTagline = styled.p`
  font-size: 0.875rem;
  opacity: 0.7;
  margin: 0;
  line-height: 1.5;
  
  @media (max-width: 768px) {
    display: none;
  }
`;

export const LoginPanel = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px 24px;
  background: ${colors.background};
  
  @media (max-width: 768px) {
    padding: 32px 20px;
    flex: 1;
  }
`;

export const LoginCard = styled.div`
  width: 100%;
  max-width: 400px;
  background: ${colors.paper};
  border-radius: 16px;
  padding: 36px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
  border: 1px solid ${colors.border};
  
  @media (max-width: 768px) {
    padding: 24px 20px;
    border-radius: 12px;
  }
`;

export const LoginTitle = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${colors.text};
  margin: 0 0 8px 0;
  text-align: center;
  
  @media (max-width: 768px) {
    font-size: 1.25rem;
  }
`;

export const LoginSubtitle = styled.p`
  font-size: 0.875rem;
  color: ${colors.textSecondary};
  margin: 0 0 28px 0;
  text-align: center;
  line-height: 1.5;
`;

export const FormGroup = styled.div`
  margin-bottom: 18px;
`;

export const FormLabel = styled.label`
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: ${colors.text};
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
`;

export const InputWrapper = styled.div`
  display: flex;
  align-items: center;
  background: ${colors.background};
  border-radius: 8px;
  padding: 4px 14px;
  border: 1px solid ${colors.border};
  transition: all 0.2s ease;
  
  &:focus-within {
    border-color: ${colors.secondary};
    background: white;
    box-shadow: 0 0 0 3px ${colors.secondary}15;
  }
`;

export const InputIcon = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${colors.textSecondary};
  margin-right: 10px;
`;

export const StyledInput = styled.input`
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.9375rem;
  padding: 12px 0;
  color: ${colors.text};
  font-family: 'Source Sans Pro', sans-serif;
  
  &::placeholder {
    color: ${colors.textSecondary};
    opacity: 0.6;
  }
`;

export const PasswordToggle = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: ${colors.textSecondary};
  transition: color 0.2s;
  
  &:hover {
    color: ${colors.secondary};
  }
`;

export const ForgotPasswordLink = styled.a`
  display: block;
  text-align: right;
  font-size: 0.8125rem;
  color: ${colors.secondary};
  text-decoration: none;
  margin-top: 6px;
  margin-bottom: 20px;
  font-weight: 500;
  cursor: pointer;
  
  &:hover {
    text-decoration: underline;
  }
`;

export const SubmitButton = styled.button`
  width: 100%;
  padding: 14px 24px;
  font-size: 0.9375rem;
  font-weight: 600;
  color: white;
  background: ${colors.primary};
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Source Sans Pro', sans-serif;
  
  &:hover {
    background: ${colors.primaryLight};
  }
  
  &:active {
    background: ${colors.primaryDark};
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
`;

export const ErrorMessage = styled.div`
  background: ${colors.error}08;
  border: 1px solid ${colors.error}25;
  color: ${colors.error};
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.8125rem;
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const SecureNotice = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid ${colors.border};
  font-size: 0.75rem;
  color: ${colors.textSecondary};
  
  svg {
    color: ${colors.accent};
  }
`;

export const Footer = styled.div`
  text-align: center;
  font-size: 0.6875rem;
  color: ${colors.textSecondary};
  margin-top: 24px;
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

// Legacy exports for backward compatibility
export const LoginHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 36px 36px 0 36px;
  flex-shrink: 0;
`;

export const TopRightText = styled.div`
  font-size: 1rem;
  color: #222;
  font-weight: 600;
  a {
    color: ${colors.secondary};
    text-decoration: underline;
    margin-left: 4px;
  }
`;

export const MainContent = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 36px;
`;

export const StyledForm = styled.form`
  width: 100%;
`;

export const ForgotPassword = styled.a`
  font-size: 0.95rem;
  color: ${colors.secondary};
  text-decoration: none;
  float: right;
  margin-top: 0.25rem;
  margin-bottom: 1.25rem;
  cursor: pointer;
`;

export const Divider = styled.div`
  display: flex;
  align-items: center;
  width: 100%;
  margin: 1.5rem 0 1rem 0;
  color: ${colors.textSecondary};
  font-size: 0.95rem;
  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: ${colors.border};
    margin: 0 12px;
  }
`;

export const SocialRow = styled.div`
  display: flex;
  justify-content: center;
  gap: 1.25rem;
  margin-top: 0.5rem;
`;

export const SocialIcon = styled.img`
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07);
  padding: 6px;
  cursor: pointer;
`;

export const StyledInputGroup = styled.div`
  display: flex;
  align-items: center;
  background: ${colors.background};
  border-radius: 8px;
  padding: 0.5rem 1rem;
  margin-bottom: 1.25rem;
  border: 1px solid ${colors.border};
  transition: all 0.2s;
  &:focus-within {
    border-color: ${colors.secondary};
    background: white;
  }
`;

export const EyeButton = styled.button`
  background: none;
  border: none;
  outline: none;
  cursor: pointer;
  color: ${colors.textSecondary};
  display: flex;
  align-items: center;
  font-size: 1.2rem;
  margin-left: 0.5rem;
  padding: 0;
`;

export const StyledButton = styled.button`
  width: 100%;
  background: ${colors.primary};
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.9rem 0;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;

  &:hover, &:focus {
    background: ${colors.primaryLight};
  }
`;
