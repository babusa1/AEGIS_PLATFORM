export interface SymptomGroup {
  name: string;
  icon: string;
  symptoms: { id: string; name: string; available?: boolean }[];
}

export interface SummaryData {
  symptoms_assessed?: { id: string; name: string }[];
  triage_results?: Array<{
    symptom_name: string;
    level: string;
    message?: string;
  }>;
  highest_level?: string;
}

export interface Message {
  id: number;
  chat_uuid: string;
  sender: 'user' | 'assistant' | 'ruby' | 'system';
  message_type: 
    | 'text' 
    | 'button_response' 
    | 'multi_select_response' 
    | 'single-select' 
    | 'multi-select' 
    | 'button-prompt'
    | 'button_prompt' 
    | 'feeling-select' 
    | 'feeling_response'
    | 'symptom-select'
    | 'symptom_select'
    | 'yes_no'
    | 'choice'
    | 'multiselect'
    | 'number'
    | 'triage_result'
    | 'disclaimer'
    | 'emergency_check'
    | 'emergency'
    | 'summary';
  content: string;
  structured_data?: {
    options?: string[];
    options_data?: Array<{ label: string; value: any; category?: string; style?: string; action?: string }>;
    selected_options?: string[];
    max_selections?: number;
    frontend_type?: string;
    triage_level?: 'call_911' | 'notify_care_team' | 'urgent' | 'none';
    is_complete?: boolean;
    // Symptom checker specific fields
    symptom_groups?: Record<string, SymptomGroup>;
    sender?: 'ruby' | 'system' | 'user';
    avatar?: string;
    summary_data?: SummaryData;
  };
  created_at: string;
}

export interface ChatSession {
  chat_uuid: string;
  conversation_state: string;
  messages: Message[];
  is_new_session: boolean;
  symptom_list: string[];  // Add symptom list from backend
}

export type ResponseType = 'text' | 'button_prompt' | 'multi_select' | 'button_response' | 'multi_select_response' | 'feeling-select' | 'feeling_response'; 