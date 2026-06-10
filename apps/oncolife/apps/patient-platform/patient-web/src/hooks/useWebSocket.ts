import { useEffect, useRef, useState, useCallback } from 'react';
import { API_CONFIG } from '../config/api';

export const useWebSocket = (
  chatUuid: string | null,
  onMessage: (message: unknown) => void
) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  // Keep the latest onMessage in a ref so we don't recreate the socket on every re-render
  const onMessageRef = useRef(onMessage);
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connectWebSocket = useCallback(() => {
    if (!chatUuid) return;

    // Guard: do not create another socket if one already exists
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const token = localStorage.getItem('authToken');
    if (!token) {
      setConnectionError("Authentication token not found.");
      return;
    }

    // Prefer explicit WS_BASE if provided (absolute URL supported), else base URL
    const base = API_CONFIG.WS_BASE || API_CONFIG.BASE_URL;
    let wsUrl: string;

    // Always include /api/v1 prefix for WebSocket
    const apiVersion = API_CONFIG.API_VERSION || '/api/v1';
    
    if (/^wss?:\/\//i.test(base)) {
      // Absolute ws(s) base provided directly
      wsUrl = `${base.replace(/\/$/, '')}${apiVersion}/chat/ws/${chatUuid}?token=${token}`;
    } else if (/^https?:\/\//i.test(base)) {
      // Absolute API/WS base → convert http(s) → ws(s)
      const wsBase = base.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:');
      wsUrl = `${wsBase.replace(/\/$/, '')}${apiVersion}/chat/ws/${chatUuid}?token=${token}`;
    } else {
      // Relative base → same-origin
      const { protocol, host } = window.location as any;
      const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
      const prefix = base === '/' ? '' : base.replace(/\/$/, '');
      wsUrl = `${wsProtocol}//${host}${prefix}${apiVersion}/chat/ws/${chatUuid}?token=${token}`;
    }

    console.log('Connecting to WebSocket:', wsUrl);
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connection established.');
      setIsConnected(true);
      setConnectionError(null);
      retryCountRef.current = 0; // Reset retry count on successful connection
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Always use the latest handler without forcing a reconnect
        onMessageRef.current?.(data);
      } catch (e) {
        console.error('Failed to parse WS message', e);
      }
    };

    wsRef.current.onerror = () => {
      setConnectionError('WebSocket error occurred.');
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      if (retryCountRef.current < maxRetries) {
        retryCountRef.current += 1;
        retryTimeoutRef.current = setTimeout(connectWebSocket, 1000 * retryCountRef.current);
      } else {
        setConnectionError('Failed to connect to chat.');
      }
    };
  }, [chatUuid]);

  const sendMessage = useCallback((
    content: string,
    message_type: 'text' | 'button_response' | 'multi_select_response' | 'feeling_response'
  ) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const payload = {
        type: 'user_message',
        message_type,
        content,
      };
      wsRef.current.send(JSON.stringify(payload));
    } else {
      console.error('Cannot send message, WebSocket is not open.');
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onmessage = null;
        wsRef.current.onerror = null;
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [connectWebSocket]);

  return {
    isConnected,
    connectionError,
    sendMessage,
  };
};