/**
 * Diary API Service
 * ==================
 * 
 * Type-safe diary entry API calls.
 */

import { api } from '../client';
import { API_CONFIG } from '../../config/api';
import type { DiaryEntry, DiaryEntryCreate, DiaryEntryUpdate } from '../types';

const { ENDPOINTS } = API_CONFIG;

export const diaryApi = {
  /**
   * Get all diary entries
   */
  getAll: async (timezone: string = 'America/Los_Angeles'): Promise<DiaryEntry[]> => {
    return api.get<DiaryEntry[]>(`${ENDPOINTS.DIARY.LIST}?timezone=${timezone}`);
  },

  /**
   * Get diary entries by month
   */
  getByMonth: async (
    year: number,
    month: number,
    timezone: string = 'America/Los_Angeles'
  ): Promise<DiaryEntry[]> => {
    return api.get<DiaryEntry[]>(
      `${ENDPOINTS.DIARY.BY_MONTH(year, month)}?timezone=${timezone}`
    );
  },

  /**
   * Create a new diary entry
   */
  create: async (entry: DiaryEntryCreate): Promise<DiaryEntry> => {
    return api.post<DiaryEntry>(ENDPOINTS.DIARY.CREATE, entry);
  },

  /**
   * Update an existing diary entry
   */
  update: async (
    entryUuid: string,
    updates: DiaryEntryUpdate,
    timezone: string = 'America/Los_Angeles'
  ): Promise<DiaryEntry> => {
    return api.patch<DiaryEntry>(
      `${ENDPOINTS.DIARY.UPDATE(entryUuid)}?timezone=${timezone}`,
      updates
    );
  },

  /**
   * Soft delete a diary entry
   */
  delete: async (entryUuid: string): Promise<void> => {
    return api.patch(ENDPOINTS.DIARY.DELETE(entryUuid));
  },
};

export default diaryApi;





