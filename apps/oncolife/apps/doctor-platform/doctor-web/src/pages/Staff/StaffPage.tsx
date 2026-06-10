/**
 * OncoLife Physician Portal - Staff Management
 * Staff list with search and management capabilities
 */

import React, { useState } from 'react';
import { useTheme, useMediaQuery } from '@mui/material';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TablePagination from '@mui/material/TablePagination';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Avatar from '@mui/material/Avatar';
import Chip from '@mui/material/Chip';
import InputAdornment from '@mui/material/InputAdornment';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import { Search, Plus, Edit, UserCog, Mail, Building2, ChevronRight, X } from 'lucide-react';
import styled from 'styled-components';
import { useStaff } from '../../services/staff';
import type { Staff } from '../../services/staff';

// Theme colors (Doctor)
const colors = {
  primary: '#1E3A5F',
  primaryLight: '#2E5077',
  secondary: '#2563EB',
  background: '#F8FAFC',
  paper: '#FFFFFF',
  text: '#0F172A',
  textSecondary: '#475569',
  border: '#E2E8F0',
  accent: '#0D9488',
};

const PageContainer = styled.div`
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  
  @media (max-width: 768px) {
    padding: 16px;
  }
`;

const PageHeader = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 24px;
  
  @media (min-width: 768px) {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
`;

const HeaderTitle = styled.div`
  h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: ${colors.primary};
    margin: 0;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  p {
    font-size: 0.875rem;
    color: ${colors.textSecondary};
    margin: 4px 0 0 0;
  }
  
  @media (max-width: 768px) {
    h1 {
      font-size: 1.25rem;
    }
  }
`;

const ControlsRow = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 20px;
  
  @media (max-width: 576px) {
    flex-direction: column;
    align-items: stretch;
  }
`;

const SearchWrapper = styled.div`
  flex: 1;
  min-width: 280px;
  
  @media (max-width: 576px) {
    min-width: 100%;
  }
`;

const TableWrapper = styled.div`
  background: ${colors.paper};
  border-radius: 12px;
  border: 1px solid ${colors.border};
  overflow: hidden;
`;

const MobileCard = styled.div`
  background: ${colors.paper};
  border-radius: 12px;
  border: 1px solid ${colors.border};
  margin-bottom: 12px;
  overflow: hidden;
`;

const MobileCardHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, ${colors.primary}05 0%, ${colors.accent}05 100%);
  border-bottom: 1px solid ${colors.border};
`;

const MobileCardContent = styled.div`
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const MobileCardRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
  
  .label {
    color: ${colors.textSecondary};
    font-weight: 500;
  }
  
  .value {
    color: ${colors.text};
  }
`;

const MobileCardAction = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
  border-top: 1px solid ${colors.border};
`;

const RoleBadge = styled.span<{ $role: string }>`
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  
  ${props => {
    switch (props.$role.toLowerCase()) {
      case 'doctor':
      case 'physician':
        return `
          background: ${colors.primary}15;
          color: ${colors.primary};
          border: 1px solid ${colors.primary}30;
        `;
      case 'nurse':
        return `
          background: ${colors.accent}15;
          color: ${colors.accent};
          border: 1px solid ${colors.accent}30;
        `;
      default:
        return `
          background: ${colors.secondary}15;
          color: ${colors.secondary};
          border: 1px solid ${colors.secondary}30;
        `;
    }
  }}
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 64px 24px;
  
  svg {
    color: ${colors.textSecondary};
    margin-bottom: 16px;
  }
  
  h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: ${colors.text};
    margin: 0 0 8px 0;
  }
  
  p {
    color: ${colors.textSecondary};
    font-size: 0.875rem;
    margin: 0;
  }
`;

// Staff type is imported from services/staff

