/**
 * OncoLife Physician Portal - Patients Management
 * Patient list with search and management capabilities
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
import Skeleton from '@mui/material/Skeleton';
import Card from '@mui/material/Card';
import { Search, Plus, Edit, Users, Calendar, Mail, ChevronRight } from 'lucide-react';
import styled from 'styled-components';
import { usePatients, type Patient } from '../../services/patients';
import AddPatientModal from './components/AddPatientModal';
import EditPatientModal from './components/EditPatientModal';

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
  background: linear-gradient(135deg, ${colors.primary}05 0%, ${colors.secondary}05 100%);
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

const PatientsPage: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  
  const { data, isLoading, error } = usePatients(page + 1, search, rowsPerPage);
  
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
  
  const handleAddPatient = () => {
    setIsAddModalOpen(true);
  };
  
  const handleEditPatient = (patient: Patient) => {
    setSelectedPatient(patient);
    setIsEditModalOpen(true);
  };
  
  const getInitials = (firstName: string, lastName: string) => {
    return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase() || 'P';
  };
  
  return (
    <PageContainer>
      <PageHeader>
        <HeaderTitle>
          <h1>
            <Users size={24} color={colors.secondary} />
            Patient Management
          </h1>
          <p>View and manage your patient roster</p>
        </HeaderTitle>
        
        <Button
          variant="contained"
          startIcon={<Plus size={18} />}
          onClick={handleAddPatient}
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
          Add Patient
        </Button>
      </PageHeader>
      
      <ControlsRow>
        <SearchWrapper>
          <TextField
            fullWidth
            placeholder="Search by name, email, or MRN..."
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
            Error loading patients. Please try again.
          </Typography>
        </Box>
      )}
      
      {isLoading ? (
        <TableWrapper>
          <Box sx={{ p: 3 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Box key={i} sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <Skeleton variant="circular" width={40} height={40} />
                <Box sx={{ flex: 1 }}>
                  <Skeleton variant="text" width="40%" />
                  <Skeleton variant="text" width="60%" />
                </Box>
              </Box>
            ))}
          </Box>
        </TableWrapper>
      ) : data?.data.length === 0 ? (
        <TableWrapper>
          <EmptyState>
            <Users size={48} />
            <h3>No Patients Found</h3>
            <p>Add your first patient or try a different search term.</p>
          </EmptyState>
        </TableWrapper>
      ) : isMobile ? (
        // Mobile Card View
        <Box>
          {data?.data.map((patient) => (
            <MobileCard key={patient.id}>
              <MobileCardHeader>
                <Avatar sx={{ 
                  bgcolor: colors.primary, 
                  width: 44, 
                  height: 44,
                  fontWeight: 600,
                }}>
                  {getInitials(patient.firstName, patient.lastName)}
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {patient.firstName} {patient.lastName}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    MRN: {patient.mrn}
                  </Typography>
                </Box>
              </MobileCardHeader>
              <MobileCardContent>
                <MobileCardRow>
                  <span className="label">Email</span>
                  <span className="value">{patient.email}</span>
                </MobileCardRow>
                <MobileCardRow>
                  <span className="label">DOB</span>
                  <span className="value">{patient.dateOfBirth}</span>
                </MobileCardRow>
                <MobileCardRow>
                  <span className="label">Sex</span>
                  <span className="value">{patient.sex}</span>
                </MobileCardRow>
              </MobileCardContent>
              <MobileCardAction>
                <Button
                  size="small"
                  endIcon={<ChevronRight size={16} />}
                  onClick={() => handleEditPatient(patient)}
                  sx={{ color: colors.secondary }}
                >
                  Edit
                </Button>
              </MobileCardAction>
            </MobileCard>
          ))}
          
          {data && data.total > rowsPerPage && (
            <TablePagination
              component="div"
              count={data.total}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
              rowsPerPageOptions={[5, 10, 25]}
              sx={{ bgcolor: colors.paper, borderRadius: 2, mt: 2 }}
            />
          )}
        </Box>
      ) : (
        // Desktop Table View
        <TableWrapper>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: `${colors.primary}08` }}>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Patient</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Email</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>MRN</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>DOB</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }}>Sex</TableCell>
                  <TableCell sx={{ fontWeight: 600, color: colors.primary }} align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data?.data.map((patient) => (
                  <TableRow 
                    key={patient.id}
                    sx={{ 
                      '&:hover': { bgcolor: colors.background },
                      cursor: 'pointer',
                    }}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ 
                          bgcolor: colors.primary, 
                          width: 36, 
                          height: 36,
                          fontSize: '0.875rem',
                          fontWeight: 600,
                        }}>
                          {getInitials(patient.firstName, patient.lastName)}
                        </Avatar>
                        <Typography fontWeight={500}>
                          {patient.firstName} {patient.lastName}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Mail size={14} color={colors.textSecondary} />
                        {patient.email}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={patient.mrn} 
                        size="small" 
                        sx={{ 
                          bgcolor: `${colors.secondary}15`,
                          color: colors.secondary,
                          fontWeight: 600,
                          fontSize: '0.75rem',
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Calendar size={14} color={colors.textSecondary} />
                        {patient.dateOfBirth}
                      </Box>
                    </TableCell>
                    <TableCell>{patient.sex}</TableCell>
                    <TableCell align="center">
                      <Tooltip title="Edit Patient">
                        <IconButton
                          size="small"
                          onClick={() => handleEditPatient(patient)}
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
          
          <TablePagination
            component="div"
            count={data?.total || 0}
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
        </TableWrapper>
      )}
      
      <AddPatientModal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
      />
      
      <EditPatientModal
        open={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedPatient(null);
        }}
        patient={selectedPatient}
      />
    </PageContainer>
  );
};

export default PatientsPage;
