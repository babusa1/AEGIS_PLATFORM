import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Typography,
  Box
} from '@mui/material';
import { X, User, Mail, Calendar, Phone, Shield, Stethoscope, Building, Globe, Heart, Users } from 'lucide-react';
import styled from 'styled-components';
import { theme } from '@oncolife/ui-components';
import { useAddPatient, type Patient } from '../../../services/patients';

const StyledDialog = styled(Dialog)`
  .MuiDialog-paper {
    border-radius: 12px;
    min-width: 800px;
    max-width: 900px;
  }
`;

const DialogHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e0e0e0;
`;

const InputWithIcon = styled.div`
  position: relative;
  margin-bottom: 2rem !important;
  margin-top: 0 !important;
  
  .MuiInputBase-root {
    padding-left: 56px;
    border-radius: 8px;
  }
  
  .MuiInputLabel-root {
    left: 56px;
  }
  
  .MuiInputLabel-shrink {
    left: 0;
  }
`;

const InputIcon = styled.div`
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  color: ${theme.colors.gray[400]};
  z-index: 1;
  pointer-events: none;
`;

const SelectWithIcon = styled(FormControl)`
  margin-bottom: 2rem !important;
  margin-top: 0 !important;
  
  .MuiInputBase-root {
    border-radius: 8px;
  }
`;

const RaceLabel = styled.div`
  .MuiInputLabel-root {
    font-size: 0.875rem;
  }
  
  .race-subtitle {
    font-size: 0.75rem;
    color: ${theme.colors.gray[500]};
    margin-top: 2px;
  }
