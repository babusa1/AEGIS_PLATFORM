/**
 * API Configuration - Doctor Portal
 * ===================================
 * 
 * Centralized API configuration with versioned endpoints.
 * All API calls now use the /api/v1/ prefix.
 */

// Base URLs from environment variables
const API_BASE = import.meta.env.VITE_API_BASE || '';

// API Version prefix
const API_VERSION = '/api/v1';

export const API_CONFIG = {
  // Base URLs
  BASE_URL: `${API_BASE}${API_VERSION}`,
  API_VERSION,
  
  // Endpoint definitions - all versioned
  ENDPOINTS: {
    // Authentication
    AUTH: {
      LOGIN: '/auth/login',
      SIGNUP: '/auth/signup',
      LOGOUT: '/auth/logout',
      COMPLETE_NEW_PASSWORD: '/auth/complete-new-password',
      DELETE_USER: '/auth/delete-user',
    },
    
    // Staff Management
    STAFF: {
      LIST: '/staff',
      PROFILE: '/staff/profile',
      BY_UUID: (uuid: string) => `/staff/${uuid}`,
    },
    
    // Clinic Management
    CLINICS: {
      LIST: '/clinics',
      CREATE: '/clinics',
      BY_UUID: (uuid: string) => `/clinics/${uuid}`,
    },
    
    // Patient Access (read-only)
    PATIENTS: {
      LIST: '/patients',
      BY_UUID: (uuid: string) => `/patients/${uuid}`,
      ALERTS: (uuid: string) => `/patients/${uuid}/alerts`,
      CONVERSATIONS: (uuid: string) => `/patients/${uuid}/conversations`,
      DIARY: (uuid: string) => `/patients/${uuid}/diary`,
      STATS: (uuid: string) => `/patients/${uuid}/stats`,
    },
    
    // Dashboard & Analytics
    DASHBOARD: {
      LANDING: '/dashboard',
      PATIENT_TIMELINE: (uuid: string) => `/dashboard/patient/${uuid}`,
      PATIENT_QUESTIONS: (uuid: string) => `/dashboard/patient/${uuid}/questions`,
      REPORTS_LIST: '/dashboard/reports',
      REPORTS_WEEKLY: '/dashboard/reports/weekly',
      REPORTS_GENERATE: '/dashboard/reports/generate',
    },
    
    // Health Check
    HEALTH: '/health',
  },
} as const;

// Helper to build full URL
export const buildUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

export default API_CONFIG;



