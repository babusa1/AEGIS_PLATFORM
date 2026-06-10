import styled from 'styled-components';

export const InputGroup = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background-color: #ffffff;
  transition: border-color 0.2s ease;

  &:focus-within {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
`;

export const Input = styled.input`
  flex: 1;
  padding: 12px 16px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 16px;
  color: #1f2937;

  &::placeholder {
    color: #9ca3af;
  }
`;

export const InputIcon = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  color: #6b7280;
`;

export const EyeButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s ease;

  &:hover {
    color: #374151;
  }

  &:focus {
    outline: none;
    color: #3b82f6;
  }
`; 