/**
 * Onboarding Wizard Component
 * 
 * Multi-step onboarding flow for new patients:
 * 1. Password Reset (handled separately via Cognito)
 * 2. Acknowledgement - Medical disclaimer
 * 3. Terms & Privacy - Legal acceptance
 * 4. Reminder Setup - Notification preferences
 * 
 * The wizard tracks progress and prevents skipping steps.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { Check, ChevronRight, Shield, Bell, FileText, Lock } from 'lucide-react';
import { Background, WrapperStyle, Logo, Card } from '@oncolife/ui-components';
import logo from '../../assets/logo.png';
import { onboardingApi } from '../../api/services';
import type { OnboardingStatus } from '../../api/services';

// ============================================================================
// STYLED COMPONENTS
// ============================================================================

const WizardContainer = styled.div`
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
`;

const Header = styled.div`
  display: flex;
  justify-content: center;
  padding: 20px 0;
`;

const StepIndicator = styled.div`
  display: flex;
  justify-content: center;
  margin-bottom: 40px;
  gap: 8px;
`;

const Step = styled.div<{ active: boolean; completed: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  background: ${({ active, completed }) => 
    active ? '#6B46C1' : 
    completed ? '#22c55e' : 
    '#e5e7eb'};
  color: ${({ active, completed }) => 
    active || completed ? '#fff' : '#666'};
  font-size: 0.9rem;
  font-weight: ${({ active }) => active ? '600' : '400'};
  transition: all 0.3s ease;
  
  svg {
    width: 16px;
    height: 16px;
  }
`;

const StepDivider = styled.div`
  width: 30px;
  height: 2px;
  background: #e5e7eb;
  align-self: center;
`;

const StepContent = styled.div`
  animation: fadeIn 0.3s ease;
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const Title = styled.h1`
  font-size: 1.75rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
  text-align: center;
`;

const Subtitle = styled.p`
  font-size: 1rem;
  color: #6b7280;
  margin-bottom: 24px;
  text-align: center;
`;

const ContentCard = styled(Card)`
  padding: 32px;
  margin-bottom: 24px;
`;

const DisclaimerBox = styled.div`
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  padding: 16px;
  margin: 20px 0;
  
  h4 {
    color: #92400e;
    margin: 0 0 8px 0;
    font-size: 0.95rem;
  }
  
  p {
    color: #78350f;
    margin: 0;
    font-size: 0.9rem;
    line-height: 1.5;
  }
`;

const CheckboxGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 24px 0;
`;

const CheckboxLabel = styled.label`
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: #f3f4f6;
    border-color: #d1d5db;
  }
  
  input {
    width: 20px;
    height: 20px;
    accent-color: #6B46C1;
    cursor: pointer;
    flex-shrink: 0;
    margin-top: 2px;
  }
  
  span {
    font-size: 0.95rem;
    color: #374151;
    line-height: 1.5;
  }
`;

const ReminderOptions = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin: 20px 0;
`;

const ReminderOption = styled.button<{ selected: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  border: 2px solid ${({ selected }) => selected ? '#6B46C1' : '#e5e7eb'};
  border-radius: 12px;
  background: ${({ selected }) => selected ? '#f5f3ff' : '#fff'};
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: #6B46C1;
  }
  
  svg {
    color: ${({ selected }) => selected ? '#6B46C1' : '#9ca3af'};
  }
  
  span {
    font-size: 0.9rem;
    color: ${({ selected }) => selected ? '#6B46C1' : '#374151'};
    font-weight: ${({ selected }) => selected ? '600' : '400'};
  }
`;

const TimeInput = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  
  label {
    font-size: 0.95rem;
    color: #374151;
  }
  
  input {
    padding: 10px 16px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 1rem;
    
    &:focus {
      outline: none;
      border-color: #6B46C1;
      box-shadow: 0 0 0 3px rgba(107, 70, 193, 0.1);
    }
  }
`;

const ButtonGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
`;

const Button = styled.button<{ variant?: 'primary' | 'secondary' }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  
  ${({ variant }) => variant === 'primary' ? `
    background: #6B46C1;
    color: #fff;
    
    &:hover:not(:disabled) {
      background: #553c9a;
    }
    
    &:disabled {
      background: #d1d5db;
      cursor: not-allowed;
    }
  ` : `
    background: #fff;
    color: #374151;
    border: 1px solid #d1d5db;
    
    &:hover {
      background: #f9fafb;
    }
  `}
`;

const LoadingSpinner = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  
  &::after {
    content: '';
    width: 40px;
    height: 40px;
    border: 3px solid #e5e7eb;
    border-top-color: #6B46C1;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

const CompletionMessage = styled.div`
  text-align: center;
  padding: 40px;
  
  svg {
    width: 64px;
    height: 64px;
    color: #22c55e;
    margin-bottom: 20px;
  }
  
  h2 {
    color: #1f2937;
    margin-bottom: 12px;
  }
  
  p {
    color: #6b7280;
    margin-bottom: 24px;
  }
`;

// ============================================================================
// STEP DEFINITIONS
// ============================================================================

type OnboardingStepType = 'acknowledgement' | 'terms_privacy' | 'reminder_setup';

interface StepConfig {
  id: OnboardingStepType;
  label: string;
  icon: React.ReactNode;
}

const STEPS: StepConfig[] = [
  { id: 'acknowledgement', label: 'Acknowledge', icon: <Shield size={16} /> },
  { id: 'terms_privacy', label: 'Terms', icon: <FileText size={16} /> },
  { id: 'reminder_setup', label: 'Reminders', icon: <Bell size={16} /> },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const OnboardingWizard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [currentStep, setCurrentStep] = useState<OnboardingStepType>('acknowledgement');
  
  // Form state
  const [acknowledged, setAcknowledged] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [hipaaAcknowledged, setHipaaAcknowledged] = useState(false);
  const [reminderChannel, setReminderChannel] = useState<'email' | 'sms' | 'both'>('email');
  const [reminderTime, setReminderTime] = useState('09:00');
  
  // Fetch onboarding status on mount
  useEffect(() => {
    fetchStatus();
  }, []);
  
  const fetchStatus = async () => {
    try {
      const data = await onboardingApi.getOnboardingStatus();
      setStatus(data);
      
      // If already onboarded, redirect to chat
      if (data.is_onboarded) {
        navigate('/chat');
        return;
      }
      
      // Set current step based on status
      if (data.current_step) {
        // Map backend step names to our step IDs
        if (data.current_step === 'acknowledgement') {
          setCurrentStep('acknowledgement');
        } else if (data.current_step === 'terms_privacy') {
          setCurrentStep('terms_privacy');
        } else if (data.current_step === 'reminder_setup') {
          setCurrentStep('reminder_setup');
        }
      }
    } catch (error) {
      console.error('Failed to fetch onboarding status:', error);
      // On error, start from beginning
    } finally {
      setLoading(false);
    }
  };
  
  const handleAcknowledgement = async () => {
    if (!acknowledged) return;
    
    setSubmitting(true);
    try {
      const acknowledgementText = 
        "I understand that OncoLife is a symptom tracking tool and does not replace my care team or emergency services. In case of emergency, I will call 911.";
      
      await onboardingApi.completeAcknowledgementStep({
        acknowledged: true,
        acknowledgement_text: acknowledgementText,
      });
      
      setCurrentStep('terms_privacy');
    } catch (error) {
      console.error('Failed to complete acknowledgement:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };
  
  const handleTermsPrivacy = async () => {
    if (!termsAccepted || !privacyAccepted) return;
    
    setSubmitting(true);
    try {
      await onboardingApi.completeTermsStep({
        terms_accepted: true,
        privacy_accepted: true,
        hipaa_acknowledged: hipaaAcknowledged,
      });
      
      setCurrentStep('reminder_setup');
    } catch (error) {
      console.error('Failed to accept terms:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };
  
  const handleReminderSetup = async () => {
    setSubmitting(true);
    try {
      const result = await onboardingApi.completeReminderStep({
        channel: reminderChannel,
        reminder_time: reminderTime,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      
      if (result.is_onboarded) {
        // Show success message briefly, then redirect
        setTimeout(() => {
          navigate('/chat');
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to set reminders:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };
  
  const getStepIndex = (step: OnboardingStepType): number => {
    return STEPS.findIndex(s => s.id === step);
  };
  
  const isStepCompleted = (step: OnboardingStepType): boolean => {
    const currentIndex = getStepIndex(currentStep);
    const stepIndex = getStepIndex(step);
    return stepIndex < currentIndex;
  };
  
  if (loading) {
    return (
      <Background>
        <WrapperStyle>
          <Header>
            <Logo src={logo} alt="OncoLife" />
          </Header>
          <LoadingSpinner />
        </WrapperStyle>
      </Background>
    );
  }
  
  // Render completion state
  if (status?.is_onboarded) {
    return (
      <Background>
        <WrapperStyle>
          <Header>
            <Logo src={logo} alt="OncoLife" />
          </Header>
          <WizardContainer>
            <ContentCard>
              <CompletionMessage>
                <Check />
                <h2>You're All Set!</h2>
                <p>Redirecting you to the chat...</p>
              </CompletionMessage>
            </ContentCard>
          </WizardContainer>
        </WrapperStyle>
      </Background>
    );
  }
  
  return (
    <Background>
      <WrapperStyle>
        <Header>
          <Logo src={logo} alt="OncoLife" />
        </Header>
        
        <WizardContainer>
          {/* Step Indicator */}
          <StepIndicator>
            {STEPS.map((step, index) => (
              <React.Fragment key={step.id}>
                <Step 
                  active={currentStep === step.id} 
                  completed={isStepCompleted(step.id)}
                >
                  {isStepCompleted(step.id) ? <Check size={16} /> : step.icon}
                  {step.label}
                </Step>
                {index < STEPS.length - 1 && <StepDivider />}
              </React.Fragment>
            ))}
          </StepIndicator>
          
          {/* Step Content */}
          <StepContent>
            {/* STEP 1: Acknowledgement */}
            {currentStep === 'acknowledgement' && (
              <ContentCard>
                <Title>Important Health Information</Title>
                <Subtitle>Please read and acknowledge the following</Subtitle>
                
                <p style={{ lineHeight: 1.7, color: '#374151' }}>
                  Welcome to OncoLife. This application is designed to help you track your symptoms 
                  and communicate with your care team during your treatment journey.
                </p>
                
                <DisclaimerBox>
                  <h4>⚠️ Emergency Disclaimer</h4>
                  <p>
                    <strong>This app is NOT for emergencies.</strong> If you are experiencing 
                    a medical emergency, please call <strong>911</strong> immediately.
                  </p>
                </DisclaimerBox>
                
                <p style={{ lineHeight: 1.7, color: '#374151' }}>
                  OncoLife is a supplemental tool that helps you record and share how you're feeling 
                  with your healthcare providers. It does not provide medical diagnoses, treatment 
                  recommendations, or replace professional medical care.
                </p>
                
                <CheckboxGroup>
                  <CheckboxLabel>
                    <input 
                      type="checkbox" 
                      checked={acknowledged} 
                      onChange={(e) => setAcknowledged(e.target.checked)}
                    />
                    <span>
                      I understand that OncoLife is a symptom tracking tool and does not replace my 
                      care team or emergency services. In case of emergency, I will call 911.
                    </span>
                  </CheckboxLabel>
                </CheckboxGroup>
                
                <ButtonGroup>
                  <Button 
                    variant="primary" 
                    onClick={handleAcknowledgement}
                    disabled={!acknowledged || submitting}
                  >
                    {submitting ? 'Processing...' : 'Continue'}
                    <ChevronRight size={18} />
                  </Button>
                </ButtonGroup>
              </ContentCard>
            )}
            
            {/* STEP 2: Terms & Privacy */}
            {currentStep === 'terms_privacy' && (
              <ContentCard>
                <Title>Terms & Privacy</Title>
                <Subtitle>Please review and accept to continue</Subtitle>
                
                <p style={{ lineHeight: 1.7, color: '#374151', marginBottom: '20px' }}>
                  To use OncoLife, you must accept our Terms of Service and Privacy Policy. 
                  These documents explain how we collect, use, and protect your health information.
                </p>
                
                <CheckboxGroup>
                  <CheckboxLabel>
                    <input 
                      type="checkbox" 
                      checked={termsAccepted} 
                      onChange={(e) => setTermsAccepted(e.target.checked)}
                    />
                    <span>
                      I have read and accept the <a href="/terms" target="_blank" style={{ color: '#6B46C1' }}>Terms & Conditions</a>
                    </span>
                  </CheckboxLabel>
                  
                  <CheckboxLabel>
                    <input 
                      type="checkbox" 
                      checked={privacyAccepted} 
                      onChange={(e) => setPrivacyAccepted(e.target.checked)}
                    />
                    <span>
                      I have read and accept the <a href="/privacy" target="_blank" style={{ color: '#6B46C1' }}>Privacy Policy</a>
                    </span>
                  </CheckboxLabel>
                  
                  <CheckboxLabel>
                    <input 
                      type="checkbox" 
                      checked={hipaaAcknowledged} 
                      onChange={(e) => setHipaaAcknowledged(e.target.checked)}
                    />
                    <span>
                      I acknowledge the <a href="/hipaa" target="_blank" style={{ color: '#6B46C1' }}>HIPAA Notice</a> regarding 
                      my protected health information (PHI)
                    </span>
                  </CheckboxLabel>
                </CheckboxGroup>
                
                <ButtonGroup>
                  <Button 
                    variant="primary" 
                    onClick={handleTermsPrivacy}
                    disabled={!termsAccepted || !privacyAccepted || submitting}
                  >
                    {submitting ? 'Processing...' : 'Accept & Continue'}
                    <ChevronRight size={18} />
                  </Button>
                </ButtonGroup>
              </ContentCard>
            )}
            
            {/* STEP 3: Reminder Setup */}
            {currentStep === 'reminder_setup' && (
              <ContentCard>
                <Title>Set Your Reminders</Title>
                <Subtitle>Choose how and when you'd like to be reminded to check in</Subtitle>
                
                <p style={{ lineHeight: 1.7, color: '#374151', marginBottom: '24px' }}>
                  OncoLife can send you daily reminders to log how you're feeling. 
                  This helps you stay on track and ensures your care team has up-to-date information.
                </p>
                
                <h3 style={{ fontSize: '1rem', color: '#374151', marginBottom: '12px' }}>
                  How would you like to receive reminders?
                </h3>
                
                <ReminderOptions>
                  <ReminderOption 
                    selected={reminderChannel === 'email'}
                    onClick={() => setReminderChannel('email')}
                    type="button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="20" height="16" x="2" y="4" rx="2"/>
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
                    </svg>
                    <span>Email</span>
                  </ReminderOption>
                  
                  <ReminderOption 
                    selected={reminderChannel === 'sms'}
                    onClick={() => setReminderChannel('sms')}
                    type="button"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="14" height="20" x="5" y="2" rx="2" ry="2"/>
                      <path d="M12 18h.01"/>
                    </svg>
                    <span>Text Message</span>
                  </ReminderOption>
                  
                  <ReminderOption 
                    selected={reminderChannel === 'both'}
                    onClick={() => setReminderChannel('both')}
                    type="button"
                  >
                    <Bell size={24} />
                    <span>Both</span>
                  </ReminderOption>
                </ReminderOptions>
                
                <TimeInput>
                  <label htmlFor="reminder-time">Remind me at:</label>
                  <input 
                    id="reminder-time"
                    type="time" 
                    value={reminderTime}
                    onChange={(e) => setReminderTime(e.target.value)}
                  />
                </TimeInput>
                
                <ButtonGroup>
                  <Button 
                    variant="primary" 
                    onClick={handleReminderSetup}
                    disabled={submitting}
                  >
                    {submitting ? 'Completing Setup...' : 'Complete Setup'}
                    <Check size={18} />
                  </Button>
                </ButtonGroup>
              </ContentCard>
            )}
          </StepContent>
        </WizardContainer>
      </WrapperStyle>
    </Background>
  );
};

export default OnboardingWizard;





