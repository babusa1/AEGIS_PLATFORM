import React, { useState, useEffect } from 'react';
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
import { X, User, Mail, Building, Stethoscope } from 'lucide-react';
import styled from 'styled-components';
import { theme } from '@oncolife/ui-components';
import { useUpdateStaff, type Staff, type UpdateStaffRequest } from '../../../../restful/staff';

const StyledDialog = styled(Dialog)`
  .MuiDialog-paper {
    border-radius: 12px;
    min-width: 600px;
    max-width: 700px;
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

interface EditStaffModalProps {
  open: boolean;
  onClose: () => void;
  staff: Staff | null;
}

const EditStaffModal: React.FC<EditStaffModalProps> = ({ open, onClose, staff }) => {
  const [formData, setFormData] = useState<UpdateStaffRequest>({
    firstName: '',
    lastName: '',
    email: '',
    role: '',
    clinicName: '',
    npiNumber: ''
  });
  
  const [errors, setErrors] = useState<Partial<UpdateStaffRequest>>({});
  
  const updateStaffMutation = useUpdateStaff();
  
  // Populate form when staff data changes
  useEffect(() => {
    if (staff) {
      setFormData({
        firstName: staff.firstName,
        lastName: staff.lastName,
        email: staff.email,
        role: staff.role,
        clinicName: staff.clinicName || '',
        npiNumber: staff.npiNumber || ''
      });
      setErrors({});
    }
  }, [staff]);
  
  const handleInputChange = (field: keyof UpdateStaffRequest, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };
  
  const validateForm = (): boolean => {
    const newErrors: Partial<UpdateStaffRequest> = {};
    
    if (!formData.firstName?.trim()) {
      newErrors.firstName = 'First name is required';
    }
    
    if (!formData.lastName?.trim()) {
      newErrors.lastName = 'Last name is required';
    }
    
    if (!formData.email?.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    if (!formData.role) {
      newErrors.role = 'Role is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSubmit = async () => {
    if (!validateForm() || !staff) {
      return;
    }
    
    try {
      await updateStaffMutation.mutateAsync({ id: staff.id, data: formData });
      handleClose();
    } catch (error) {
      console.error('Error updating staff:', error);
    }
  };
  
  const handleClose = () => {
    setFormData({
      firstName: '',
      lastName: '',
      email: '',
      role: '',
      clinicName: '',
      npiNumber: ''
    });
    setErrors({});
    onClose();
  };
  
  if (!staff) {
    return null;
  }
  
  return (
    <StyledDialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogContent>
        <DialogHeader>
          <div>
            <Typography variant="h5" component="h2" fontWeight="bold" color={theme.colors.gray[800]}>
              Update Staff
            </Typography>
            <Typography variant="body2" color={theme.colors.gray[600]} sx={{ mt: 1 }}>
              Please enter Staff's detail
            </Typography>
          </div>
          <IconButton onClick={handleClose} size="small">
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
              error={!!errors.firstName}
              helperText={errors.firstName}
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
              error={!!errors.lastName}
              helperText={errors.lastName}
            />
          </InputWithIcon>
          
          <InputWithIcon>
            <InputIcon>
              <Mail size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Email"
              placeholder="Staff's Email"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
              error={!!errors.email}
              helperText={errors.email}
            />
          </InputWithIcon>
          
          <SelectWithIcon fullWidth>
            <InputLabel>Role</InputLabel>
            <Select
              value={formData.role}
              onChange={(e) => handleInputChange('role', e.target.value)}
              error={!!errors.role}
              label="Role"
            >
              <MenuItem value="physician">Physician</MenuItem>
              <MenuItem value="staff">Staff</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
            {errors.role && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                {errors.role}
              </Typography>
            )}
          </SelectWithIcon>
          
          <InputWithIcon>
            <InputIcon>
              <Building size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="Clinic Name"
              placeholder="Clinic Name"
              value={formData.clinicName}
              onChange={(e) => handleInputChange('clinicName', e.target.value)}
            />
          </InputWithIcon>
          
          <InputWithIcon>
            <InputIcon>
              <Stethoscope size={20} />
            </InputIcon>
            <TextField
              fullWidth
              label="NPI Number"
              placeholder="NPI Number"
              value={formData.npiNumber}
              onChange={(e) => handleInputChange('npiNumber', e.target.value)}
            />
          </InputWithIcon>
        </Box>
      </DialogContent>
      
      <DialogActions sx={{ padding: '1.5rem 2rem', borderTop: '1px solid #e0e0e0' }}>
        <Button
          onClick={handleClose}
          variant="outlined"
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
          onClick={handleSubmit}
          variant="contained"
          disabled={updateStaffMutation.isPending}
          sx={{
            backgroundColor: theme.colors.primary,
            '&:hover': {
              backgroundColor: '#0056b3',
            },
            '&:disabled': {
              backgroundColor: theme.colors.gray[300],
            }
          }}
        >
          {updateStaffMutation.isPending ? 'Updating...' : 'Update'}
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};

export default EditStaffModal; 