// Modal Components
const AddStaffModal: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => (
  <Dialog 
    open={open} 
    onClose={onClose}
    maxWidth="sm"
    fullWidth
    PaperProps={{
      sx: { borderRadius: 3 }
    }}
  >
    <DialogTitle sx={{ 
      display: 'flex', 
      justifyContent: 'space-between', 
      alignItems: 'center',
      borderBottom: `1px solid ${colors.border}`,
    }}>
      <Typography variant="h6" fontWeight={600}>Add Staff Member</Typography>
      <IconButton onClick={onClose} size="small">
        <X size={20} />
      </IconButton>
    </DialogTitle>
    <DialogContent sx={{ pt: 3 }}>
      <Typography color="textSecondary" sx={{ mb: 3 }}>
        Add staff functionality will be implemented here. Staff members will receive 
        an email invitation to set up their account.
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField label="First Name" fullWidth size="small" />
        <TextField label="Last Name" fullWidth size="small" />
        <TextField label="Email" fullWidth size="small" type="email" />
        <TextField label="Role" fullWidth size="small" select>
          <option value="nurse">Nurse Navigator</option>
          <option value="ma">Medical Assistant</option>
        </TextField>
      </Box>
    </DialogContent>
    <DialogActions sx={{ p: 2, borderTop: `1px solid ${colors.border}` }}>
      <Button onClick={onClose} sx={{ color: colors.textSecondary }}>Cancel</Button>
      <Button 
        variant="contained" 
        sx={{ 
          bgcolor: colors.primary,
          '&:hover': { bgcolor: colors.primaryLight }
        }}
      >
        Send Invitation
      </Button>
    </DialogActions>
  </Dialog>
);

const EditStaffModal: React.FC<{ open: boolean; onClose: () => void; staff: Staff | null }> = ({ open, onClose, staff }) => (
  <Dialog 
    open={open} 
    onClose={onClose}
    maxWidth="sm"
    fullWidth
    PaperProps={{
      sx: { borderRadius: 3 }
    }}
  >
    <DialogTitle sx={{ 
      display: 'flex', 
      justifyContent: 'space-between', 
      alignItems: 'center',
      borderBottom: `1px solid ${colors.border}`,
    }}>
      <Typography variant="h6" fontWeight={600}>Edit Staff Member</Typography>
      <IconButton onClick={onClose} size="small">
        <X size={20} />
      </IconButton>
    </DialogTitle>
    <DialogContent sx={{ pt: 3 }}>
      <Typography color="textSecondary" sx={{ mb: 3 }}>
        Editing {staff?.firstName} {staff?.lastName}'s profile.
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField label="First Name" fullWidth size="small" defaultValue={staff?.firstName} />
        <TextField label="Last Name" fullWidth size="small" defaultValue={staff?.lastName} />
        <TextField label="Email" fullWidth size="small" type="email" defaultValue={staff?.email} />
        <TextField label="Role" fullWidth size="small" defaultValue={staff?.role} />
      </Box>
    </DialogContent>
    <DialogActions sx={{ p: 2, borderTop: `1px solid ${colors.border}` }}>
      <Button onClick={onClose} sx={{ color: colors.textSecondary }}>Cancel</Button>
      <Button 
        variant="contained" 
        sx={{ 
          bgcolor: colors.primary,
          '&:hover': { bgcolor: colors.primaryLight }
        }}
      >
        Save Changes
      </Button>
    </DialogActions>
  </Dialog>
);

