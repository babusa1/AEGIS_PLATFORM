import logo from '../../assets/logo.png';
import React, { useState } from 'react';
import { Background, WrapperStyle, Logo, Card } from '@oncolife/ui-components';
import { MainContent, StyledButton, LoginTitle, LoginHeader } from './LoginPage.styles';
import { useNavigate } from 'react-router-dom';
import { patientService } from '../../services/patient';

const Acknowledgement: React.FC<{ onAgree?: () => void }> = ({ onAgree }) => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const handleAgree = async () => {
    try {
      setSubmitting(true);
      await patientService.updateConsent();
      onAgree?.();
      navigate('/chat');
    } catch (error) {
      console.error('Failed to update consent acknowledgement:', error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Background>
        <WrapperStyle>
            <LoginHeader>
                <Logo src={logo} alt="Logo" />
            </LoginHeader>
            <MainContent>
                <Card width="720px">
                    <LoginTitle>Acknowledgement</LoginTitle>
                    <p>Dear OncoLife AI User,</p>
                    <p>
                        Welcome to OncoLife. This chatbot is designed to track patient feedback for patient-reported outcomes. We appreciate your commitment to improving your health and well-being through our personalized healthcare solutions. Do not put in any information that you do not want to share.
                    </p>
                    <p style={{ fontWeight: 'bold' }}>Emergency and Medical Advice Disclaimer</p>
                    <p>
                        <b>Emergency Situations:</b> This chatbot is not a substitute for professional medical advice, diagnosis, or treatment. In case of a medical emergency, call 911 or your local emergency number immediately.
                    </p>
                    <p>
                        <b>Severe but Non-Emergent Issues:</b> For severe but non-emergent issues, please contact your healthcare provider as soon as possible.
                    </p>
                    <p>
                        <b>No Medical Advice:</b> This chatbot does not dispense medical advice. Always seek the advice of your physician or other qualified health providers with any questions you may have regarding a medical condition.
                    </p>
                    <p>
                        Please review the terms and conditions carefully before proceeding. By clicking 'I agree' below, you understand the limitations of the chatbot and agree to use it as intended. We are dedicated to ensuring the confidentiality and security of your information.<br /><br />
                        Sincerely,<br />
                        The OncoLife AI Team
                    </p>
                    <StyledButton variant="primary" type="button" onClick={handleAgree} disabled={submitting}>
                        {submitting ? 'Processing...' : 'I Agree'}
                    </StyledButton>
                </Card>
            </MainContent>
        </WrapperStyle>
    </Background>
  );
};

export default Acknowledgement;
