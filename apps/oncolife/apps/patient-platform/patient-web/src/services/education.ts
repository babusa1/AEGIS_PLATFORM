/**
 * Education Service
 * =================
 * 
 * Service for fetching education resources from the backend API.
 * Education content is symptom-specific, clinician-approved PDFs
 * served from S3 (production) or local static files (development).
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

// ============= Types =============

export interface EducationDocument {
  id: string;
  symptom_code: string;
  symptom_name: string;
  title: string;
  source: string;
  summary: string;
  keywords: string[];
  pdf_url: string;
  display_order: number;
}

export interface EducationHandbook {
  id: string;
  title: string;
  description: string;
  handbook_type: string;
  pdf_url: string;
}

export interface EducationTabContent {
  current_symptom_docs: EducationDocument[];
  common_symptom_docs: EducationDocument[];
  care_team_handouts: EducationHandbook[];
}

export interface EducationSymptom {
  code: string;
  name: string;
  category: string;
  document_count: number;
}

export interface EducationDisclaimer {
  id: string;
  text: string;
  version: string;
}

// ============= Types for PDFs Endpoint =============

export interface EducationPdfItem {
  id: string;
  symptom_code: string;
  symptom_name: string;
  title: string;
  source: string;
  file_path: string;
  pdf_url: string;
  summary: string;
  keywords: string[];
}

export interface EducationHandbookItem {
  id: string;
  title: string;
  description: string;
  file_path: string;
  pdf_url: string;
  handbook_type: string;
}

export interface EducationPdfsResponse {
  symptom_pdfs: EducationPdfItem[];
  handbooks: EducationHandbookItem[];
  total_pdfs: number;
  total_handbooks: number;
}

// ============= API Functions =============

/**
 * Fetch all education PDFs (simple endpoint).
 * Works without requiring symptom sessions.
 */
const fetchEducationPdfs = async (): Promise<EducationPdfsResponse> => {
  const response = await apiClient.get<EducationPdfsResponse>(
    API_CONFIG.ENDPOINTS.EDUCATION.PDFS
  );
  return response.data;
};

/**
 * Fetch education tab content for the current patient.
 * Returns content organized by: current symptoms, common symptoms, handouts.
 */
const fetchEducationTab = async (): Promise<EducationTabContent> => {
  const response = await apiClient.get<EducationTabContent>(
    API_CONFIG.ENDPOINTS.EDUCATION.TAB
  );
  return response.data;
};

/**
 * Search education documents by keyword.
 */
const searchEducation = async (query: string): Promise<EducationDocument[]> => {
  const response = await apiClient.get<EducationDocument[]>(
    API_CONFIG.ENDPOINTS.EDUCATION.SEARCH(query)
  );
  return response.data;
};

/**
 * Get a specific education document by ID.
 */
const fetchEducationDocument = async (documentId: string): Promise<EducationDocument> => {
  const response = await apiClient.get<EducationDocument>(
    API_CONFIG.ENDPOINTS.EDUCATION.DOCUMENT(documentId)
  );
  return response.data;
};

/**
 * Get list of all symptom categories with document counts.
 */
const fetchEducationSymptoms = async (): Promise<EducationSymptom[]> => {
  const response = await apiClient.get<EducationSymptom[]>(
    API_CONFIG.ENDPOINTS.EDUCATION.SYMPTOMS
  );
  return response.data;
};

/**
 * Get the standard education disclaimer text.
 */
const fetchEducationDisclaimer = async (): Promise<EducationDisclaimer> => {
  const response = await apiClient.get<EducationDisclaimer>(
    API_CONFIG.ENDPOINTS.EDUCATION.DISCLAIMER
  );
  return response.data;
};

// ============= React Query Hooks =============

/**
 * Hook to fetch all education PDFs (simple endpoint).
 * This works without requiring symptom sessions.
 * 
 * @example
 * const { data, isLoading, error } = useEducationPdfs();
 */
export const useEducationPdfs = () => {
  return useQuery({
    queryKey: ['education', 'pdfs'],
    queryFn: fetchEducationPdfs,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
};

/**
 * Hook to fetch education tab content.
 * 
 * @example
 * const { data, isLoading, error } = useEducationTab();
 */
export const useEducationTab = () => {
  return useQuery({
    queryKey: ['education', 'tab'],
    queryFn: fetchEducationTab,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
};

/**
 * Hook to search education documents.
 * 
 * @param query - Search query string
 * @example
 * const { data, isLoading } = useEducationSearch('nausea');
 */
export const useEducationSearch = (query: string) => {
  return useQuery({
    queryKey: ['education', 'search', query],
    queryFn: () => searchEducation(query),
    enabled: query.length >= 2, // Only search if query has 2+ chars
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
  });
};

/**
 * Hook to fetch a specific education document.
 * 
 * @param documentId - Document UUID
 */
export const useEducationDocument = (documentId: string) => {
  return useQuery({
    queryKey: ['education', 'document', documentId],
    queryFn: () => fetchEducationDocument(documentId),
    enabled: !!documentId,
  });
};

/**
 * Hook to fetch all symptom categories.
 */
export const useEducationSymptoms = () => {
  return useQuery({
    queryKey: ['education', 'symptoms'],
    queryFn: fetchEducationSymptoms,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes (rarely changes)
  });
};

/**
 * Hook to fetch the education disclaimer.
 */
export const useEducationDisclaimer = () => {
  return useQuery({
    queryKey: ['education', 'disclaimer'],
    queryFn: fetchEducationDisclaimer,
    staleTime: 60 * 60 * 1000, // Cache for 1 hour (rarely changes)
  });
};

// ============= Helper Functions =============

/**
 * Open a PDF document in a new tab.
 * Works with both S3 pre-signed URLs (production) and local static URLs (development).
 */
export const openEducationPdf = (pdfUrl: string): void => {
  window.open(pdfUrl, '_blank', 'noopener,noreferrer');
};

/**
 * Download a PDF document.
 */
export const downloadEducationPdf = async (pdfUrl: string, filename: string): Promise<void> => {
  try {
    const response = await fetch(pdfUrl);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Failed to download PDF:', error);
    // Fallback: open in new tab
    openEducationPdf(pdfUrl);
  }
};

export default {
  useEducationTab,
  useEducationSearch,
  useEducationDocument,
  useEducationSymptoms,
  useEducationDisclaimer,
  openEducationPdf,
  downloadEducationPdf,
};
