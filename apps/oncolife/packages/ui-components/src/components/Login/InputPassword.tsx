import React, { useState } from 'react';
import { Form } from 'react-bootstrap';
import { Lock, Eye, EyeOff } from 'lucide-react';
import { InputGroup, Input, InputIcon, EyeButton } from './InputPassword.styles';

interface InputPasswordProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  className?: string;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}

const InputPassword: React.FC<InputPasswordProps> = ({
  label = 'Password',
  placeholder = 'Password',
  value,
  onChange,
  autoComplete = 'current-password',
  className,
  onKeyDown
}) => {
  const [showPassword, setShowPassword] = useState(false);

  const handleTogglePassword = () => setShowPassword((prev) => !prev);

  return (
    <Form.Group className={className} controlId="formPassword">
      <Form.Label>{label}</Form.Label>
      <InputGroup>
        <InputIcon>
          <Lock size={20} />
        </InputIcon>
        <Input
          type={showPassword ? "text" : "password"}
          placeholder={placeholder}
          autoComplete={autoComplete}
          value={value}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <EyeButton 
          type="button" 
          onClick={handleTogglePassword} 
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
        </EyeButton>
      </InputGroup>
    </Form.Group>
  );
};

export default InputPassword; 