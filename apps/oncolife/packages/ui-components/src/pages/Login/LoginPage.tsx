import React from 'react';
import { Link } from 'react-router-dom';
import Login from './Login';
import logo from '../../assets/logo.png';
import { Background, WrapperStyle, Logo } from '../../styles/GlobalStyles';
import {
  TopRightText,
  MainContent,
  Footer,
  LoginHeader,
} from './LoginPage.styles';

const LoginPage: React.FC = () => {
  return (
    <Background>
      <WrapperStyle>
        <LoginHeader>
          <Logo src={logo} alt="Logo" />
          <TopRightText>
            Don't you have an account? <Link to="/signup">Sign up</Link>
          </TopRightText>
        </LoginHeader>
        
        <MainContent>
          <Login />
        </MainContent>
        
        <Footer>© 2025 OncoLife - All Right Reserved</Footer>
      </WrapperStyle>
    </Background>
  );
};

export default LoginPage; 