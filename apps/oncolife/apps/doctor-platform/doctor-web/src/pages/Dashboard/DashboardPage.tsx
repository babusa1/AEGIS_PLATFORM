/**
 * =============================================================================
 * OncoLife Physician Dashboard
 * =============================================================================
 * 
 * Module:      DashboardPage.tsx
 * Description: Analytics-driven clinical monitoring dashboard for physicians.
 *              Displays severity-ranked patient list with real-time symptom
 *              data from the patient platform.
 * 
 * Created:     2025-12-28
 * Modified:    2026-01-16
 * Author:      Naveen Babu S A
 * Version:     2.1.0
 * 
 * Features:
 *   - Severity-ranked patient list (urgent/severe/moderate/mild)
 *   - Color-coded severity badges
 *   - Search and filter functionality
 *   - Real-time patient data from API
 *   - Click-through to patient detail view
 * 
 * Copyright:
 *   (c) 2026 OncoLife Health Technologies. All rights reserved.
 * =============================================================================
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme, useMediaQuery } from '@mui/material';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Pagination from '@mui/material/Pagination';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Paper from '@mui/material/Paper';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Skeleton from '@mui/material/Skeleton';
import { 
  Search, 
  Calendar, 
  User, 
  FileText, 
  AlertTriangle,
  ChevronRight,
  Activity,
  TrendingUp,
  Clock
} from 'lucide-react';
import styled from 'styled-components';
import { usePatientSummaries, type PatientSummary } from '../../services/dashboard';

// Theme colors (Doctor)
const colors = {
  primary: '#1E3A5F',
  secondary: '#2563EB',
  background: '#F8FAFC',
  paper: '#FFFFFF',
  text: '#0F172A',
  textSecondary: '#475569',
  border: '#E2E8F0',
  severity: {
    mild: '#10B981',
    moderate: '#F59E0B',
    severe: '#EA580C',
    urgent: '#DC2626',
  },
};

// Styled components
const DashboardContainer = styled.div`
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  
  @media (max-width: 768px) {
    padding: 16px;
  }
`;

const DashboardHeader = styled.div`
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
    font-size: 1.75rem;
    font-weight: 700;
    color: ${colors.primary};
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  p {
    font-size: 0.875rem;
    color: ${colors.textSecondary};
    margin: 4px 0 0 0;
  }
  
  @media (max-width: 768px) {
    h1 {
      font-size: 1.5rem;
    }
  }
`;

const StatsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  
  @media (max-width: 992px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 576px) {
    grid-template-columns: 1fr;
  }
`;

const StatCard = styled.div<{ $accentColor?: string }>`
  background: white;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid ${colors.border};
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: ${props => props.$accentColor || colors.secondary};
  }
  
  .stat-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    background: ${props => props.$accentColor ? `${props.$accentColor}15` : `${colors.secondary}15`};
    color: ${props => props.$accentColor || colors.secondary};
  }
  
  .stat-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: ${colors.text};
    line-height: 1;
    margin-bottom: 4px;
  }
  
  .stat-label {
    font-size: 0.8125rem;
    color: ${colors.textSecondary};
    font-weight: 500;
  }
`;

const ControlsContainer = styled.div`
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

const PatientList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const PatientCard = styled.div`
  background: white;
  border-radius: 12px;
  border: 1px solid ${colors.border};
  overflow: hidden;
  transition: all 0.2s ease;
  cursor: pointer;
  
  &:hover {
    border-color: ${colors.secondary};
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
    transform: translateY(-1px);
  }
`;

const PatientHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, ${colors.primary}08 0%, ${colors.secondary}08 100%);
  border-bottom: 1px solid ${colors.border};
  
  @media (max-width: 768px) {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
  }
`;

const PatientInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 24px;
  
  @media (max-width: 768px) {
    flex-wrap: wrap;
    gap: 12px;
  }
`;

const PatientName = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  
  .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: ${colors.primary};
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.875rem;
  }
  
  .name {
    font-weight: 600;
    color: ${colors.text};
    font-size: 1rem;
  }
  
  @media (max-width: 576px) {
    .avatar {
      width: 36px;
      height: 36px;
    }
    .name {
      font-size: 0.9375rem;
    }
  }
`;

const DetailBadge = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8125rem;
  color: ${colors.textSecondary};
  
  svg {
    width: 14px;
    height: 14px;
    color: ${colors.textSecondary};
  }
`;

const SeverityBadge = styled.span<{ $severity: 'mild' | 'moderate' | 'severe' | 'urgent' }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: ${props => `${colors.severity[props.$severity]}15`};
  color: ${props => colors.severity[props.$severity]};
  border: 1px solid ${props => `${colors.severity[props.$severity]}30`};
`;

const PatientContent = styled.div`
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  
  @media (max-width: 768px) {
    padding: 14px 16px;
  }
`;

const ContentRow = styled.div`
  display: flex;
  gap: 12px;
  align-items: flex-start;
  
  .label {
    font-weight: 600;
    color: ${colors.textSecondary};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    min-width: 80px;
    padding-top: 2px;
  }
  
  .value {
    color: ${colors.text};
    font-size: 0.875rem;
    line-height: 1.5;
    flex: 1;
  }
`;

const ViewDetailsLink = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid ${colors.border};
  color: ${colors.secondary};
  font-size: 0.875rem;
  font-weight: 500;
  
  svg {
    transition: transform 0.2s;
  }
  
  &:hover svg {
    transform: translateX(4px);
  }
`;

const PaginationContainer = styled.div`
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding: 16px;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 48px 24px;
  background: white;
  border-radius: 12px;
  border: 1px dashed ${colors.border};
  
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

const DashboardPage: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  
  const { data, isLoading, error } = usePatientSummaries(page, search, filter);
  
  // Calculate dynamic stats from patient data
  const urgentCount = data?.data.filter(p => p.maxSeverity === 'urgent' || p.hasEscalation).length || 0;
  const checkInsToday = data?.data.filter(p => {
    if (!p.lastUpdated) return false;
    const lastCheckin = new Date(p.lastUpdated);
    const today = new Date();
    return lastCheckin.toDateString() === today.toDateString();
  }).length || 0;
  
  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };
  
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(event.target.value);
    setPage(1);
  };
  
  const handleFilterChange = (event: any) => {
    setFilter(event.target.value);
    setPage(1);
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getSeverity = (patient: PatientSummary): 'mild' | 'moderate' | 'severe' | 'urgent' => {
    // Use severity from API if available
    if (patient.maxSeverity) {
      return patient.maxSeverity;
    }
    // Fallback: detect from summary text
    const summary = patient.summary || '';
    if (summary.toLowerCase().includes('urgent') || summary.toLowerCase().includes('emergency') || patient.hasEscalation) {
      return 'urgent';
    }
    if (summary.toLowerCase().includes('severe')) {
      return 'severe';
    }
    if (summary.toLowerCase().includes('moderate')) {
      return 'moderate';
    }
    return 'mild';
  };
  
  return (
    <DashboardContainer>
      {/* Header */}
      <DashboardHeader>
        <HeaderTitle>
          <h1>
            <Activity size={28} color={colors.secondary} />
            Patient Dashboard
          </h1>
          <p>Monitor patient symptoms and clinical trends</p>
        </HeaderTitle>
      </DashboardHeader>
      
      {/* Stats Cards */}
      <StatsRow>
        <StatCard $accentColor={colors.secondary}>
          <div className="stat-icon">
            <User size={20} />
          </div>
          <div className="stat-value">{data?.total || 0}</div>
          <div className="stat-label">Total Patients</div>
        </StatCard>
        
        <StatCard $accentColor={colors.severity.urgent}>
          <div className="stat-icon">
            <AlertTriangle size={20} />
          </div>
          <div className="stat-value">{urgentCount}</div>
          <div className="stat-label">Urgent Cases</div>
        </StatCard>
        
        <StatCard $accentColor="#10B981">
          <div className="stat-icon">
            <TrendingUp size={20} />
          </div>
          <div className="stat-value">{checkInsToday}</div>
          <div className="stat-label">Check-ins Today</div>
        </StatCard>
        
        <StatCard $accentColor="#8B5CF6">
          <div className="stat-icon">
            <Clock size={20} />
          </div>
          <div className="stat-value">-</div>
          <div className="stat-label">Avg Response Time</div>
        </StatCard>
      </StatsRow>
      
      {/* Controls */}
      <ControlsContainer>
        <SearchWrapper>
          <TextField
            fullWidth
            placeholder="Search patients..."
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
                backgroundColor: 'white',
              }
            }}
          />
        </SearchWrapper>
        
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={filter}
            label="Time Range"
            onChange={handleFilterChange}
            sx={{ borderRadius: '10px', backgroundColor: 'white' }}
          >
            <MenuItem value="all">All Time</MenuItem>
            <MenuItem value="today">Today</MenuItem>
            <MenuItem value="week">This Week</MenuItem>
            <MenuItem value="month">This Month</MenuItem>
          </Select>
        </FormControl>
      </ControlsContainer>
      
      {/* Patient List */}
      {error && (
        <Box sx={{ 
          p: 2, 
          bgcolor: '#FEF2F2', 
          borderRadius: 2, 
          border: '1px solid #FECACA',
          mb: 2 
        }}>
          <Typography color="error" variant="body2">
            Error loading patient summaries. Please try again.
          </Typography>
        </Box>
      )}
      
      {isLoading ? (
        <PatientList>
          {[1, 2, 3].map((i) => (
            <Card key={i} sx={{ borderRadius: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <Skeleton variant="circular" width={40} height={40} />
                  <Box sx={{ flex: 1 }}>
                    <Skeleton variant="text" width="60%" />
                    <Skeleton variant="text" width="40%" />
                  </Box>
                </Box>
                <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1 }} />
              </CardContent>
            </Card>
          ))}
        </PatientList>
      ) : data?.data.length === 0 ? (
        <EmptyState>
          <User size={48} />
          <h3>No Patients Found</h3>
          <p>Try adjusting your search or filter criteria.</p>
        </EmptyState>
      ) : (
        <PatientList>
          {data?.data.map((patient) => (
            <PatientCard key={patient.id} onClick={() => navigate(`/patients/${patient.id}`)}>
              <PatientHeader>
                <PatientInfo>
                  <PatientName>
                    <div className="avatar">
                      {getInitials(patient.patientName)}
                    </div>
                    <span className="name">{patient.patientName}</span>
                  </PatientName>
                  <DetailBadge>
                    <Calendar size={14} />
                    DOB: {patient.dateOfBirth}
                  </DetailBadge>
                  <DetailBadge>
                    <FileText size={14} />
                    MRN: {patient.mrn}
                  </DetailBadge>
                </PatientInfo>
                <SeverityBadge $severity={getSeverity(patient)}>
                  {getSeverity(patient)}
                </SeverityBadge>
              </PatientHeader>
              
              <PatientContent>
                <ContentRow>
                  <span className="label">Symptoms</span>
                  <span className="value">{patient.symptoms || 'No symptoms reported'}</span>
                </ContentRow>
                <ContentRow>
                  <span className="label">Summary</span>
                  <span className="value">{patient.summary || 'No summary available'}</span>
                </ContentRow>
              </PatientContent>
              
              <ViewDetailsLink>
                View Details <ChevronRight size={16} style={{ marginLeft: 4 }} />
              </ViewDetailsLink>
            </PatientCard>
          ))}
        </PatientList>
      )}
      
      {data && data.totalPages > 1 && (
        <PaginationContainer>
          <Pagination
            count={data.totalPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
            size={isMobile ? 'small' : 'medium'}
          />
        </PaginationContainer>
      )}
    </DashboardContainer>
  );
};

export default DashboardPage;
