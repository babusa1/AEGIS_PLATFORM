import { getUserTimezone } from '@oncolife/shared-utils';
import { apiClient } from '../utils/apiClient';
import { API_CONFIG } from '../config/api';

export const chatService = {
  getTodaySession: async () => {
    const timezone = getUserTimezone();
    const response = await apiClient.get(
      `${API_CONFIG.ENDPOINTS.CHAT.SESSION_TODAY}?timezone=${encodeURIComponent(timezone)}`
    );
    return { success: true, status: response.status, data: response.data };
  },

  sendMessage: async (chatUuid: string, content: string) => {
    // Use WebSocket for sending messages - this is just a fallback REST endpoint
    const response = await apiClient.post(`/chat/${chatUuid}/message`, {
      chat_uuid: chatUuid,
      content,
    });
    return response.data;
  },

  startNewSession: async () => {
    const timezone = getUserTimezone();
    const response = await apiClient.post(
      `${API_CONFIG.ENDPOINTS.CHAT.SESSION_NEW}?timezone=${encodeURIComponent(timezone)}`
    );
    return response.data;
  },

  logChemoDate: async (chemoDate: Date) => {
    const timezone = getUserTimezone();
    const response = await apiClient.post(API_CONFIG.ENDPOINTS.CHEMO.LOG, {
      chemo_date: chemoDate.toISOString().split('T')[0],
      timezone,
    });
    return response.data;
  },
};
