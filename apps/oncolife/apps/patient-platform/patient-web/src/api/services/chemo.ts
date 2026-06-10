/**
 * Chemotherapy API Service
 * =========================
 * 
 * Type-safe chemotherapy tracking API calls.
 */

import { api } from '../client';
import { API_CONFIG } from '../../config/api';
import type { ChemoLogRequest, ChemoLogResponse, ChemoDate } from '../types';

const { ENDPOINTS } = API_CONFIG;

export const chemoApi = {
  /**
   * Log a new chemotherapy date
   */
  logChemoDate: async (request: ChemoLogRequest): Promise<ChemoLogResponse> => {
    return api.post<ChemoLogResponse>(ENDPOINTS.CHEMO.LOG, request);
  },

  /**
   * Get all chemotherapy history
   */
  getHistory: async (): Promise<ChemoDate[]> => {
    return api.get<ChemoDate[]>(ENDPOINTS.CHEMO.HISTORY);
  },

  /**
   * Get chemotherapy dates by month
   */
  getByMonth: async (year: number, month: number): Promise<ChemoDate[]> => {
    return api.get<ChemoDate[]>(ENDPOINTS.CHEMO.BY_MONTH(year, month));
  },
};

export default chemoApi;





