/**
 * Onboarding API Service
 * 
 * Handles all onboarding-related API calls:
 * - Get onboarding status
 * - Complete password step
 * - Complete acknowledgement step
 * - Complete terms/privacy step
 * - Complete reminder setup
 */

import apiClient from '../client';
import { API_CONFIG } from '../../config/api';

// ============================================================================
// TYPES
// ============================================================================

export interface OnboardingStatus {
  is_onboarded: boolean;
  current_step: string | null;
  steps: {
    password_reset: boolean;
    acknowledgement: boolean;
    terms_privacy: boolean;
    reminder_setup: boolean;
  } | null;
  first_login_at: string | null;
  onboarding_completed_at: string | null;
}

export interface StepCompletionResponse {
  success: boolean;
  message: string;
  next_step?: string;
}

export interface AcknowledgementRequest {
  acknowledged: boolean;
  acknowledgement_text: string;
}

export interface TermsPrivacyRequest {
  terms_accepted: boolean;
  privacy_accepted: boolean;
  hipaa_acknowledged: boolean;
}

export interface ReminderSetupRequest {
  channel: 'email' | 'sms' | 'both';
  email?: string;
  phone?: string;
  reminder_time?: string;
  timezone?: string;
}

export interface ReminderCompletionResponse extends StepCompletionResponse {
  is_onboarded: boolean;
  redirect_to: string;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Get current onboarding status
 */
export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const response = await apiClient.get<OnboardingStatus>(
    `${API_CONFIG.ENDPOINTS.ONBOARDING}/status`
  );
  return response.data;
}

/**
 * Complete password reset step
 * Call this after successfully changing the temp password
 */
export async function completePasswordStep(): Promise<StepCompletionResponse> {
  const response = await apiClient.post<StepCompletionResponse>(
    `${API_CONFIG.ENDPOINTS.ONBOARDING}/complete/password`
  );
  return response.data;
}

/**
 * Complete acknowledgement step
 */
export async function completeAcknowledgementStep(
  data: AcknowledgementRequest
): Promise<StepCompletionResponse> {
  const response = await apiClient.post<StepCompletionResponse>(
    `${API_CONFIG.ENDPOINTS.ONBOARDING}/complete/acknowledgement`,
    data
  );
  return response.data;
}

/**
 * Complete terms and privacy step
 */
export async function completeTermsStep(
  data: TermsPrivacyRequest
): Promise<StepCompletionResponse> {
  const response = await apiClient.post<StepCompletionResponse>(
    `${API_CONFIG.ENDPOINTS.ONBOARDING}/complete/terms`,
    data
  );
  return response.data;
}

/**
 * Complete reminder setup and finalize onboarding
 */
export async function completeReminderStep(
  data: ReminderSetupRequest
): Promise<ReminderCompletionResponse> {
  const response = await apiClient.post<ReminderCompletionResponse>(
    `${API_CONFIG.ENDPOINTS.ONBOARDING}/complete/reminders`,
    data
  );
  return response.data;
}

// Default export for convenience
const onboardingService = {
  getOnboardingStatus,
  completePasswordStep,
  completeAcknowledgementStep,
  completeTermsStep,
  completeReminderStep,
};

export default onboardingService;





