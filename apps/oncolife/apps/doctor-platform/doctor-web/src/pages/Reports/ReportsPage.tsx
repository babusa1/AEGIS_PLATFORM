/**
 * =============================================================================
 * Weekly Reports Page - Doctor Portal
 * =============================================================================
 * 
 * Module:      ReportsPage.tsx
 * Description: Weekly physician reports for patient monitoring. Displays
 *              summary statistics, severity breakdown, and patient data.
 * 
 * Created:     2026-01-02
 * Modified:    2026-01-16
 * Author:      Naveen Babu S A
 * Version:     2.1.0
 * 
 * Features:
 *   - Week selector for historical reports
 *   - Summary statistics (total patients, escalations)
 *   - Severity breakdown chart
 *   - Patient table with max severity
 *   - Report generation functionality
 * 
 * Copyright:
 *   (c) 2026 OncoLife Health Technologies. All rights reserved.
 * =============================================================================
 */

import React, { useState } from 'react';
import { useTheme, useMediaQuery } from '@mui/material';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Skeleton from '@mui/material/Skeleton';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import {
  FileText,
  Download,
  Calendar,
  Users,
  AlertTriangle,
  TrendingUp,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  BarChart3,
} from 'lucide-react';
import styled from 'styled-components';
import {
  useWeeklyReportData,
  useReportsList,
  useGenerateReport,
  type WeeklyReportData,
} from '../../services/dashboard';

// Theme colors
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
const PageContainer = styled.div`
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeInUp 0.4s ease-out;

  @media (max-width: 768px) {
    padding: 16px;
  }
`;

const PageHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;

  .header-left {
    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      color: ${colors.primary};
      margin: 0 0 4px 0;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    p {
      font-size: 0.9rem;
      color: ${colors.textSecondary};
      margin: 0;
    }
  }

  .header-actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  @media (max-width: 600px) {
    flex-direction: column;
    align-items: stretch;

    .header-actions {
      justify-content: flex-end;
    }
  }
`;

const StatsGrid = styled.div`
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

const StatCard = styled.div<{ $color?: string }>`
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
    background: ${props => props.$color || colors.secondary};
  }

  .stat-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    background: ${props => props.$color ? `${props.$color}15` : `${colors.secondary}15`};
    color: ${props => props.$color || colors.secondary};
  }

  .stat-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: ${colors.text};
    margin: 0;
  }

  .stat-label {
    font-size: 0.85rem;
    color: ${colors.textSecondary};
    margin-top: 4px;
  }
`;

const WeekSelector = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  padding: 8px 16px;
  border-radius: 12px;
  border: 1px solid ${colors.border};

  .week-display {
    font-weight: 600;
    color: ${colors.text};
    min-width: 200px;
    text-align: center;
  }

  button {
    background: none;
    border: none;
    padding: 4px;
    cursor: pointer;
    color: ${colors.textSecondary};
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      background: ${colors.background};
      color: ${colors.primary};
    }
  }
`;

const SeverityBreakdown = styled.div`
  display: flex;
  gap: 8px;
  flex-wrap: wrap;

  .severity-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    background: ${colors.background};
    border-radius: 20px;
    font-size: 0.85rem;

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 60px 24px;

  svg {
    color: ${colors.textSecondary};
    opacity: 0.4;
    margin-bottom: 16px;
  }

  h3 {
    font-size: 1.25rem;
    color: ${colors.text};
    margin: 0 0 8px 0;
  }

  p {
    color: ${colors.textSecondary};
    margin: 0;
  }
