/**
 * Staff Service - Doctor Portal
 * ==============================
 * 
 * Handles all staff-related API calls.
 * Connects to doctor-api backend endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

// =============================================================================
// Types
// =============================================================================

export interface Staff {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  clinicName?: string;
  npiNumber?: string;
}

export interface StaffListResponse {
  data: Staff[];
  total: number;
  page: number;
  page_size: number;
}

export interface AddStaffRequest {
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  clinicName?: string;
  npiNumber?: string;
}

export interface UpdateStaffRequest {
  firstName?: string;
  lastName?: string;
  email?: string;
  role?: string;
  clinicName?: string;
  npiNumber?: string;
}

// Backend response types (from doctor-api)
interface BackendStaffResponse {
  staff_uuid: string;
  email_address: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
  role: string;
  npi_number?: string;
  created_at?: string;
  updated_at?: string;
}

interface BackendStaffListResponse {
  staff: BackendStaffResponse[];
  total: number;
  skip: number;
  limit: number;
}

// =============================================================================
// Transform Functions (Backend → Frontend)
// =============================================================================

const transformStaff = (backend: BackendStaffResponse): Staff => ({
  id: backend.staff_uuid,
  firstName: backend.first_name || '',
  lastName: backend.last_name || '',
  email: backend.email_address,
  role: backend.role,
  clinicName: '', // TODO: Add clinic name from backend if available
  npiNumber: backend.npi_number,
});

// =============================================================================
// API Functions
// =============================================================================

const getStaff = async (
  page: number, 
  search?: string, 
  pageSize: number = 10
): Promise<StaffListResponse> => {
  try {
    const skip = (page - 1) * pageSize;
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: pageSize.toString(),
    });
    
    let endpoint = `${API_CONFIG.ENDPOINTS.STAFF.LIST}?${params.toString()}`;
    
    // Use search endpoint if search term provided
    if (search && search.length >= 2) {
      endpoint = `${API_CONFIG.ENDPOINTS.STAFF.LIST}/search?q=${encodeURIComponent(search)}&limit=${pageSize}`;
      
      const response = await apiClient.get<BackendStaffResponse[]>(endpoint);
      const staffList = response.data.map(transformStaff);
      
      return {
        data: staffList,
        total: staffList.length,
        page,
        page_size: pageSize,
      };
    }
    
    const response = await apiClient.get<BackendStaffListResponse>(endpoint);
    const staffList = response.data.staff.map(transformStaff);
    
    return {
      data: staffList,
      total: response.data.total,
      page,
      page_size: pageSize,
    };
  } catch (error) {
    console.error('Error fetching staff:', error);
    return {
      data: [],
      total: 0,
      page: 1,
      page_size: pageSize,
    };
  }
};

const addStaffMember = async (
  data: AddStaffRequest
): Promise<{ message: string; staff_uuid: string }> => {
  // Determine if this is a physician or staff member
  if (data.role === 'physician') {
    const response = await apiClient.post<{ message: string; staff_uuid: string }>(
      `${API_CONFIG.ENDPOINTS.STAFF.LIST}/physician`,
      {
        email_address: data.email,
        first_name: data.firstName,
        last_name: data.lastName,
        npi_number: data.npiNumber || '0000000000', // NPI is required for physicians
        clinic_uuid: '00000000-0000-0000-0000-000000000000', // TODO: Get from context
      }
    );
    return response.data;
  } else {
    const response = await apiClient.post<{ message: string; staff_uuid: string }>(
      `${API_CONFIG.ENDPOINTS.STAFF.LIST}/member`,
      {
        email_address: data.email,
        first_name: data.firstName,
        last_name: data.lastName,
        role: data.role,
        physician_uuids: [], // TODO: Get from context
        clinic_uuid: '00000000-0000-0000-0000-000000000000', // TODO: Get from context
      }
    );
    return response.data;
  }
};

const updateStaffMember = async ({ 
  id, 
  data 
}: { 
  id: string; 
  data: UpdateStaffRequest 
}): Promise<{ message: string }> => {
  // TODO: Implement when backend supports staff updates
  // const response = await apiClient.put(
  //   API_CONFIG.ENDPOINTS.STAFF.BY_UUID(id),
  //   {
  //     first_name: data.firstName,
  //     last_name: data.lastName,
  //     email_address: data.email,
  //     role: data.role,
  //   }
  // );
  // return response.data;
  throw new Error('Staff update not yet implemented in backend');
};

// =============================================================================
// React Query Hooks
// =============================================================================

export const useStaff = (page: number, search?: string, pageSize: number = 10) => {
  return useQuery({
    queryKey: ['staff', page, search, pageSize],
    queryFn: () => getStaff(page, search, pageSize),
  });
};

export const useAddStaff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: addStaffMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
};

export const useUpdateStaff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: updateStaffMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
};
