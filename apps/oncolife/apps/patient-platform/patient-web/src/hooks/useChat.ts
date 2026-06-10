/**
 * useChat Hook
 * =============
 * 
 * Chat/Symptom Checker hook for managing chat state and WebSocket connection.
 * 
 * Features:
 * - Session management
 * - Real-time messaging via WebSocket
 * - Message handling
 * - Connection state management
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { chatApi, chatWebSocket } from '../api';
import type { ChatSession, ChatMessage, WebSocketMessage, OverallFeeling } from '../api/types';

interface ChatState {
  session: ChatSession | null;
  messages: ChatMessage[];
  isLoading: boolean;
  isConnected: boolean;
  isSending: boolean;
  error: string | null;
}

interface UseChatOptions {
  patientUuid: string;
  timezone?: string;
  autoConnect?: boolean;
}

interface UseChatReturn extends ChatState {
  loadSession: () => Promise<ChatSession | null>;
  createNewSession: () => Promise<ChatSession | null>;
  sendMessage: (content: string, messageType?: string, structuredData?: Record<string, unknown>) => void;
  updateFeeling: (feeling: OverallFeeling) => Promise<void>;
  connect: () => void;
  disconnect: () => void;
  clearError: () => void;
}

export function useChat(options: UseChatOptions): UseChatReturn {
  const { patientUuid, timezone = 'America/Los_Angeles', autoConnect = true } = options;
  
  const [state, setState] = useState<ChatState>({
    session: null,
    messages: [],
    isLoading: true,
    isConnected: false,
    isSending: false,
    error: null,
  });

  const socketRef = useRef<WebSocket | null>(null);

  // Load or create today's session
  const loadSession = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const session = await chatApi.getOrCreateSession(patientUuid, timezone);
      setState(prev => ({
        ...prev,
        session,
        messages: session.messages || [],
        isLoading: false,
      }));
      return session;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load session';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
      return null;
    }
  }, [patientUuid, timezone]);

  // Create a fresh session
  const createNewSession = useCallback(async () => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const session = await chatApi.createNewSession(patientUuid, timezone);
      setState(prev => ({
        ...prev,
        session,
        messages: session.messages || [],
        isLoading: false,
      }));

      // Reconnect WebSocket if was connected
      if (state.isConnected && session.chat_uuid) {
        disconnect();
        setTimeout(() => connect(), 100);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create session';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: message,
      }));
    }
  }, [patientUuid, timezone, state.isConnected]);

  // Handle incoming messages
  const handleMessage = useCallback((message: ChatMessage) => {
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, message],
      isSending: false,
    }));
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!state.session?.chat_uuid) {
      console.warn('[useChat] No session to connect to');
      return;
    }

    try {
      socketRef.current = chatWebSocket.connect(state.session.chat_uuid, {
        onMessage: handleMessage,
        onOpen: () => {
          setState(prev => ({ ...prev, isConnected: true }));
        },
        onClose: () => {
          setState(prev => ({ ...prev, isConnected: false }));
        },
        onError: () => {
          setState(prev => ({
            ...prev,
            isConnected: false,
            error: 'Connection error',
          }));
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to connect';
      setState(prev => ({ ...prev, error: message }));
    }
  }, [state.session?.chat_uuid, handleMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    chatWebSocket.disconnect();
    setState(prev => ({ ...prev, isConnected: false }));
  }, []);

  // Send a message
  const sendMessage = useCallback((
    content: string,
    messageType: string = 'text',
    structuredData?: Record<string, unknown>
  ) => {
    if (!state.isConnected) {
      console.warn('[useChat] Not connected, cannot send message');
      return;
    }

    const message: WebSocketMessage = {
      content,
      message_type: messageType,
      structured_data: structuredData,
    };

    const sent = chatWebSocket.send(message);
    if (sent) {
      setState(prev => ({ ...prev, isSending: true }));
    }
  }, [state.isConnected]);

  // Update overall feeling
  const updateFeeling = useCallback(async (feeling: OverallFeeling) => {
    if (!state.session?.chat_uuid) return;

    try {
      await chatApi.updateOverallFeeling(
        state.session.chat_uuid,
        patientUuid,
        feeling
      );
      setState(prev => ({
        ...prev,
        session: prev.session ? { ...prev.session, overall_feeling: feeling } : null,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update feeling';
      setState(prev => ({ ...prev, error: message }));
    }
  }, [state.session?.chat_uuid, patientUuid]);

  // Clear error
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Load session on mount
  useEffect(() => {
    loadSession();
  }, [loadSession]);

  // Auto-connect when session is ready
  useEffect(() => {
    if (autoConnect && state.session?.chat_uuid && !state.isConnected) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [state.session?.chat_uuid, autoConnect]);

  return {
    ...state,
    loadSession,
    createNewSession,
    sendMessage,
    updateFeeling,
    connect,
    disconnect,
    clearError,
  };
}

export default useChat;





