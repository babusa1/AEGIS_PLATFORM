/**
 * Patient Service - Doctor Portal
 * ================================
 * 
 * Handles all patient-related API calls.
 * Connects to doctor-api backend endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

// =============================================================================
// Types
// =============================================================================

export interface Patient {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  mrn: string;
  dateOfBirth: string;
  sex: 'Male' | 'Female' | 'Other';
  race: string;
  phoneNumber: string;
  physician: string;
  diseaseType: string;
  associateClinic: string;
  treatmentType: string;
}

export interface PatientsResponse {
  data: Patient[];
  total: number;
  page: number;
  totalPages: number;
}

// Backend response types (from doctor-api)
interface BackendPatientSummary {
  uuid: string;
  email_address: string;
  first_name?: string;
  last_name?: string;
  created_at?: string;
  phone_number?: string;
}

interface BackendPatientDetail {
  uuid: string;
  email_address: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  dob?: string;
  sex?: string;
  disease_type?: string;
  treatment_type?: string;
  created_at?: string;
  mrn?: string;
}

interface BackendPatientListResponse {
  patients: BackendPatientSummary[];
  total: number;
  skip: number;
  limit: number;
}

// =============================================================================
// Transform Functions (Backend → Frontend)
// =============================================================================

const transformPatientSummary = (backend: BackendPatientSummary): Patient => ({
  id: backend.uuid,
  firstName: backend.first_name || '',
  lastName: backend.last_name || '',
  email: backend.email_address,
  mrn: '',
  dateOfBirth: '',
  sex: 'Other',
  race: '',
  phoneNumber: backend.phone_number || '',
  physician: '',
  diseaseType: '',
  associateClinic: '',
  treatmentType: '',
});

const transformPatientDetail = (backend: BackendPatientDetail): Patient => ({
  id: backend.uuid,
  firstName: backend.first_name || '',
  lastName: backend.last_name || '',
  email: backend.email_address,
  mrn: backend.mrn || '',
  dateOfBirth: backend.dob || '',
  sex: (backend.sex as 'Male' | 'Female' | 'Other') || 'Other',
  race: '',
  phoneNumber: backend.phone_number || '',
  physician: '',
  diseaseType: backend.disease_type || '',
  associateClinic: '',
  treatmentType: backend.treatment_type || '',
});

// =============================================================================
// API Functions
// =============================================================================

const fetchPatients = async (
  page: number = 1, 
  search: string = '',
  rowsPerPage: number = 10
): Promise<PatientsResponse> => {
  try {
    const skip = (page - 1) * rowsPerPage;
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: rowsPerPage.toString(),
    });
    
    if (search && search.length >= 2) {
      params.append('search', search);
    }
    
    const response = await apiClient.get<BackendPatientListResponse>(
      `${API_CONFIG.ENDPOINTS.PATIENTS.LIST}?${params.toString()}`
    );
    
    const patients = response.data.patients.map(transformPatientSummary);
    
    return {
      data: patients,
      total: response.data.total,
      page,
      totalPages: Math.ceil(response.data.total / rowsPerPage),
    };
  } catch (error) {
    console.error('Error fetching patients:', error);
    // Return empty response on error
    return {
      data: [],
      total: 0,
      page: 1,
      totalPages: 0,
    };
  }
};

const fetchPatientDetails = async (patientId: string): Promise<Patient> => {
  const response = await apiClient.get<BackendPatientDetail>(
    API_CONFIG.ENDPOINTS.PATIENTS.BY_UUID(patientId)
  );
  
  return transformPatientDetail(response.data);
};

// =============================================================================
// React Query Hooks
// =============================================================================

export const usePatients = (
  page: number = 1, 
  search: string = '',
  rowsPerPage: number = 10
) => {
  return useQuery({
    queryKey: ['patients', page, search, rowsPerPage],
    queryFn: () => fetchPatients(page, search, rowsPerPage),
  });
};

export const usePatientDetails = (patientId: string) => {
  return useQuery({
    queryKey: ['patientDetails', patientId],
    queryFn: () => fetchPatientDetails(patientId),
    enabled: !!patientId,
  });
};

// =============================================================================
// Mutation Hooks (for future use when backend supports these)
// =============================================================================

export const useAddPatient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (patientData: Omit<Patient, 'id'>): Promise<Patient> => {
      // TODO: Implement when backend supports patient creation from doctor portal
      // const response = await apiClient.post(API_CONFIG.ENDPOINTS.PATIENTS.LIST, patientData);
      // return transformPatientDetail(response.data);
      throw new Error('Patient creation not yet implemented');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
};

export const useUpdatePatient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, ...patientData }: Patient): Promise<Patient> => {
      // TODO: Implement when backend supports patient updates from doctor portal
      // const response = await apiClient.put(API_CONFIG.ENDPOINTS.PATIENTS.BY_UUID(id), patientData);
      // return transformPatientDetail(response.data);
      throw new Error('Patient update not yet implemented');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
};
