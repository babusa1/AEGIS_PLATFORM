/**
 * OncoLife Ruby - Profile Page Styles
 * Responsive, themed design for patient profile management
 */

import styled from "styled-components";

// Theme colors (Patient)
const colors = {
  primary: '#00897B',
  primaryLight: '#4DB6AC',
  primaryDark: '#00695C',
  secondary: '#7E57C2',
  background: '#F5F7FA',
  paper: '#FFFFFF',
  text: '#1E293B',
  textSecondary: '#64748B',
  border: '#E2E8F0',
  success: '#10B981',
  error: '#EF4444',
};

export const ProfileContainer = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background-color: ${colors.background};
`;

export const ProfileHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(135deg, ${colors.primary} 0%, ${colors.primaryDark} 100%);
  color: white;
  
  @media (max-width: 576px) {
    padding: 16px;
  }
`;

export const ProfileTitle = styled.h1`
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  
  @media (max-width: 576px) {
    font-size: 1.25rem;
  }
`;

export const ProfileContent = styled.div`
  padding: 24px;
  flex: 1;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  
  @media (max-width: 768px) {
    padding: 16px;
  }
`;

export const ProfileCard = styled.div`
  background-color: ${colors.paper};
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  
  @media (max-width: 576px) {
    border-radius: 12px;
  }
`;

export const ProfileInfoHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  background: linear-gradient(135deg, ${colors.primary}10 0%, ${colors.secondary}10 100%);
  border-bottom: 1px solid ${colors.border};
  
  @media (max-width: 576px) {
    flex-direction: column;
    text-align: center;
    padding: 20px 16px;
  }
`;

export const ProfileImageContainer = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
`;

export const ProfileImage = styled.div<{ imageUrl?: string }>`
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background-image: ${props => props.imageUrl 
    ? `url(${props.imageUrl})` 
    : `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`};
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 2rem;
  font-weight: 600;
  border: 4px solid ${colors.paper};
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  
  @media (max-width: 576px) {
    width: 72px;
    height: 72px;
    font-size: 1.5rem;
  }
`;

export const EditImageButton = styled.button`
  position: absolute;
  bottom: 0;
  right: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: ${colors.primary};
  border: 3px solid ${colors.paper};
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  
  &:hover {
    background: ${colors.primaryDark};
    transform: scale(1.05);
  }
  
  svg {
    width: 14px;
    height: 14px;
  }
`;

export const ProfileInfo = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  
  @media (max-width: 576px) {
    align-items: center;
  }
`;

export const ProfileName = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: ${colors.text};
  margin: 0;
  
  @media (max-width: 576px) {
    font-size: 1.25rem;
  }
`;

export const ProfileEmail = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  color: ${colors.textSecondary};
  font-size: 0.9375rem;
  
  svg {
    width: 16px;
    height: 16px;
    color: ${colors.primary};
  }
`;

export const EditProfileButton = styled.button`
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  font-weight: 600;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px ${colors.primary}40;
  
  &:hover {
    background: ${colors.primaryDark};
    transform: translateY(-1px);
    box-shadow: 0 4px 12px ${colors.primary}50;
  }
  
  &:active {
    transform: translateY(0);
  }
  
  @media (max-width: 576px) {
    width: 100%;
    justify-content: center;
    margin-top: 12px;
  }
`;

export const SectionTitle = styled.h3`
  font-size: 1rem;
  font-weight: 600;
  color: ${colors.textSecondary};
  margin: 0 0 20px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: ${colors.border};
    margin-left: 16px;
  }
`;

export const InformationGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  padding: 24px;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    padding: 20px 16px;
  }
`;

export const InformationColumn = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

export const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

export const InputLabel = styled.label`
  font-size: 0.8125rem;
  font-weight: 600;
  color: ${colors.textSecondary};
  text-transform: uppercase;
  letter-spacing: 0.03em;
`;

export const InputField = styled.input<{ isEditing?: boolean }>`
  padding: 12px 16px;
  border: 2px solid ${props => props.isEditing ? colors.primary : colors.border};
  border-radius: 10px;
  font-size: 1rem;
  color: ${colors.text};
  background-color: ${props => props.isEditing ? colors.paper : colors.background};
  transition: all 0.2s ease;
  font-family: 'Source Sans Pro', sans-serif;
  
  &:focus {
    outline: none;
    border-color: ${colors.primary};
    box-shadow: 0 0 0 4px ${colors.primary}15;
  }
  
  &:disabled {
    background-color: ${colors.background};
    color: ${colors.textSecondary};
    cursor: not-allowed;
  }
  
  &::placeholder {
    color: ${colors.textSecondary};
    opacity: 0.7;
  }
`;

export const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  gap: 16px;
  
  span {
    color: ${colors.textSecondary};
    font-size: 0.9375rem;
  }
`;

export const ErrorContainer = styled.div`
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  color: #991B1B;
  display: flex;
  align-items: center;
  gap: 12px;
  
  svg {
    flex-shrink: 0;
  }
`;

export const ButtonGroup = styled.div`
  display: flex;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid ${colors.border};
  background: ${colors.background};
  
  @media (max-width: 576px) {
    flex-direction: column;
    padding: 16px;
  }
`;

export const SaveButton = styled.button`
  background: linear-gradient(135deg, ${colors.success} 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 12px 28px;
  font-weight: 600;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px ${colors.success}40;
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px ${colors.success}50;
  }
  
  &:active {
    transform: translateY(0);
  }
  
  &:disabled {
    background: ${colors.textSecondary};
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  @media (max-width: 576px) {
    width: 100%;
    justify-content: center;
  }
`;

export const CancelButton = styled.button`
  background: ${colors.paper};
  color: ${colors.textSecondary};
  border: 2px solid ${colors.border};
  border-radius: 10px;
  padding: 12px 28px;
  font-weight: 600;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &:hover {
    background: ${colors.background};
    border-color: ${colors.textSecondary};
  }
  
  @media (max-width: 576px) {
    width: 100%;
    justify-content: center;
  }
`;
