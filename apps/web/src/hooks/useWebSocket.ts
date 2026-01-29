'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { getAuthToken } from '@/lib/auth';
import toast from 'react-hot-toast';
import { getApiBaseUrl } from "@/lib/apiBaseUrl";

/**
 * WebSocket hook for real-time notifications
 * Phase 4B: Task 6.3 - Frontend WebSocket Integration
 *
 * Features:
 * - Auto-connect on mount with JWT authentication
 * - Auto-reconnect on disconnect with exponential backoff
 * - Event-based notification handling
 * - Connection status tracking
 * - Heartbeat/ping-pong support
 */

export interface WebSocketNotificationData {
  alert_id?: string;
  case_id?: string;
  rule_id?: string;
  document_celex?: string;
  [key: string]: unknown;
}

export interface WebSocketNotification {
  type: string;
  event_type: string;
  title?: string;
  message: string;
  data?: WebSocketNotificationData;
  timestamp: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  link?: string;
}

export interface WebSocketMessage {
  type: string;
  event_type?: string;
  message?: string;
  data?: WebSocketNotificationData;
  timestamp?: string;
}

export interface UseWebSocketOptions {
  enabled?: boolean;
  onNotification?: (notification: WebSocketNotification) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  showToasts?: boolean;
  apiUrl?: string;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  notifications: WebSocketNotification[];
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  clearNotifications: () => void;
  reconnect: () => void;
}

const DEFAULT_OPTIONS: UseWebSocketOptions = {
  enabled: true,
  showToasts: true,
  apiUrl: getApiBaseUrl(),
};

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [notifications, setNotifications] = useState<WebSocketNotification[]>([]);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000; // 1 second

  const getValidToken = useCallback(() => {
    const token = getAuthToken();
    if (!token) return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    try {
      const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(atob(normalized));
      if (payload?.exp && typeof payload.exp === 'number') {
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp <= now) return null;
      }
      return token;
    } catch {
      return null;
    }
  }, []);

  const getWebSocketUrl = useCallback(() => {
    const token = getValidToken();
    const wsProtocol = opts.apiUrl?.startsWith('https') ? 'wss' : 'ws';
    const baseUrl = opts.apiUrl?.replace(/^https?:\/\//, '') || 'localhost:8000';
    return `${wsProtocol}://${baseUrl}/ws${token ? `?token=${token}` : ''}`;
  }, [opts.apiUrl, getValidToken]);

  const showNotificationToast = useCallback((notification: WebSocketNotification) => {
    if (!opts.showToasts) return;

    const message = notification.title
      ? `${notification.title}: ${notification.message}`
      : notification.message;

    switch (notification.priority) {
      case 'critical':
      case 'high':
        toast.error(message, { duration: 6000 });
        break;
      case 'medium':
        toast(message, {
          duration: 4000,
          icon: '⚠️',
        });
        break;
      case 'low':
      default:
        toast.success(message, { duration: 3000 });
        break;
    }
  }, [opts.showToasts]);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(message);

      // Handle different message types
      switch (message.type) {
        case 'notification':
          const notification = message as WebSocketNotification;
          setNotifications(prev => [notification, ...prev].slice(0, 50)); // Keep last 50
          showNotificationToast(notification);
          opts.onNotification?.(notification);
          break;

        case 'connection.established':
          console.log('[WebSocket] Connection established:', message.message);
          break;

        case 'ping':
          // Respond to ping with pong
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
          }
          break;

        case 'system.alert':
          const systemAlert = message as WebSocketNotification;
          showNotificationToast(systemAlert);
          break;

        default:
          console.log('[WebSocket] Received message:', message);
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error);
    }
  }, [showNotificationToast, opts]);

  const connect = useCallback(() => {
    if (!opts.enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      const token = getValidToken();
      if (!token) {
        setIsConnected(false);
        setConnectionStatus('disconnected');
        return;
      }
      const wsUrl = getWebSocketUrl();
      console.log('[WebSocket] Connecting to:', wsUrl.replace(/token=[^&]+/, 'token=***'));

      setConnectionStatus('connecting');
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        opts.onConnected?.();
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setConnectionStatus('error');
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        wsRef.current = null;
        opts.onDisconnected?.();

        // Auto-reconnect with exponential backoff
        if (opts.enabled && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
            30000 // Max 30 seconds
          );
          reconnectAttemptsRef.current += 1;

          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('[WebSocket] Max reconnection attempts reached');
          toast.error('Lost connection to server. Please refresh the page.', { duration: 10000 });
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      setConnectionStatus('error');
    }
  }, [opts, getWebSocketUrl, handleMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message: not connected');
    }
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(() => connect(), 100);
  }, [connect, disconnect]);

  // Connect on mount
  // eslint-disable-next-line react-hooks/exhaustive-deps -- Intentionally limited deps:
  // We only want to reconnect when `enabled` changes, not when callbacks update.
  // Including connect/disconnect would cause infinite reconnection loops.
  useEffect(() => {
    if (opts.enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [opts.enabled]);

  return {
    isConnected,
    connectionStatus,
    notifications,
    lastMessage,
    sendMessage,
    clearNotifications,
    reconnect,
  };
}