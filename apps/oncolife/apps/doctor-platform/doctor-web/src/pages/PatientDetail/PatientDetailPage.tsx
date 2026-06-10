/**
 * Patient Detail Page
 * ===================
 * 
 * Detailed view of a patient including:
 * - Symptom timeline (zigzag chart)
 * - Treatment overlay
 * - Shared questions
 * - Diary entries
 */

import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTheme, useMediaQuery } from '@mui/material';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import { 
  ArrowLeft, 
  Activity, 
  Calendar, 
  MessageSquare, 
  TrendingUp,
  AlertTriangle,
  Clock,
  Pill,
  CheckCircle
} from 'lucide-react';
import styled from 'styled-components';
import {
  usePatientTimeline,
  usePatientQuestions,
  usePatientDetails,
  type SymptomDataPoint,
  type TreatmentEvent,
  type SharedQuestion,
} from '../../services/dashboard';

// Theme colors (Doctor - Clinical Navy)
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
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;

  .back-button {
    color: ${colors.textSecondary};
    &:hover {
      color: ${colors.primary};
    }
  }

  .patient-info {
    flex: 1;

    h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: ${colors.primary};
      margin: 0 0 4px 0;
    }

    .meta {
      display: flex;
      gap: 16px;
      font-size: 0.9rem;
      color: ${colors.textSecondary};
    }
  }
`;

const TimelineCard = styled(Paper)`
  padding: 24px;
  margin-bottom: 24px;
  border-radius: 16px;
  border: 1px solid ${colors.border};

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h3 {
      font-size: 1.1rem;
      font-weight: 600;
      color: ${colors.text};
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
    }
  }

  .legend {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    color: ${colors.textSecondary};

    .dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }
  }
`;

const TimelineChart = styled.div`
  position: relative;
  height: 300px;
  background: ${colors.background};
  border-radius: 12px;
  padding: 20px;
  overflow-x: auto;

  .y-axis {
    position: absolute;
    left: 0;
    top: 20px;
    bottom: 40px;
    width: 60px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-size: 0.75rem;
    color: ${colors.textSecondary};
  }

  .chart-area {
    margin-left: 70px;
    height: 100%;
    position: relative;
  }

  .gridlines {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 40px;

    .gridline {
      border-bottom: 1px dashed ${colors.border};
      height: 25%;
    }
  }

  .x-axis {
    position: absolute;
    bottom: 0;
    left: 70px;
    right: 20px;
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: ${colors.textSecondary};
  }
`;

const TreatmentMarker = styled.div<{ $position: number }>`
  position: absolute;
  left: ${props => props.$position}%;
  top: 0;
  bottom: 40px;
  width: 2px;
  background: ${colors.secondary};
  opacity: 0.6;

  &::after {
    content: attr(data-label);
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.7rem;
    color: ${colors.secondary};
    white-space: nowrap;
  }
`;

const QuestionsSection = styled.div`
  .question-card {
    background: ${colors.paper};
    border: 1px solid ${colors.border};
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;

    .question-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }

    .question-text {
      font-size: 1rem;
      color: ${colors.text};
      line-height: 1.5;
    }

    .question-meta {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      font-size: 0.85rem;
      color: ${colors.textSecondary};
    }
  }

  .empty-state {
    text-align: center;
    padding: 40px;
    color: ${colors.textSecondary};

    svg {
      margin-bottom: 12px;
      opacity: 0.5;
    }
  }
`;

const SymptomLine = styled.div<{ $color: string }>`
  position: absolute;
  height: 3px;
  background: ${props => props.$color};
  border-radius: 2px;
  transition: all 0.3s ease;

  &:hover {
    height: 5px;
  }
`;

const DataPoint = styled.div<{ $color: string; $x: number; $y: number }>`
  position: absolute;
  left: ${props => props.$x}%;
  bottom: ${props => props.$y}%;
  width: 10px;
  height: 10px;
  background: ${props => props.$color};
  border: 2px solid white;
  border-radius: 50%;
  transform: translate(-50%, 50%);
  cursor: pointer;
  z-index: 2;
  transition: transform 0.2s ease;

  &:hover {
    transform: translate(-50%, 50%) scale(1.3);
  }
