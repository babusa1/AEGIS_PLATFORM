/**
 * =============================================================================
 * Dashboard Service - Doctor Portal
 * =============================================================================
 * 
 * Module:      dashboard.ts
 * Description: API service for dashboard and analytics endpoints. Handles
 *              patient ranking, symptom timelines, and weekly reports.
 * 
 * Created:     2025-12-28
 * Modified:    2026-01-16
 * Author:      Naveen Babu S A
 * Version:     2.1.0
 * 
 * Endpoints Used:
 *   GET  /api/v1/dashboard            - Ranked patient list
 *   GET  /api/v1/dashboard/patient/:id - Patient detail with timeline
 *   GET  /api/v1/dashboard/reports/weekly - Weekly report data
 * 
 * Copyright:
 *   (c) 2026 OncoLife Health Technologies. All rights reserved.
 * =============================================================================
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

// =============================================================================
// Types
// =============================================================================

export interface PatientSummary {
  id: string;
  patientName: string;
  dateOfBirth: string;
  mrn: string;
  symptoms: string;
  summary: string;
  lastUpdated: string;
  status: 'active' | 'inactive' | 'pending';
  priority: 'high' | 'medium' | 'low';
  // Added for severity display
  maxSeverity: 'mild' | 'moderate' | 'severe' | 'urgent' | null;
  hasEscalation: boolean;
  severityBadge: string;
}

export interface PatientRanking {
  patient_uuid: string;
  first_name: string | null;
  last_name: string | null;
  email_address: string | null;
  last_checkin: string | null;
  max_severity: string | null;
  has_escalation: boolean;
  severity_badge: string;
}

export interface DashboardLanding {
  patients: PatientRanking[];
  total_patients: number;
  period_days: number;
}

export interface SymptomDataPoint {
  date: string | null;
  severity: string;
  severity_numeric: number;
}

export interface TreatmentEvent {
  event_type: string;
  event_date: string | null;
  metadata: Record<string, unknown>;
}

export interface PatientTimeline {
  patient_uuid: string;
  period_days: number;
  symptom_series: Record<string, SymptomDataPoint[]>;
  treatment_events: TreatmentEvent[];
}

export interface SharedQuestion {
  id: string;
  question_text: string;
  category: string | null;
  is_answered: boolean;
  created_at: string | null;
}

export interface WeeklyReportSummary {
  report_id: string | null;
  physician_id: string;
  report_week_start: string;
  report_week_end: string;
  generated_at: string;
  patient_count: number;
  total_alerts: number;
  total_questions: number;
}

export interface PatientReportSection {
  patient: Record<string, unknown>;
  symptoms: Record<string, unknown>;
  alerts: Array<Record<string, unknown>>;
  questions: Array<Record<string, unknown>>;
}

export interface WeeklyReportData {
  physician_id: string;
  report_week_start: string;
  report_week_end: string;
  generated_at: string;
  patient_count: number;
  total_alerts: number;
  total_questions: number;
  patients: PatientReportSection[];
}

export interface DashboardResponse {
  data: PatientSummary[];
  total: number;
  page: number;
  totalPages: number;
}

// =============================================================================
// Transform Functions
// =============================================================================

const mapSeverityToPriority = (severity: string | null): 'high' | 'medium' | 'low' => {
  if (!severity) return 'low';
  switch (severity.toLowerCase()) {
    case 'urgent':
    case 'severe':
      return 'high';
    case 'moderate':
      return 'medium';
    default:
      return 'low';
  }
};

const transformPatientRankingToSummary = (ranking: PatientRanking): PatientSummary => ({
  id: ranking.patient_uuid,
  patientName: `${ranking.first_name || ''} ${ranking.last_name || ''}`.trim() || 'Unknown',
  dateOfBirth: '',
  mrn: '',
  symptoms: '',
  summary: ranking.has_escalation ? 'urgent escalation' : (ranking.max_severity || ''),
  lastUpdated: ranking.last_checkin || '',
  status: 'active',
  priority: mapSeverityToPriority(ranking.max_severity),
  // Pass through severity data from API
  maxSeverity: (ranking.max_severity as 'mild' | 'moderate' | 'severe' | 'urgent') || null,
  hasEscalation: ranking.has_escalation,
  severityBadge: ranking.severity_badge,
});

// =============================================================================
// API Functions
// =============================================================================

// Fetch dashboard landing (ranked patient list)
const fetchDashboardLanding = async (days: number = 7): Promise<DashboardLanding> => {
  try {
    const response = await apiClient.get<DashboardLanding>(
      `${API_CONFIG.ENDPOINTS.DASHBOARD.LANDING}?days=${days}`
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching dashboard landing:', error);
    return {
      patients: [],
      total_patients: 0,
      period_days: days,
    };
  }
};

// Fetch patient summaries (transformed from dashboard landing)
const fetchPatientSummaries = async (
  page: number = 1, 
  search: string = '', 
  filter: string = 'all'
): Promise<DashboardResponse> => {
  try {
    const dashboardData = await fetchDashboardLanding(30);
    
    let patients = dashboardData.patients.map(transformPatientRankingToSummary);
    
    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      patients = patients.filter(patient => 
        patient.patientName.toLowerCase().includes(searchLower) ||
        patient.mrn.toLowerCase().includes(searchLower)
      );
    }
    
    // Apply status filter
    if (filter && filter !== 'all') {
      patients = patients.filter(patient => patient.status === filter);
    }
    
    const itemsPerPage = 10;
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedData = patients.slice(startIndex, endIndex);
    
    return {
      data: paginatedData,
      total: patients.length,
      page,
      totalPages: Math.ceil(patients.length / itemsPerPage),
    };
  } catch (error) {
    console.error('Error fetching patient summaries:', error);
    return {
      data: [],
      total: 0,
      page: 1,
      totalPages: 0,
    };
  }
};

// Fetch patient timeline data
const fetchPatientTimeline = async (
  patientUuid: string,
  days: number = 30
): Promise<PatientTimeline> => {
  try {
    const response = await apiClient.get<PatientTimeline>(
      `${API_CONFIG.ENDPOINTS.DASHBOARD.PATIENT_TIMELINE(patientUuid)}?days=${days}`
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching patient timeline:', error);
    return {
      patient_uuid: patientUuid,
      period_days: days,
      symptom_series: {},
      treatment_events: [],
    };
  }
};

// Fetch patient's shared questions
const fetchPatientQuestions = async (patientUuid: string): Promise<SharedQuestion[]> => {
  try {
    const response = await apiClient.get<SharedQuestion[]>(
      API_CONFIG.ENDPOINTS.DASHBOARD.PATIENT_QUESTIONS(patientUuid)
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching patient questions:', error);
    return [];
  }
};

// Fetch weekly reports list
const fetchReportsList = async (): Promise<WeeklyReportSummary[]> => {
  try {
    const response = await apiClient.get<WeeklyReportSummary[]>(
      API_CONFIG.ENDPOINTS.DASHBOARD.REPORTS_LIST
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching reports list:', error);
    return [];
  }
};

// Fetch weekly report data
const fetchWeeklyReportData = async (weekStart?: string): Promise<WeeklyReportData> => {
  try {
    const url = weekStart 
      ? `${API_CONFIG.ENDPOINTS.DASHBOARD.REPORTS_WEEKLY}?week_start=${weekStart}`
      : API_CONFIG.ENDPOINTS.DASHBOARD.REPORTS_WEEKLY;
    const response = await apiClient.get<WeeklyReportData>(url);
    return response.data;
  } catch (error) {
    console.error('Error fetching weekly report:', error);
    const now = new Date();
    const weekStartDate = new Date(now);
    weekStartDate.setDate(now.getDate() - now.getDay());
    const weekEndDate = new Date(weekStartDate);
    weekEndDate.setDate(weekStartDate.getDate() + 6);
    
    return {
      physician_id: '',
      report_week_start: weekStartDate.toISOString().split('T')[0],
      report_week_end: weekEndDate.toISOString().split('T')[0],
      generated_at: new Date().toISOString(),
      patient_count: 0,
      total_alerts: 0,
      total_questions: 0,
      patients: [],
    };
  }
};

// Generate weekly report
const generateWeeklyReport = async (weekStart?: string): Promise<{ report_id: string }> => {
  const response = await apiClient.post<{ report_id: string }>(
    API_CONFIG.ENDPOINTS.DASHBOARD.REPORTS_GENERATE,
    { week_start: weekStart }
  );
  return response.data;
};

// =============================================================================
// React Query Hooks
// =============================================================================

export const useDashboardLanding = (days: number = 7) => {
  return useQuery({
    queryKey: ['dashboardLanding', days],
    queryFn: () => fetchDashboardLanding(days),
  });
};

export const usePatientSummaries = (
  page: number = 1, 
  search: string = '', 
  filter: string = 'all'
) => {
  return useQuery({
    queryKey: ['patientSummaries', page, search, filter],
    queryFn: () => fetchPatientSummaries(page, search, filter),
  });
};

export const usePatientTimeline = (patientUuid: string, days: number = 30) => {
  return useQuery({
    queryKey: ['patientTimeline', patientUuid, days],
    queryFn: () => fetchPatientTimeline(patientUuid, days),
    enabled: !!patientUuid,
  });
};

export const usePatientQuestions = (patientUuid: string) => {
  return useQuery({
    queryKey: ['patientQuestions', patientUuid],
    queryFn: () => fetchPatientQuestions(patientUuid),
    enabled: !!patientUuid,
  });
};

export const useReportsList = () => {
  return useQuery({
    queryKey: ['reportsList'],
    queryFn: fetchReportsList,
  });
};

export const useWeeklyReportData = (weekStart?: string) => {
  return useQuery({
    queryKey: ['weeklyReport', weekStart],
    queryFn: () => fetchWeeklyReportData(weekStart),
  });
};

export const useGenerateReport = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateWeeklyReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reportsList'] });
      queryClient.invalidateQueries({ queryKey: ['weeklyReport'] });
    },
  });
};

// Legacy hook for backwards compatibility
export const usePatientDetails = (patientId: string) => {
  return useQuery({
    queryKey: ['patientDetails', patientId],
    queryFn: async (): Promise<PatientSummary> => {
      const timeline = await fetchPatientTimeline(patientId, 30);
      return {
        id: timeline.patient_uuid,
        patientName: '',
        dateOfBirth: '',
        mrn: '',
        symptoms: Object.keys(timeline.symptom_series).join(', '),
        summary: '',
        lastUpdated: '',
        status: 'active',
        priority: 'medium',
      };
    },
    enabled: !!patientId,
  });
};
