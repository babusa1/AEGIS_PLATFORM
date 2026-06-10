import React from 'react';
import styled from 'styled-components';
import {
  InputGroup,
  InputLabel,
  InputField,
  SectionTitle,
  SaveButton,
  CancelButton,
  ButtonGroup,
} from '../ProfilePage.styles';
import type { ProfileFormData } from '../types';

interface PersonalInformationProps {
  formData: ProfileFormData;
  isEditing: boolean;
  onFieldChange: (field: keyof ProfileFormData, value: string | number | null) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving?: boolean;
}

const GridContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  align-items: center;
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const SectionDivider = styled.div`
  grid-column: 1 / -1;
  border-top: 2px solid #e0e0e0;
  margin: 1.5rem 0;
`;

const TreatmentSection = styled.div`
  grid-column: 1 / -1;
  background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
  border-radius: 12px;
  padding: 1.5rem;
  margin-top: 1rem;
  border: 1px solid #c8e6c9;
`;

const TreatmentTitle = styled.h3`
  color: #2e7d32;
  font-size: 1.1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  &::before {
    content: '💉';
  }
`;

const TreatmentGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const EmergencySection = styled.div`
  grid-column: 1 / -1;
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-radius: 12px;
  padding: 1.5rem;
  margin-top: 1rem;
  border: 1px solid #ffcc80;
`;

const EmergencyTitle = styled.h3`
  color: #e65100;
  font-size: 1.1rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  &::before {
    content: '🚨';
  }
`;

const PersonalInformation: React.FC<PersonalInformationProps> = ({
  formData,
  isEditing,
  onFieldChange,
  onSave,
  onCancel,
  isSaving = false,
}) => {
  const handleInputChange = (field: keyof ProfileFormData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    onFieldChange(field, e.target.value || null);
  };

  return (
    <div>
      <SectionTitle>Personal Information</SectionTitle>
      <GridContainer>
        <InputGroup>
          <InputLabel>First Name</InputLabel>
          <InputField
            type="text"
            value={formData.first_name || ''}
            onChange={handleInputChange('first_name')}
            disabled={!isEditing}
            isEditing={isEditing}
          />
        </InputGroup>
        <InputGroup>
          <InputLabel>Last Name</InputLabel>
          <InputField
            type="text"
            value={formData.last_name || ''}
            onChange={handleInputChange('last_name')}
            disabled={!isEditing}
            isEditing={isEditing}
          />
        </InputGroup>
        <InputGroup>
          <InputLabel>Email</InputLabel>
          <InputField
            type="email"
            value={formData.email_address || ''}
            onChange={handleInputChange('email_address')}
            disabled={!isEditing}
            isEditing={isEditing}
          />
        </InputGroup>
        <InputGroup>
          <InputLabel>Phone Number</InputLabel>
          <InputField
            type="tel"
            value={formData.phone_number || ''}
            onChange={handleInputChange('phone_number')}
            disabled={!isEditing}
            isEditing={isEditing}
          />
        </InputGroup>
        <InputGroup>
          <InputLabel>Date of Birth</InputLabel>
          <InputField
            type="date"
            value={formData.date_of_birth || ''}
            onChange={handleInputChange('date_of_birth')}
            disabled={!isEditing}
            isEditing={isEditing}
          />
        </InputGroup>
        <InputGroup>
          <InputLabel>Reminder Time</InputLabel>
          <InputField
            type="time"
            value={formData.reminder_time || ''}
            onChange={handleInputChange('reminder_time')}
            disabled={!isEditing}
            isEditing={isEditing}
          />
        </InputGroup>
        
        {/* Treatment Information Section */}
        <TreatmentSection>
          <TreatmentTitle>Treatment Information</TreatmentTitle>
          <TreatmentGrid>
            <InputGroup>
              <InputLabel>Last Chemotherapy Date</InputLabel>
              <InputField
                type="date"
                value={formData.last_chemo_date || ''}
                onChange={handleInputChange('last_chemo_date')}
                disabled={!isEditing}
                isEditing={isEditing}
                placeholder="Select date"
              />
            </InputGroup>
            <InputGroup>
              <InputLabel>Next Physician Visit</InputLabel>
              <InputField
                type="date"
                value={formData.next_physician_visit || ''}
                onChange={handleInputChange('next_physician_visit')}
                disabled={!isEditing}
                isEditing={isEditing}
                placeholder="Select date"
              />
            </InputGroup>
            <InputGroup>
              <InputLabel>Diagnosis</InputLabel>
              <InputField
                type="text"
                value={formData.diagnosis || ''}
                onChange={handleInputChange('diagnosis')}
                disabled={!isEditing}
                isEditing={isEditing}
                placeholder="e.g., Breast Cancer Stage II"
              />
            </InputGroup>
            <InputGroup>
              <InputLabel>Treatment Type</InputLabel>
              <InputField
                type="text"
                value={formData.treatment_type || ''}
                onChange={handleInputChange('treatment_type')}
                disabled={!isEditing}
                isEditing={isEditing}
                placeholder="e.g., Chemotherapy, Radiation"
              />
            </InputGroup>
            <InputGroup>
              <InputLabel>Doctor Name</InputLabel>
              <InputField
                type="text"
                value={formData.doctor_name || ''}
                onChange={handleInputChange('doctor_name')}
                disabled={!isEditing}
                isEditing={isEditing}
              />
            </InputGroup>
            <InputGroup>
              <InputLabel>Clinic Name</InputLabel>
              <InputField
                type="text"
                value={formData.clinic_name || ''}
                onChange={handleInputChange('clinic_name')}
                disabled={!isEditing}
                isEditing={isEditing}
              />
            </InputGroup>
          </TreatmentGrid>
        </TreatmentSection>
        
        {/* Emergency Contact Section */}
        <EmergencySection>
          <EmergencyTitle>Emergency Contact</EmergencyTitle>
          <TreatmentGrid>
            <InputGroup>
              <InputLabel>Contact Name</InputLabel>
              <InputField
                type="text"
                value={formData.emergency_contact_name || ''}
                onChange={handleInputChange('emergency_contact_name')}
                disabled={!isEditing}
                isEditing={isEditing}
                placeholder="Full name"
              />
            </InputGroup>
            <InputGroup>
              <InputLabel>Contact Phone</InputLabel>
              <InputField
                type="tel"
                value={formData.emergency_contact_phone || ''}
                onChange={handleInputChange('emergency_contact_phone')}
                disabled={!isEditing}
                isEditing={isEditing}
                placeholder="Phone number"
              />
            </InputGroup>
          </TreatmentGrid>
        </EmergencySection>
      </GridContainer>
      
      {isEditing && (
        <ButtonGroup>
          <SaveButton onClick={onSave} disabled={isSaving}>
            {isSaving ? '⏳ Saving...' : '💾 Save Changes'}
          </SaveButton>
          <CancelButton onClick={onCancel} disabled={isSaving}>
            Cancel
          </CancelButton>
        </ButtonGroup>
      )}
    </div>
  );
};

export default PersonalInformation; 