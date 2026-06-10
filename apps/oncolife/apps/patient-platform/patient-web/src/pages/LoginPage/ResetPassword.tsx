import logo from '../../assets/logo.png';
import React, { useState} from 'react';
import { Background, WrapperStyle, Header, Logo, Card, Title, Subtitle, InputPassword } from '@oncolife/ui-components';
import { MainContent, StyledButton } from './LoginPage.styles';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Check, X } from 'lucide-react';
import styled from 'styled-components';

const passwordRules = [
  {
    label: 'Contains at least 1 number',
    test: (pw: string) => /\d/.test(pw),
  },
  {
    label: 'Contains at least 1 special character',
    test: (pw: string) => /[!@#$%^&*(),.?":{}|<>]/.test(pw),
  },
  {
    label: 'Contains at least 1 uppercase letter',
    test: (pw: string) => /[A-Z]/.test(pw),
  },
  {
    label: 'Contains at least 1 lowercase letter',
    test: (pw: string) => /[a-z]/.test(pw),
  },
  {
    label: 'Minimum of 8 characters long',
    test: (pw: string) => pw.length >= 8,
  },
];

const RuleList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0 0 16px 0;
`;
const RuleItem = styled.li<{ status: 'gray' | 'green' | 'red' }>`
  display: flex;
  align-items: center;
  color: ${({ status }) =>
    status === 'green' ? '#22c55e' : status === 'red' ? '#ef4444' : '#888'};
  font-size: 0.97rem;
  margin-bottom: 4px;
  svg {
    margin-right: 8px;
  }
`;

const ResetPassword: React.FC = () => {
    const [resetPassword, setResetPassword] = useState<string>('');
    const { completeNewPassword, user } = useAuth();
    const navigate = useNavigate();
    const [touched, setTouched] = useState(false);

    const handleResetPassword = async () => {
      if (user?.email) {
        await completeNewPassword(user.email, resetPassword);
        navigate('/acknowledgement');
      }
    };

  return (
    <Background>
      <WrapperStyle>
        <Header>
            <Logo src={logo} alt="Logo" />
        </Header>
        <MainContent>
            <Card> 
                <Title>New Password</Title>
                <Subtitle>Please enter your new password</Subtitle>
                <div
  style={{ marginBottom: '10px', width: '100%' }}
  onBlur={() => setTouched(true)}
  tabIndex={-1}
>
  <InputPassword
    value={resetPassword}
    onChange={val => {
      setResetPassword(val);
      if (!touched) setTouched(true);
    }}
    className="mb-1"
    label="New Password"
    placeholder="New Password"
  />
  <div style={{ paddingTop: 16 }}>
    <RuleList>
      {passwordRules.map((rule) => {
        const valid = rule.test(resetPassword);
        let status: 'gray' | 'green' | 'red' = 'gray';
        if (resetPassword.length > 0) {
          status = valid ? 'green' : touched ? 'red' : 'gray';
        }
        return (
          <RuleItem key={rule.label} status={status}>
            {status === 'green' && <Check size={18} />}
            {status === 'red' && <X size={18} />}
            {status === 'gray' && <span style={{ width: 18, display: 'inline-block' }} />}
            {rule.label}
          </RuleItem>
        );
      })}
    </RuleList>
  </div>
</div>

                <StyledButton variant="primary" type="button" onClick={handleResetPassword}>
                    Reset Password
                </StyledButton>
            </Card>
        </MainContent>
      </WrapperStyle>
    </Background>
  );
};

export default ResetPassword;