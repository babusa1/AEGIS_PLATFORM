import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

export const patientService = {
  updateConsent: async () => {
    const response = await apiClient.patch(API_CONFIG.ENDPOINTS.PROFILE.CONSENT, {
      agreed_conditions: true,
      acknowledgement_done: true,
    });
    return response.data;
  },
};

