/**
 * Questions Service
 * =================
 * 
 * Service for managing "Questions to Ask Doctor" feature.
 * Patients can create, update, and share questions with their physician.
 */

import { apiClient } from '../utils/apiClient';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { API_CONFIG } from '../config/api';

// Types
export interface Question {
  id: string;
  patient_uuid: string;
  question_text: string;
  share_with_physician: boolean;
  is_answered: boolean;
  category: 'symptom' | 'medication' | 'treatment' | 'other';
  created_at: string;
  updated_at: string;
}

export interface QuestionsListResponse {
  questions: Question[];
  total: number;
}

export interface CreateQuestionParams {
  question_text: string;
  share_with_physician?: boolean;
  category?: 'symptom' | 'medication' | 'treatment' | 'other';
}

export interface UpdateQuestionParams {
  question_text?: string;
  share_with_physician?: boolean;
  category?: 'symptom' | 'medication' | 'treatment' | 'other';
  is_answered?: boolean;
}

// API Functions
const fetchQuestions = async (sharedOnly: boolean = false): Promise<QuestionsListResponse> => {
  const response = await apiClient.get(
    `${API_CONFIG.ENDPOINTS.QUESTIONS.LIST}?shared_only=${sharedOnly}`
  );
  return response.data;
};

const createQuestion = async (params: CreateQuestionParams): Promise<Question> => {
  const response = await apiClient.post(API_CONFIG.ENDPOINTS.QUESTIONS.CREATE, params);
  return response.data;
};

const updateQuestion = async ({
  id,
  ...params
}: UpdateQuestionParams & { id: string }): Promise<Question> => {
  const response = await apiClient.patch(API_CONFIG.ENDPOINTS.QUESTIONS.UPDATE(id), params);
  return response.data;
};

const deleteQuestion = async (id: string): Promise<void> => {
  await apiClient.delete(API_CONFIG.ENDPOINTS.QUESTIONS.DELETE(id));
};

const toggleShare = async ({
  id,
  share,
}: {
  id: string;
  share: boolean;
}): Promise<Question> => {
  const response = await apiClient.post(
    `${API_CONFIG.ENDPOINTS.QUESTIONS.SHARE(id)}?share=${share}`
  );
  return response.data;
};

// React Query Hooks
export const useQuestions = (sharedOnly: boolean = false) => {
  return useQuery({
    queryKey: ['questions', sharedOnly],
    queryFn: () => fetchQuestions(sharedOnly),
  });
};

export const useCreateQuestion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createQuestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
    },
  });
};

export const useUpdateQuestion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateQuestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
    },
  });
};

export const useDeleteQuestion = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteQuestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
    },
  });
};

export const useToggleShare = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: toggleShare,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
    },
  });
};

