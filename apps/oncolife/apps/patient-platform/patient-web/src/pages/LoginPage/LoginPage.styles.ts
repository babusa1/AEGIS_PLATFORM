/**
 * OncoLife Ruby - Patient Login Page Styles
 * Brand: Healing Teal + Soft Lavender
 */

import styled from 'styled-components';

// Theme colors (Patient)
const colors = {
  primary: '#00897B',      // Healing Teal
  primaryLight: '#4DB6AC',
  primaryDark: '#00695C',
  secondary: '#7E57C2',    // Soft Lavender
  secondaryLight: '#B388FF',
  background: '#F5F7FA',
  paper: '#FFFFFF',
  text: '#1E293B',
  textSecondary: '#64748B',
  border: '#E2E8F0',
  error: '#EF4444',
  success: '#10B981',
};

export const LoginContainer = styled.div`
  min-height: 100vh;
  display: flex;
  background: linear-gradient(135deg, ${colors.primary}08 0%, ${colors.secondary}08 100%);
  
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
    top: -50%;
    right: -50%;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle, ${colors.secondary}30 0%, transparent 70%);
    pointer-events: none;
  }
  
  &::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -30%;
    width: 80%;
    height: 80%;
    background: radial-gradient(circle, ${colors.primaryLight}20 0%, transparent 60%);
    pointer-events: none;
  }
  
  @media (max-width: 768px) {
    flex: 0;
    padding: 32px 24px;
    min-height: 200px;
  }
`;

export const BrandContent = styled.div`
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 400px;
`;

export const LogoContainer = styled.div`
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  font-size: 2.5rem;
  
  @media (max-width: 768px) {
    width: 64px;
    height: 64px;
    font-size: 2rem;
    margin-bottom: 16px;
  }
`;

export const BrandTitle = styled.h1`
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
  
  @media (max-width: 768px) {
    font-size: 1.75rem;
  }
`;

export const BrandSubtitle = styled.p`
  font-size: 1.125rem;
  opacity: 0.9;
  margin: 0 0 32px 0;
  font-weight: 500;
  
  @media (max-width: 768px) {
    font-size: 0.875rem;
    margin-bottom: 0;
  }
`;

export const BrandTagline = styled.p`
  font-size: 1rem;
  opacity: 0.8;
  margin: 0;
  font-style: italic;
  
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
  max-width: 420px;
  background: ${colors.paper};
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  
  @media (max-width: 768px) {
    padding: 28px 24px;
    border-radius: 20px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  }
`;

export const LoginTitle = styled.h2`
  font-size: 1.75rem;
  font-weight: 700;
  color: ${colors.text};
  margin: 0 0 8px 0;
  text-align: center;
  
  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`;

export const LoginSubtitle = styled.p`
  font-size: 0.875rem;
  color: ${colors.textSecondary};
  margin: 0 0 32px 0;
  text-align: center;
  line-height: 1.5;
  
  @media (max-width: 768px) {
    margin-bottom: 24px;
  }
`;

export const FormGroup = styled.div`
  margin-bottom: 20px;
`;

export const FormLabel = styled.label`
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: ${colors.text};
  margin-bottom: 8px;
`;

export const InputWrapper = styled.div`
  display: flex;
  align-items: center;
  background: ${colors.background};
  border-radius: 12px;
  padding: 4px 16px;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  
  &:focus-within {
    border-color: ${colors.primary};
    background: white;
    box-shadow: 0 0 0 4px ${colors.primary}15;
  }
`;

export const InputIcon = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${colors.textSecondary};
  margin-right: 12px;
`;

export const StyledInput = styled.input`
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 1rem;
  padding: 14px 0;
  color: ${colors.text};
  font-family: 'Source Sans Pro', sans-serif;
  
  &::placeholder {
    color: ${colors.textSecondary};
    opacity: 0.7;
  }
`;

export const PasswordToggle = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  color: ${colors.textSecondary};
  transition: color 0.2s;
  
  &:hover {
    color: ${colors.primary};
  }
`;

export const ForgotPasswordLink = styled.a`
  display: block;
  text-align: right;
  font-size: 0.875rem;
  color: ${colors.primary};
  text-decoration: none;
  margin-top: 8px;
  margin-bottom: 24px;
  font-weight: 500;
  cursor: pointer;
  
  &:hover {
    color: ${colors.primaryDark};
    text-decoration: underline;
  }
`;

export const SubmitButton = styled.button`
  width: 100%;
  padding: 16px 24px;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Source Sans Pro', sans-serif;
  box-shadow: 0 4px 12px ${colors.primary}40;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px ${colors.primary}50;
  }
  
  &:active {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
  }
`;

export const ErrorMessage = styled.div`
  background: ${colors.error}10;
  border: 1px solid ${colors.error}30;
  color: ${colors.error};
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 0.875rem;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const Divider = styled.div`
  display: flex;
  align-items: center;
  margin: 28px 0;
  color: ${colors.textSecondary};
  font-size: 0.875rem;
  
  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: ${colors.border};
  }
  
  span {
    padding: 0 16px;
  }
`;

export const SignUpLink = styled.div`
  text-align: center;
  font-size: 0.875rem;
  color: ${colors.textSecondary};
  margin-top: 24px;
  
  a {
    color: ${colors.primary};
    font-weight: 600;
    text-decoration: none;
    margin-left: 4px;
    
    &:hover {
      text-decoration: underline;
    }
  }
`;

export const Footer = styled.div`
  text-align: center;
  font-size: 0.75rem;
  color: ${colors.textSecondary};
  margin-top: 32px;
  opacity: 0.8;
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
  a {
    color: ${colors.primary};
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
  color: ${colors.primary};
  text-decoration: none;
  float: right;
  margin-top: 0.25rem;
  margin-bottom: 1.25rem;
  cursor: pointer;
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
  border-radius: 12px;
  padding: 0.5rem 1rem;
  margin-bottom: 1.25rem;
  border: 2px solid transparent;
  transition: all 0.2s;
  &:focus-within {
    border: 2px solid ${colors.primary};
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

export const StyledButton = styled.button<{ variant?: 'primary' | 'secondary' }>`
  width: 100%;
  background: ${({ variant }) => 
    variant === 'secondary' 
      ? colors.background 
      : `linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%)`
  };
  color: ${({ variant }) => variant === 'secondary' ? colors.text : '#fff'};
  border: ${({ variant }) => variant === 'secondary' ? `2px solid ${colors.border}` : 'none'};
  border-radius: 12px;
  padding: 0.9rem 0;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: ${({ variant }) => variant === 'secondary' ? 'none' : `0 4px 12px ${colors.primary}40`};
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;

  &:hover, &:focus {
    transform: translateY(-1px);
    box-shadow: ${({ variant }) => variant === 'secondary' ? `0 2px 8px rgba(0,0,0,0.1)` : `0 6px 20px ${colors.primary}50`};
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
  }
`;
