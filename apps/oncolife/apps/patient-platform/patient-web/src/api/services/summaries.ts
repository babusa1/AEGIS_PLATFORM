/**
 * Summaries API Service
 * ======================
 * 
 * Type-safe conversation summary API calls.
 */

import { api } from '../client';
import { API_CONFIG } from '../../config/api';
import type { ConversationSummary, ConversationDetail } from '../types';

const { ENDPOINTS } = API_CONFIG;

export const summariesApi = {
  /**
   * Get summaries by month
   */
  getByMonth: async (
    year: number,
    month: number,
    timezone: string = 'America/Los_Angeles'
  ): Promise<ConversationSummary[]> => {
    return api.get<ConversationSummary[]>(
      `${ENDPOINTS.SUMMARIES.BY_MONTH(year, month)}?timezone=${timezone}`
    );
  },

  /**
   * Get detailed summary for a conversation
   */
  getDetail: async (
    conversationUuid: string,
    timezone: string = 'America/Los_Angeles'
  ): Promise<ConversationDetail> => {
    return api.get<ConversationDetail>(
      `${ENDPOINTS.SUMMARIES.DETAIL(conversationUuid)}?timezone=${timezone}`
    );
  },
};

export default summariesApi;





