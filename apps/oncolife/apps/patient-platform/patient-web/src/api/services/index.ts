/**
 * API Services Index
 * ===================
 * 
 * Centralized export of all API services.
 * 
 * Usage:
 *   import { authApi, chatApi, profileApi, onboardingApi } from '@/api/services';
 *   
 *   const profile = await profileApi.getProfile();
 *   const status = await onboardingApi.getOnboardingStatus();
 */

export { authApi } from './auth';
export { chatApi, chatWebSocket } from './chat';
export { profileApi } from './profile';
export { diaryApi } from './diary';
export { chemoApi } from './chemo';
export { summariesApi } from './summaries';
export { default as onboardingApi } from './onboarding';
export * from './onboarding';

