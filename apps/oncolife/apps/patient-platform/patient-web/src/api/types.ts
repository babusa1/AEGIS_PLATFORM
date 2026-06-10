/**
 * API Types
 * =========
 * 
 * TypeScript type definitions for all API requests and responses.
 * Ensures type safety across the application.
 */

// =============================================================================
// Common Types
// =============================================================================

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  hasMore: boolean;
}

// =============================================================================
// Authentication Types
// =============================================================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  valid: boolean;
  message: string;
  user_status?: string;
  session?: string;  // For NEW_PASSWORD_REQUIRED challenge
  tokens?: AuthTokens;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  id_token: string;
  token_type: string;
}

export interface SignupRequest {
  email: string;
  first_name: string;
  last_name: string;
  physician_email?: string;
}

export interface SignupResponse {
  message: string;
  email: string;
  user_status: string;
}

export interface CompletePasswordRequest {
  email: string;
  new_password: string;
  session: string;
}

export interface CompletePasswordResponse {
  message: string;
  tokens: AuthTokens;
}

// =============================================================================
// Profile Types
// =============================================================================

export interface PatientProfile {
  first_name: string | null;
  last_name: string | null;
  email_address: string;
  phone_number: string | null;
  date_of_birth: string | null;
  reminder_time: string | null;
  doctor_name: string | null;
  clinic_name: string | null;
}

export interface PatientConfigurations {
  reminder_method?: string;
  reminder_time?: string;
  acknowledgement_done?: boolean;
  agreed_conditions?: boolean;
}

// =============================================================================
// Chat Types
// =============================================================================

export type MessageType = 
  | 'text'
  | 'single-select'
  | 'multi-select'
  | 'symptom-select'
  | 'number'
  | 'triage-result';

export type TriageLevel = 'call_911' | 'notify_care_team' | 'none';

export type OverallFeeling = 'Very Happy' | 'Happy' | 'Neutral' | 'Bad' | 'Very Bad';

export interface ChatMessage {
  uuid: string;
  chat_uuid: string;
  sender: 'user' | 'assistant';
  content: string;
  message_type: MessageType;
  created_at: string;
  structured_data?: {
    options?: string[];
    options_data?: Array<{ id: string; label: string; value?: string }>;
    frontend_type?: string;
    triage_level?: TriageLevel;
    is_complete?: boolean;
  };
}

export interface ChatSession {
  chat_uuid: string;
  conversation_state: string;
  messages: ChatMessage[];
  is_new_session: boolean;
  symptom_list: string[];
  created_at?: string;
  overall_feeling?: OverallFeeling;
}

export interface WebSocketMessage {
  content: string;
  message_type: string;
  structured_data?: Record<string, unknown>;
}

export interface ChatStateResponse {
  uuid: string;
  conversation_state: string;
  symptom_list: string[];
  overall_feeling?: OverallFeeling;
  created_at: string;
}

// =============================================================================
// Chemotherapy Types
// =============================================================================

export interface ChemoLogRequest {
  chemo_date: string;  // YYYY-MM-DD format
  timezone?: string;
}

export interface ChemoLogResponse {
  success: boolean;
  message: string;
  chemo_date: string;
}

export interface ChemoDate {
  chemo_date: string;
  created_at: string;
}

// =============================================================================
// Diary Types
// =============================================================================

export interface DiaryEntry {
  entry_uuid: string;
  patient_uuid?: string;
  title: string | null;
  diary_entry: string;
  marked_for_doctor: boolean;
  is_deleted: boolean;
  created_at: string;
  last_updated_at?: string;
}

export interface DiaryEntryCreate {
  title?: string;
  diary_entry: string;
  marked_for_doctor?: boolean;
}

export interface DiaryEntryUpdate {
  title?: string;
  diary_entry?: string;
  marked_for_doctor?: boolean;
}

// =============================================================================
// Summary Types
// =============================================================================

export interface ConversationSummary {
  uuid: string;
  created_at: string;
  conversation_state: string;
  symptom_list: string[];
  bulleted_summary?: string;
  overall_feeling?: OverallFeeling;
}

export interface ConversationDetail extends ConversationSummary {
  messages?: ChatMessage[];
}

// =============================================================================
// Health Types
// =============================================================================

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down';
  timestamp?: string;
  services?: Record<string, 'ok' | 'down'>;
}