`;

// Generate colors for symptom lines
const symptomColors = [
  '#2563EB', // Blue
  '#10B981', // Green
  '#F59E0B', // Yellow
  '#EA580C', // Orange
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#06B6D4', // Cyan
  '#EF4444', // Red
];

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      {...other}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

const PatientDetailPage: React.FC = () => {
  const { uuid } = useParams<{ uuid: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  const [tabValue, setTabValue] = useState(0);
  const [timelineDays, setTimelineDays] = useState(30);

  // Fetch data
  const { data: timeline, isLoading: timelineLoading } = usePatientTimeline(uuid || '', timelineDays);
  const { data: questions, isLoading: questionsLoading } = usePatientQuestions(uuid || '');
  const { data: patientDetails } = usePatientDetails(uuid || '');

  const handleBack = () => {
    navigate('/dashboard');
  };

  const getSeverityColor = (severity: string): string => {
    const severityMap: Record<string, string> = {
      mild: colors.severity.mild,
      moderate: colors.severity.moderate,
      severe: colors.severity.severe,
      urgent: colors.severity.urgent,
    };
    return severityMap[severity.toLowerCase()] || colors.severity.mild;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const renderTimeline = () => {
    if (timelineLoading) {
      return <Skeleton variant="rectangular" height={300} />;
    }

    if (!timeline?.symptom_series || Object.keys(timeline.symptom_series).length === 0) {
      return (
        <Box sx={{ textAlign: 'center', py: 6, color: colors.textSecondary }}>
          <Activity size={48} style={{ marginBottom: 12, opacity: 0.5 }} />
          <Typography>No symptom data available for this period</Typography>
        </Box>
      );
    }

    const symptoms = Object.entries(timeline.symptom_series);
    const allDates = new Set<string>();
    symptoms.forEach(([, dataPoints]) => {
      dataPoints.forEach(dp => allDates.add(dp.date));
    });
    const sortedDates = Array.from(allDates).sort();

    return (
      <TimelineChart>
        <div className="y-axis">
          <span>Urgent (4)</span>
          <span>Severe (3)</span>
          <span>Moderate (2)</span>
          <span>Mild (1)</span>
        </div>
        
        <div className="chart-area">
          <div className="gridlines">
            <div className="gridline" />
            <div className="gridline" />
            <div className="gridline" />
            <div className="gridline" />
          </div>

          {/* Treatment markers */}
          {timeline.treatment_events.map((event, idx) => {
            const dateIndex = sortedDates.indexOf(event.event_date);
            const position = dateIndex >= 0 
              ? (dateIndex / (sortedDates.length - 1)) * 100 
              : 0;
            return (
              <TreatmentMarker 
                key={idx} 
                $position={position}
                data-label={event.event_type.replace('_', ' ')}
              />
            );
          })}

          {/* Symptom data points */}
          {symptoms.map(([symptomId, dataPoints], symptomIdx) => (
            dataPoints.map((dp, dpIdx) => {
              const dateIndex = sortedDates.indexOf(dp.date);
              const x = sortedDates.length > 1 
                ? (dateIndex / (sortedDates.length - 1)) * 100 
                : 50;
              const y = (dp.severity_numeric / 4) * 100;
              
              return (
                <Tooltip 
                  key={`${symptomId}-${dpIdx}`}
                  title={`${symptomId}: ${dp.severity} on ${formatDate(dp.date)}`}
                >
                  <DataPoint 
                    $color={symptomColors[symptomIdx % symptomColors.length]}
                    $x={x}
                    $y={y}
                  />
                </Tooltip>
              );
            })
          ))}
        </div>

        <div className="x-axis">
          {sortedDates.slice(0, 7).map((date, idx) => (
            <span key={idx}>{formatDate(date)}</span>
          ))}
        </div>
      </TimelineChart>
    );
  };

  const renderQuestions = () => {
    if (questionsLoading) {
      return (
        <>
          <Skeleton variant="rectangular" height={100} sx={{ mb: 2, borderRadius: 2 }} />
          <Skeleton variant="rectangular" height={100} sx={{ borderRadius: 2 }} />
        </>
      );
    }

    if (!questions || questions.length === 0) {
      return (
        <div className="empty-state">
          <MessageSquare size={48} />
          <Typography>No shared questions from this patient</Typography>
        </div>
      );
    }

    return questions.map((question) => (
      <div key={question.id} className="question-card">
        <div className="question-header">
          <Chip 
            label={question.category} 
            size="small" 
            sx={{ 
              bgcolor: `${colors.secondary}15`,
              color: colors.secondary,
              fontWeight: 500,
            }} 
          />
          {question.is_answered && (
            <Chip 
              icon={<CheckCircle size={14} />}
              label="Answered" 
              size="small" 
              sx={{ 
                bgcolor: `${colors.severity.mild}15`,
                color: colors.severity.mild,
              }} 
            />
          )}
        </div>
        <p className="question-text">{question.question_text}</p>
        <div className="question-meta">
          <Clock size={14} />
          <span>{formatDate(question.created_at)}</span>
        </div>
      </div>
    ));
  };

  return (
    <PageContainer>
      <PageHeader>
        <IconButton className="back-button" onClick={handleBack}>
          <ArrowLeft size={24} />
        </IconButton>
        <div className="patient-info">
          <h1>
            {patientDetails?.patientName || 'Patient Details'}
          </h1>
          <div className="meta">
            {patientDetails?.mrn && <span>MRN: {patientDetails.mrn}</span>}
            {patientDetails?.dateOfBirth && <span>DOB: {patientDetails.dateOfBirth}</span>}
          </div>
        </div>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant={timelineDays === 7 ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setTimelineDays(7)}
            sx={{ minWidth: 60 }}
          >
            7 Days
          </Button>
          <Button
            variant={timelineDays === 30 ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setTimelineDays(30)}
            sx={{ minWidth: 60 }}
          >
            30 Days
          </Button>
        </Box>
      </PageHeader>

      {/* Symptom Timeline */}
      <TimelineCard elevation={0}>
        <div className="chart-header">
          <h3>
            <TrendingUp size={20} />
            Symptom Timeline
          </h3>
          {timeline?.symptom_series && (
            <div className="legend">
              {Object.keys(timeline.symptom_series).map((symptom, idx) => (
                <div key={symptom} className="legend-item">
                  <div 
                    className="dot" 
                    style={{ background: symptomColors[idx % symptomColors.length] }} 
                  />
                  <span>{symptom}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        {renderTimeline()}
      </TimelineCard>

      {/* Tabs for additional info */}
      <Paper sx={{ borderRadius: 3, border: `1px solid ${colors.border}` }} elevation={0}>
        <Tabs 
          value={tabValue} 
          onChange={(_, v) => setTabValue(v)}
          sx={{ borderBottom: `1px solid ${colors.border}`, px: 2 }}
        >
          <Tab 
            icon={<MessageSquare size={18} />} 
            iconPosition="start" 
            label="Shared Questions" 
          />
          <Tab 
            icon={<Pill size={18} />} 
            iconPosition="start" 
            label="Treatment Events" 
          />
          <Tab 
            icon={<AlertTriangle size={18} />} 
            iconPosition="start" 
            label="Escalations" 
          />
        </Tabs>

        <Box sx={{ p: 3 }}>
          <TabPanel value={tabValue} index={0}>
            <QuestionsSection>
              {renderQuestions()}
            </QuestionsSection>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            {timeline?.treatment_events && timeline.treatment_events.length > 0 ? (
              timeline.treatment_events.map((event, idx) => (
                <Card 
                  key={idx} 
                  sx={{ mb: 2, border: `1px solid ${colors.border}` }}
                  elevation={0}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={600}>
                          {event.event_type.replace('_', ' ').toUpperCase()}
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          {formatDate(event.event_date)}
                        </Typography>
                      </Box>
                      <Chip 
                        icon={<Calendar size={14} />}
                        label={event.metadata?.cycle ? `Cycle ${event.metadata.cycle}` : 'Event'}
                        size="small"
                      />
                    </Box>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Box sx={{ textAlign: 'center', py: 4, color: colors.textSecondary }}>
                <Pill size={48} style={{ marginBottom: 12, opacity: 0.5 }} />
                <Typography>No treatment events recorded</Typography>
              </Box>
            )}
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Box sx={{ textAlign: 'center', py: 4, color: colors.textSecondary }}>
              <AlertTriangle size={48} style={{ marginBottom: 12, opacity: 0.5 }} />
              <Typography>Escalation history coming soon</Typography>
            </Box>
          </TabPanel>
        </Box>
      </Paper>
    </PageContainer>
  );
};

export default PatientDetailPage;

