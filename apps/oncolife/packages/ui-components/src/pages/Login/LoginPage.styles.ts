import styled from 'styled-components';
import { Form, Button } from 'react-bootstrap';

export const LoginTitle = styled.h2`
  font-size: 1.6rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
  text-align: center;
`;

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
    color: #222;
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

export const StyledForm = styled(Form)`
  width: 100%;
`;

export const ForgotPassword = styled.a`
  font-size: 0.95rem;
  color: #4d7cfe;
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
  color: #bbb;
  font-size: 0.95rem;
  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e0e0e0;
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

export const Footer = styled.div`
  padding: 0 36px 24px 36px;
  font-size: 0.95rem;
  color: #222;
  opacity: 0.7;
  flex-shrink: 0;
`;

export const StyledInputGroup = styled.div`
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  padding: 0.5rem 1rem;
  margin-bottom: 1.25rem;
  border: 2px solid transparent;
  transition: border 0.2s;
  &:focus-within {
    border: 2px solid #4d7cfe;
  }
`;

export const StyledInput = styled.input`
  border: none;
  outline: none;
  background: transparent;
  flex: 1;
  font-size: 1.1rem;
  padding: 0.75rem 0.5rem;
  color: #222;
  &::placeholder {
    color: #bbb;
    opacity: 1;
  }
`;

export const InputIcon = styled.span`
  display: flex;
  align-items: center;
  color: #888;
  margin-right: 0.75rem;
  font-size: 1.2rem;
`;

export const EyeButton = styled.button`
  background: none;
  border: none;
  outline: none;
  cursor: pointer;
  color: #888;
  display: flex;
  align-items: center;
  font-size: 1.2rem;
  margin-left: 0.5rem;
  padding: 0;
`;

export const StyledButton = styled(Button)`
  width: 100%;
  background: #4d97fe;
  color: #fff;
  border: none;
  border-radius: 16px;
  padding: 0.9rem 0;
  font-size: 1.25rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  outline: none;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;

  &:hover, &:focus {
    background: #357ae8;
    color: #fff;
  }
`; 