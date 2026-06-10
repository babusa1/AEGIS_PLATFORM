/**
 * API Configuration
 * =================
 * 
 * Centralized API configuration with versioned endpoints.
 * All API calls now use the /api/v1/ prefix.
 */

// Base URLs from environment variables
// In dev mode, default to localhost:8000 for direct API access
const API_BASE = import.meta.env.VITE_API_BASE || '';
const WS_BASE = import.meta.env.VITE_WS_BASE || (
  import.meta.env.DEV ? 'ws://localhost:8000' : API_BASE.replace('http', 'ws')
);

// API Version prefix
const API_VERSION = '/api/v1';

export const API_CONFIG = {
  // Base URLs
  BASE_URL: `${API_BASE}${API_VERSION}`,
  WS_BASE: WS_BASE,
  API_VERSION,
  
  // Endpoint definitions - all versioned
  ENDPOINTS: {
    // Authentication
    AUTH: {
      LOGIN: '/auth/login',
      SIGNUP: '/auth/signup',
      COMPLETE_NEW_PASSWORD: '/auth/complete-new-password',
      LOGOUT: '/auth/logout',
      DELETE: '/auth/delete-patient',
    },
    
    // Patient Profile
    PROFILE: {
      GET: '/profile',
      INFO: '/profile/info',
      CONFIG: '/profile/config',
      CONSENT: '/profile/consent',
    },
    
    // Symptom Checker Chat
    CHAT: {
      SESSION_TODAY: '/chat/session/today',
      SESSION_NEW: '/chat/session/new',
      FULL: (uuid: string) => `/chat/${uuid}/full`,
      STATE: (uuid: string) => `/chat/${uuid}/state`,
      FEELING: (uuid: string) => `/chat/${uuid}/feeling`,
      DELETE: (uuid: string) => `/chat/${uuid}`,
      WS: (uuid: string) => `/chat/ws/${uuid}`,
    },
    
    // Chemotherapy
    CHEMO: {
      LOG: '/chemo/log',
      HISTORY: '/chemo/history',
      BY_MONTH: (year: number, month: number) => `/chemo/${year}/${month}`,
    },
    
    // Diary Entries
    DIARY: {
      LIST: '/diary',
      BY_MONTH: (year: number, month: number) => `/diary/${year}/${month}`,
      CREATE: '/diary',
      UPDATE: (uuid: string) => `/diary/${uuid}`,
      DELETE: (uuid: string) => `/diary/${uuid}/delete`,
    },
    
    // Conversation Summaries
    SUMMARIES: {
      BY_MONTH: (year: number, month: number) => `/summaries/${year}/${month}`,
      DETAIL: (uuid: string) => `/summaries/detail/${uuid}`,
    },
    
    // Patient Onboarding
    ONBOARDING: '/onboarding',
    
    // Questions to Ask Doctor
    QUESTIONS: {
      LIST: '/questions',
      CREATE: '/questions',
      UPDATE: (id: string) => `/questions/${id}`,
      DELETE: (id: string) => `/questions/${id}`,
      SHARE: (id: string) => `/questions/${id}/share`,
    },
    
    // Education Resources
    EDUCATION: {
      TAB: '/education/tab',
      PDFS: '/education/pdfs',  // Simple endpoint for getting all PDFs
      SEARCH: (query: string) => `/education/search?q=${encodeURIComponent(query)}`,
      DOCUMENT: (id: string) => `/education/document/${id}`,
      SYMPTOMS: '/education/symptoms',
      DISCLAIMER: '/education/disclaimer',
      DELIVER: '/education/deliver',
      SUMMARY: '/education/summary',
      SESSION: '/education/session',
      SESSION_DETAIL: (id: string) => `/education/session/${id}`,
    },
    
    // Notes/Diary
    NOTES: '/diary',
    
    // Health Check
    HEALTH: '/health',
  },
} as const;

// Helper to build full URL
export const buildUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Helper to build WebSocket URL
export const buildWsUrl = (endpoint: string, token: string): string => {
  const wsBase = API_CONFIG.WS_BASE || API_CONFIG.BASE_URL.replace('http', 'ws');
  return `${wsBase}${API_VERSION}${endpoint}?token=${token}`;
};

export default API_CONFIG;