const StaffPage: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedStaff, setSelectedStaff] = useState<Staff | null>(null);
  
  // Real API call using useStaff hook
  const { data, isLoading, error } = useStaff(page + 1, search, rowsPerPage);
  
  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
  };
  
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(event.target.value);
    setPage(0);
  };
  
  const handleEditStaff = (staff: Staff) => {
    setSelectedStaff(staff);
    setIsEditModalOpen(true);
  };
  
  const getInitials = (firstName: string, lastName: string) => {
    return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase() || 'S';
  };

  const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
      case 'doctor':
      case 'physician':
        return colors.primary;
      case 'nurse':
        return colors.accent;
      default:
        return colors.secondary;
    }
  };
  
  return (
    <PageContainer>
      <PageHeader>
        <HeaderTitle>
          <h1>
            <UserCog size={24} color={colors.accent} />
            Staff Management
          </h1>
          <p>Manage your clinic staff and their access</p>
        </HeaderTitle>
        
        <Button
          variant="contained"
          startIcon={<Plus size={18} />}
          onClick={() => setIsAddModalOpen(true)}
          sx={{
            bgcolor: colors.primary,
            borderRadius: 2,
            px: 3,
            py: 1,
            textTransform: 'none',
            fontWeight: 600,
            '&:hover': {
              bgcolor: colors.primaryLight,
            },
          }}
        >
          Add Staff
        </Button>
      </PageHeader>
      
      <ControlsRow>
        <SearchWrapper>
          <TextField
            fullWidth
            placeholder="Search by name or email..."
            value={search}
            onChange={handleSearchChange}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search size={18} color={colors.textSecondary} />
                </InputAdornment>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '10px',
                bgcolor: colors.paper,
              },
            }}
          />
        </SearchWrapper>
      </ControlsRow>
      
      {error && (
        <Box sx={{ 
          p: 2, 
          bgcolor: '#FEF2F2', 
          borderRadius: 2, 
          border: '1px solid #FECACA',
          mb: 2 
        }}>
          <Typography color="error" variant="body2">
            Error loading staff. Please try again.
          </Typography>
        </Box>
      )}
      
      {isLoading ? (
        <TableWrapper>
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 6 }}>
            <CircularProgress />
          </Box>
        </TableWrapper>
      ) : data.data.length === 0 ? (
        <TableWrapper>
          <EmptyState>
            <UserCog size={48} />
            <h3>No Staff Members Found</h3>
            <p>Add your first staff member to get started.</p>
          </EmptyState>
        </TableWrapper>
      ) : isMobile ? (
        // Mobile Card View
        <Box>
          {data.data.map((staff) => (
            <MobileCard key={staff.id}>
              <MobileCardHeader>
                <Avatar sx={{ 
                  bgcolor: getRoleColor(staff.role), 
                  width: 44, 
                  height: 44,
                  fontWeight: 600,
                }}>
                  {getInitials(staff.firstName, staff.lastName)}
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {staff.firstName} {staff.lastName}
                  </Typography>
                  <RoleBadge $role={staff.role}>{staff.role}</RoleBadge>
                </Box>
              </MobileCardHeader>
              <MobileCardContent>
                <MobileCardRow>
                  <span className="label">Email</span>
                  <span className="value">{staff.email}</span>
                </MobileCardRow>
                <MobileCardRow>
                  <span className="label">Clinic</span>
                  <span className="value">{staff.clinicName || '-'}</span>
                </MobileCardRow>
              </MobileCardContent>
              <MobileCardAction>
                <Button
                  size="small"
                  endIcon={<ChevronRight size={16} />}
                  onClick={() => handleEditStaff(staff)}
                  sx={{ color: colors.secondary }}
                >
                  Edit
                </Button>
              </MobileCardAction>
            </MobileCard>
          ))}
        </Box>
      ) : (
        // Desktop Table View
        <TableWrapper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: `${colors.primary}08` }}>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Staff Member</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Email</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Role</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Clinic</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }} align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.data.map((staff) => (
                  <TableRow 
                    key={staff.id}
                    sx={{ 
                      '&:hover': { bgcolor: colors.background },
                      cursor: 'pointer',
                    }}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ 
                          bgcolor: getRoleColor(staff.role), 
                          width: 36, 
                          height: 36,
                          fontSize: '0.875rem',
                          fontWeight: 600,
                        }}>
                          {getInitials(staff.firstName, staff.lastName)}
                        </Avatar>
                        <Typography fontWeight={500}>
                          {staff.firstName} {staff.lastName}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Mail size={14} color={colors.textSecondary} />
                        {staff.email}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <RoleBadge $role={staff.role}>{staff.role}</RoleBadge>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Building2 size={14} color={colors.textSecondary} />
                        {staff.clinicName || '-'}
                      </Box>
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="Edit Staff">
                        <IconButton
                          size="small"
                          onClick={() => handleEditStaff(staff)}
                          sx={{ 
                            color: colors.secondary,
                            '&:hover': { bgcolor: `${colors.secondary}15` },
                          }}
                        >
                          <Edit size={18} />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          {data.total > rowsPerPage && (
            <TablePagination
              component="div"
              count={data.total}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              rowsPerPageOptions={[5, 10, 25]}
              sx={{
                borderTop: `1px solid ${colors.border}`,
                bgcolor: colors.background,
              }}
            />
          )}
        </TableWrapper>
      )}
      
      <AddStaffModal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
      />
      
      <EditStaffModal
        open={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedStaff(null);
        }}
        staff={selectedStaff}
      />
    </PageContainer>
  );
};

export default StaffPage;