`;

interface AddPatientModalProps {
  open: boolean;
  onClose: () => void;
}

const AddPatientModal: React.FC<AddPatientModalProps> = ({ open, onClose }) => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    mrn: '',
    dateOfBirth: '',
    sex: '',
    race: '',
    phoneNumber: '',
    physician: '',
    diseaseType: '',
    associateClinic: '',
    treatmentType: ''
  });

  const addPatientMutation = useAddPatient();

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async () => {
    try {
      await addPatientMutation.mutateAsync(formData as Omit<Patient, 'id'>);
      onClose();
      setFormData({
        firstName: '',
        lastName: '',
        email: '',
        mrn: '',
        dateOfBirth: '',
        sex: '',
        race: '',
        phoneNumber: '',
        physician: '',
        diseaseType: '',
        associateClinic: '',
        treatmentType: ''
      });
    } catch (error) {
      console.error('Error adding patient:', error);
    }
  };

  const handleCancel = () => {
    onClose();
    setFormData({
      firstName: '',
      lastName: '',
      email: '',
      mrn: '',
      dateOfBirth: '',
      sex: '',
      race: '',
      phoneNumber: '',
      physician: '',
      diseaseType: '',
      associateClinic: '',
      treatmentType: ''
    });
  };

  return (
    <StyledDialog open={open} onClose={onClose} maxWidth="md" fullWidth>
              <DialogContent sx={{ padding: '2rem' }}>
        <DialogHeader>
          <div>
            <Typography variant="h5" component="h2" fontWeight={600} gutterBottom>
              Add Patient
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Please enter Patient's detail
            </Typography>
          </div>
          <IconButton onClick={onClose} size="small">
            <X size={20} />
          </IconButton>
        </DialogHeader>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <InputWithIcon>
            <InputIcon>
              <User size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="First Name"
              placeholder="First Name"
              value={formData.firstName}
              onChange={(e) => handleInputChange('firstName', e.target.value)}
            />
          </InputWithIcon>

          <InputWithIcon>
            <InputIcon>
              <User size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Last Name"
              placeholder="Last Name"
              value={formData.lastName}
              onChange={(e) => handleInputChange('lastName', e.target.value)}
            />
          </InputWithIcon>

          <InputWithIcon>
            <InputIcon>
              <Mail size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Email"
              placeholder="Patient's Email"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
            />
          </InputWithIcon>

          <InputWithIcon>
            <InputIcon>
              <Calendar size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Date of birth"
              placeholder="DOB"
              value={formData.dateOfBirth}
              onChange={(e) => handleInputChange('dateOfBirth', e.target.value)}
            />
          </InputWithIcon>

          <SelectWithIcon fullWidth>
            <InputLabel>Sex Assigned at birth</InputLabel>
            <Select
              value={formData.sex}
              onChange={(e) => handleInputChange('sex', e.target.value)}
              label="Sex Assigned at birth"
            >
              <MenuItem value="Male">Male</MenuItem>
              <MenuItem value="Female">Female</MenuItem>
              <MenuItem value="Other">Other</MenuItem>
            </Select>
          </SelectWithIcon>

          <SelectWithIcon fullWidth>
            <InputLabel>Race</InputLabel>
            <Select
              value={formData.race}
              onChange={(e) => handleInputChange('race', e.target.value)}
              label="Race"
            >
              <MenuItem value="">Select</MenuItem>
              <MenuItem value="White">White</MenuItem>
              <MenuItem value="Black">Black</MenuItem>
              <MenuItem value="Asian">Asian</MenuItem>
              <MenuItem value="Hispanic">Hispanic</MenuItem>
              <MenuItem value="Other">Other</MenuItem>
            </Select>
            <Typography variant="caption" className="race-subtitle">
              (Select the once that best applies)
            </Typography>
          </SelectWithIcon>

          {/* Row 4: Patient ID | Phone Number */}
          <InputWithIcon>
            <InputIcon>
              <Shield size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Patient ID (MRN)"
              placeholder="Patient ID"
              value={formData.mrn}
              onChange={(e) => handleInputChange('mrn', e.target.value)}
            />
          </InputWithIcon>

          <InputWithIcon>
            <InputIcon>
              <Phone size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Phone Number"
              placeholder="XXXX-XXX-XX"
              value={formData.phoneNumber}
              onChange={(e) => handleInputChange('phoneNumber', e.target.value)}
            />
          </InputWithIcon>

          {/* Row 5: Physician | Associate Clinic */}
          <SelectWithIcon fullWidth>
            <InputLabel>Physician</InputLabel>
            <Select
              value={formData.physician}
              onChange={(e) => handleInputChange('physician', e.target.value)}
              label="Physician"
            >
              <MenuItem value="">Select</MenuItem>
              <MenuItem value="Dr. Smith">Dr. Smith</MenuItem>
              <MenuItem value="Dr. Johnson">Dr. Johnson</MenuItem>
              <MenuItem value="Dr. Williams">Dr. Williams</MenuItem>
              <MenuItem value="Dr. Brown">Dr. Brown</MenuItem>
              <MenuItem value="Dr. Davis">Dr. Davis</MenuItem>
            </Select>
          </SelectWithIcon>

          <SelectWithIcon fullWidth>
            <InputLabel>Associate Clinic</InputLabel>
            <Select
              value={formData.associateClinic}
              onChange={(e) => handleInputChange('associateClinic', e.target.value)}
              label="Associate Clinic"
            >
              <MenuItem value="">Select</MenuItem>
              <MenuItem value="Oncology Center">Oncology Center</MenuItem>
              <MenuItem value="Pulmonary Clinic">Pulmonary Clinic</MenuItem>
              <MenuItem value="Gastroenterology">Gastroenterology</MenuItem>
              <MenuItem value="Urology Center">Urology Center</MenuItem>
              <MenuItem value="Gynecology">Gynecology</MenuItem>
            </Select>
          </SelectWithIcon>

          {/* Row 6: Disease Type | Treatment Type */}
          <InputWithIcon>
            <InputIcon>
              <Globe size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Patient Disease Type"
              placeholder="Disease Type"
              value={formData.diseaseType}
              onChange={(e) => handleInputChange('diseaseType', e.target.value)}
            />
          </InputWithIcon>

          <InputWithIcon>
            <InputIcon>
              <Heart size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Treatment Type"
              placeholder="Treatment Type"
              value={formData.treatmentType}
              onChange={(e) => handleInputChange('treatmentType', e.target.value)}
            />
          </InputWithIcon>
        </Box>
      </DialogContent>

      <DialogActions sx={{ padding: '1rem 2rem', gap: 1 }}>
        <Button
          variant="outlined"
          onClick={handleCancel}
          sx={{
            borderColor: theme.colors.primary,
            color: theme.colors.primary,
            '&:hover': {
              borderColor: '#0056b3',
              backgroundColor: 'rgba(0, 123, 255, 0.04)',
            }
          }}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={addPatientMutation.isPending}
          sx={{
            backgroundColor: theme.colors.primary,
            '&:hover': {
              backgroundColor: '#0056b3',
            }
          }}
        >
          {addPatientMutation.isPending ? 'Saving...' : 'Save'}
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};

export default AddPatientModal; 