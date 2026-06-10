import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

interface SignUpData {
  firstName: string;
  lastName: string;
  emailAddress: string;
}

interface SignUpResponse {
  success: boolean;
  message: string;
  user?: {
    id: string;
    email: string;
    name: string;
    role: string;
  };
  token?: string;
}

const signUpUser = async (data: SignUpData): Promise<SignUpResponse> => {
  const response = await apiClient.post<SignUpResponse>(API_CONFIG.ENDPOINTS.AUTH.SIGNUP, data);
  return response.data;
};

export const useSignUp = () => {
  return useMutation({
    mutationFn: signUpUser,
    onSuccess: (data) => {
      // Handle successful signup
      if (data.token) {
        localStorage.setItem('token', data.token);
      }
    },
    onError: (error) => {
      console.error('Signup error:', error);
    },
  });
};
