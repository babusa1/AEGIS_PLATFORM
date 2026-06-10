import { apiClient } from '../utils/apiClient';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ProfileFormData } from '../pages/ProfilePage/types';

// Extract patient UUID from auth token
const getPatientUuid = (): string => {
  const token = localStorage.getItem('authToken');
  if (token && token.startsWith('dev-mode-token-')) {
    // Token format: dev-mode-token-UUID
    return token.replace('dev-mode-token-', '');
  }
  // Default test user UUID for local dev
  return '11111111-1111-1111-1111-111111111111';
};

export const fetchProfile = async () => {
  const patientUuid = getPatientUuid();
  const response = await apiClient.get(`/profile?patient_uuid=${patientUuid}`);
  return response.data;
};

export const updateProfile = async (data: Partial<ProfileFormData>) => {
  const response = await apiClient.put('/profile', data);
  return response.data;
};

export const useFetchProfile = (options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: ['profile'],
    queryFn: fetchProfile,
    enabled: options?.enabled ?? true,
  });
};

export const useUpdateProfile = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: updateProfile,
    onSuccess: () => {
      // Invalidate profile cache to refetch
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
};