/**
 * Profile API Service
 * ====================
 * 
 * Type-safe profile API calls.
 */

import { api } from '../client';
import { API_CONFIG } from '../../config/api';
import type { PatientProfile, PatientConfigurations } from '../types';

const { ENDPOINTS } = API_CONFIG;

export const profileApi = {
  /**
   * Get complete patient profile
   */
  getProfile: async (): Promise<PatientProfile> => {
    return api.get<PatientProfile>(ENDPOINTS.PROFILE.GET);
  },

  /**
   * Get patient info only
   */
  getInfo: async (): Promise<PatientProfile> => {
    return api.get<PatientProfile>(ENDPOINTS.PROFILE.INFO);
  },

  /**
   * Update patient configurations
   */
  updateConfig: async (config: Partial<PatientConfigurations>): Promise<PatientConfigurations> => {
    return api.patch<PatientConfigurations>(ENDPOINTS.PROFILE.CONFIG, config);
  },

  /**
   * Update consent status
   */
  updateConsent: async (agreed: boolean): Promise<void> => {
    return api.patch(ENDPOINTS.PROFILE.CONSENT, { agreed_conditions: agreed });
  },
};

export default profileApi;





