import styled from 'styled-components';

interface DatePickerContainerProps {
  $fullWidth?: boolean;
}

interface DateDisplayButtonProps {
  $fullWidth?: boolean;
}

export const DatePickerContainer = styled.div<DatePickerContainerProps>`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: ${props => props.$fullWidth ? '100%' : 'auto'};
  
  .MuiTextField-root {
    min-width: 200px;
    width: ${props => props.$fullWidth ? '100%' : 'auto'};
  }
  
  .MuiInputBase-root {
    background-color: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    width: ${props => props.$fullWidth ? '100%' : 'auto'};
  }
  
  .MuiOutlinedInput-root {
    &:hover .MuiOutlinedInput-notchedOutline {
      border-color: #007BFF;
    }
    
    &.Mui-focused .MuiOutlinedInput-notchedOutline {
      border-color: #007BFF;
      border-width: 2px;
    }
  }
`;

export const DateDisplayButton = styled.button<DateDisplayButtonProps>`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 8px 16px;
  height: 40px;
  min-width: 200px;
  width: ${props => props.$fullWidth ? '100%' : 'auto'};
  justify-content: space-between;
  border: 1px solid #DEE2E6;
  background-color: #FFFFFF;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #495057;
  font-weight: 500;
  
  &:hover {
    background-color: #F8F9FA;
    border-color: #007BFF;
    color: #007BFF;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 123, 255, 0.15);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  span {
    font-size: 1.1rem;
  }
  
  svg {
    width: 16px;
    height: 16px;
  }
`; 