`;

const ReportsPage: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // State for week selection
  const [weekOffset, setWeekOffset] = useState(0);
  
  // Calculate week dates
  const getWeekDates = (offset: number) => {
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - now.getDay() - (offset * 7));
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    return {
      start: weekStart.toISOString().split('T')[0],
      end: weekEnd.toISOString().split('T')[0],
      display: `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`,
    };
  };

  const weekDates = getWeekDates(weekOffset);

  // Fetch data
  const { data: reportData, isLoading, error, refetch } = useWeeklyReportData(weekDates.start);
  const generateReportMutation = useGenerateReport();

  const handleGenerateReport = async () => {
    await generateReportMutation.mutateAsync(weekDates.start);
    refetch();
  };

  const getSeverityColor = (severity: string | null | undefined): string => {
    if (!severity) return colors.severity.mild;
    const severityMap: Record<string, string> = {
      mild: colors.severity.mild,
      moderate: colors.severity.moderate,
      severe: colors.severity.severe,
      urgent: colors.severity.urgent,
    };
    return severityMap[severity.toLowerCase()] || colors.severity.mild;
  };

  const renderStats = () => {
    if (isLoading) {
      return (
        <StatsGrid>
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} variant="rectangular" height={120} sx={{ borderRadius: 2 }} />
          ))}
        </StatsGrid>
      );
    }

    const stats = reportData?.summary_stats || {
      total_patients: 0,
      total_escalations: 0,
      severity_breakdown: {},
    };

    return (
      <StatsGrid>
        <StatCard $color={colors.secondary}>
          <div className="stat-icon">
            <Users size={20} />
          </div>
          <p className="stat-value">{stats.total_patients}</p>
          <p className="stat-label">Total Patients</p>
        </StatCard>

        <StatCard $color={colors.severity.urgent}>
          <div className="stat-icon">
            <AlertTriangle size={20} />
          </div>
          <p className="stat-value">{stats.total_escalations}</p>
          <p className="stat-label">Escalations</p>
        </StatCard>

        <StatCard $color={colors.severity.moderate}>
          <div className="stat-icon">
            <TrendingUp size={20} />
          </div>
          <p className="stat-value">
            {reportData?.patients?.length || 0}
          </p>
          <p className="stat-label">Active Reports</p>
        </StatCard>

        <StatCard $color={colors.severity.mild}>
          <div className="stat-icon">
            <MessageSquare size={20} />
          </div>
          <p className="stat-value">
            {reportData?.patients?.reduce((acc, p) => acc + (p.shared_questions?.length || 0), 0) || 0}
          </p>
          <p className="stat-label">Patient Questions</p>
        </StatCard>
      </StatsGrid>
    );
  };

  const renderSeverityBreakdown = () => {
    const breakdown = reportData?.summary_stats?.severity_breakdown || {};
    
    if (Object.keys(breakdown).length === 0) {
      return null;
    }

    return (
      <Paper sx={{ p: 3, mb: 3, borderRadius: 3, border: `1px solid ${colors.border}` }} elevation={0}>
        <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <BarChart3 size={20} />
          Severity Breakdown
        </Typography>
        <SeverityBreakdown>
          {Object.entries(breakdown).map(([severity, count]) => (
            <div key={severity} className="severity-item">
              <div className="dot" style={{ background: getSeverityColor(severity) }} />
              <span>{severity}: {count as number}</span>
            </div>
          ))}
        </SeverityBreakdown>
      </Paper>
    );
  };

  const renderPatientTable = () => {
    if (isLoading) {
      return (
        <Skeleton variant="rectangular" height={400} sx={{ borderRadius: 2 }} />
      );
    }

    if (!reportData?.patients || reportData.patients.length === 0) {
      return (
        <Paper sx={{ borderRadius: 3, border: `1px solid ${colors.border}` }} elevation={0}>
          <EmptyState>
            <FileText size={64} />
            <h3>No report data available</h3>
            <p>Generate a report for this week to see patient summaries.</p>
          </EmptyState>
        </Paper>
      );
    }

    return (
      <Paper sx={{ borderRadius: 3, border: `1px solid ${colors.border}`, overflow: 'hidden' }} elevation={0}>
        <Box sx={{ p: 2, borderBottom: `1px solid ${colors.border}` }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Users size={20} />
            Patient Summary ({reportData.patients.length} patients)
          </Typography>
        </Box>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: colors.background }}>
                <TableCell sx={{ fontWeight: 600 }}>Patient</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Max Severity</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Escalations</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Questions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reportData.patients.map((patient) => (
                <TableRow key={patient.patient_uuid} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {patient.first_name} {patient.last_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={patient.max_severity || 'None'}
                      size="small"
                      sx={{
                        bgcolor: `${getSeverityColor(patient.max_severity)}20`,
                        color: getSeverityColor(patient.max_severity),
                        fontWeight: 600,
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    {patient.escalation_count > 0 ? (
                      <Chip
                        icon={<AlertTriangle size={14} />}
                        label={patient.escalation_count}
                        size="small"
                        sx={{
                          bgcolor: `${colors.severity.urgent}15`,
                          color: colors.severity.urgent,
                        }}
                      />
                    ) : (
                      <Typography variant="body2" color="textSecondary">0</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {patient.shared_questions?.length || 0}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    );
  };

  return (
    <PageContainer>
      <PageHeader>
        <div className="header-left">
          <h1>
            <FileText size={28} />
            Weekly Reports
          </h1>
          <p>Comprehensive weekly summaries of patient symptoms and escalations</p>
        </div>
        <div className="header-actions">
          <WeekSelector>
            <button onClick={() => setWeekOffset(w => w + 1)}>
              <ChevronLeft size={20} />
            </button>
            <span className="week-display">
              <Calendar size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              {weekDates.display}
            </span>
            <button 
              onClick={() => setWeekOffset(w => Math.max(0, w - 1))}
              disabled={weekOffset === 0}
            >
              <ChevronRight size={20} />
            </button>
          </WeekSelector>
          <Button
            variant="contained"
            startIcon={generateReportMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <RefreshCw size={16} />}
            onClick={handleGenerateReport}
            disabled={generateReportMutation.isPending}
            sx={{
              bgcolor: colors.primary,
              '&:hover': { bgcolor: '#152d4a' },
            }}
          >
            {generateReportMutation.isPending ? 'Generating...' : 'Generate Report'}
          </Button>
        </div>
      </PageHeader>

      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          Error loading report data. Please try again.
        </Alert>
      )}

      {/* Stats Cards */}
      {renderStats()}

      {/* Severity Breakdown */}
      {renderSeverityBreakdown()}

      {/* Patient Table */}
      {renderPatientTable()}
    </PageContainer>
  );
};

export default ReportsPage;

