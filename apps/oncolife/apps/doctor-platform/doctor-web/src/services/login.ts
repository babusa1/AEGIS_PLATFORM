import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

interface LoginData {
  email: string;
  password: string;
}

interface CompleteNewPasswordData {
  email: string;
  newPassword: string;
}

export interface CompleteNewPasswordResponse {
  success: boolean;
  message: string;
  data?: {
  tokens?: {
      access_token: string;
      refresh_token: string;
      id_token: string;
      token_type: string;
    };
  };
}
export interface LoginResponse {
  success: boolean;
  message: string;
  error?: string;
  data?: {
    user_status?: string;
    message?: string;
    session?: string;
    requiresPasswordChange?: boolean;
    tokens?: {
      access_token: string;
      refresh_token: string;
      id_token: string;
      token_type: string;
    };
  };
}

const loginUser = async (data: LoginData): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>(API_CONFIG.ENDPOINTS.AUTH.LOGIN, data);
  return response.data;
};

export const useLogin = () => {
  return useMutation({
    mutationFn: loginUser,
    onSuccess: (data) => {

      if (data.data?.session) {
        localStorage.setItem('authToken', data.data.session);
      }
      if (data.data?.tokens) {
        localStorage.setItem('authToken', data.data.tokens.access_token);
      }
    },
    onError: (error) => {
      console.error('Login error:', error);
    },
  });
};

const completeNewPassword = async (data: CompleteNewPasswordData): Promise<CompleteNewPasswordResponse> => {
  const newData = {
    email: data?.email,
    new_password: data?.newPassword,
    session: localStorage.getItem('authToken'),
  }
  const response = await apiClient.post<CompleteNewPasswordResponse>(API_CONFIG.ENDPOINTS.AUTH.COMPLETE_NEW_PASSWORD, newData);
  return response.data;
};

export const useCompleteNewPassword = () => {
  return useMutation({
    mutationFn: completeNewPassword,
    onSuccess: (data) => {
      if (data.data?.tokens) {
        localStorage.setItem('authToken', data.data.tokens.access_token);
        localStorage.setItem('refreshToken', data.data.tokens.refresh_token);
      }
    },
    onError: (error) => {
      console.error('New password reset error:', error);
    },
  });
};

interface LogoutResponse {
  success: boolean;
  message: string;
}

const logoutUser = async (): Promise<LogoutResponse> => {
  const response = await apiClient.post<LogoutResponse>(API_CONFIG.ENDPOINTS.AUTH.LOGOUT);
  return response.data;
};


export const useLogout = () => {
  return useMutation({
    mutationFn: logoutUser,
    onSuccess: () => {
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
    },
    onError: (error) => {
      console.error('Logout error:', error);
    },
  });
};