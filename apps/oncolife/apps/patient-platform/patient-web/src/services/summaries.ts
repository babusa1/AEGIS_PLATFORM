import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

export interface Summary {
  uuid: string;
  overall_feeling: string;
  created_at: string;
  bulleted_summary: string;
  longer_summary: string;
  symptom_list?: string[];
  severity_list?: { [key: string]: any };
  medication_list?: any[];
  // Add other fields as needed
}

const fetchSummaries = async (year: number, month: number): Promise<{ data: Summary[] }> => {
  const response = await apiClient.get<Summary[]>(
    API_CONFIG.ENDPOINTS.SUMMARIES.BY_MONTH(year, month)
  );
  // Wrap the array in { data: [] } to match component expectations
  return { data: response.data || [] };
};

export const useSummaries = (year: number, month: number) => {
  return useQuery({
    queryKey: ['summaries', year, month],
    queryFn: () => fetchSummaries(year, month),
    enabled: !!year && !!month,
  });
};


const fetchSummaryDetails = async (summaryId: string): Promise<Summary> => {
  try {
    const response = await apiClient.get<Summary>(
      API_CONFIG.ENDPOINTS.SUMMARIES.DETAIL(summaryId)
    );
    return response.data;
  } catch (error) {
    console.error('Summary Details API Error:', error);
    throw error;
  }
};

export const useSummaryDetails = (summaryId: string) => {
    return useQuery({
        queryKey: ['summaryDetails', summaryId],
        queryFn: () => fetchSummaryDetails(summaryId),
        enabled: !!summaryId,
    });
};