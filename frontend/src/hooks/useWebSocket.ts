/**
 * WebSocket Hook for Real-Time Updates
 *
 * Provides WebSocket connection management with:
 * - Auto-reconnection with exponential backoff
 * - Heartbeat mechanism
 * - Channel subscriptions
 * - Type-safe event handling
 */

import { useEffect, useRef, useState, useCallback } from 'react';

// Event types matching backend
export enum EventType {
  TRANSACTION_NEW = 'transaction.new',
  TRANSACTION_UPDATED = 'transaction.updated',
  ALERT_CREATED = 'alert.created',
  ALERT_UPDATED = 'alert.updated',
  ALERT_ASSIGNED = 'alert.assigned',
  ALERT_RESOLVED = 'alert.resolved',
  ALERT_ESCALATED = 'alert.escalated',
  SYSTEM_HEALTH = 'system.health',
  METRICS_UPDATE = 'metrics.update',
  CONNECTION_ESTABLISHED = 'connection.established',
  PONG = 'pong',
  PING = 'ping',
}

export interface WebSocketEvent<T = any> {
  event_type: EventType | string;
  timestamp: string;
  data: T;
}

export interface MetricsData {
  transactions_per_minute: number;
  active_alerts: number;
  critical_alerts: number;
  pending_reviews: number;
  sars_this_month: number;
  false_positive_rate: number;
  geographic_distribution?: Array<{
    country_code: string;
    count: number;
    total_amount: number;
  }>;
}

export interface SystemHealthData {
  services: Record<string, { status: string; latency_ms: number }>;
  uptime_percentage: number;
  latency: {
    p50: number;
    p95: number;
    p99: number;
  };
  queue_depth: number;
}

export interface AlertEventData {
  alert_id: string;
  alert_type: string;
  severity: string;
  user_id: string;
  description?: string;
  ai_confidence?: number;
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseWebSocketOptions {
  url?: string;
  token?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

interface UseWebSocketReturn {
  status: ConnectionStatus;
  connect: () => void;
  disconnect: () => void;
  subscribe: (channels: string[]) => void;
  unsubscribe: (channels: string[]) => void;
  sendMessage: (message: any) => void;
  lastEvent: WebSocketEvent | null;
  isConnected: boolean;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/realtime/ws`,
    token,
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectInterval = 1000,
    heartbeatInterval = 25000,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const heartbeatTimer = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  // Clear timers
  const clearTimers = useCallback(() => {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current);
      heartbeatTimer.current = null;
    }
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
  }, []);

  // Start heartbeat
  const startHeartbeat = useCallback(() => {
    clearTimers();
    heartbeatTimer.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval, clearTimers]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus('connecting');

    const wsUrl = token ? `${url}?token=${token}` : url;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setStatus('connected');
      reconnectCount.current = 0;
      startHeartbeat();
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);
        setLastEvent(data);
        onMessage?.(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      clearTimers();
      onDisconnect?.();

      // Auto-reconnect with exponential backoff
      if (reconnectCount.current < reconnectAttempts) {
        const delay = Math.min(
          reconnectInterval * Math.pow(2, reconnectCount.current),
          30000
        );
        reconnectTimer.current = setTimeout(() => {
          reconnectCount.current++;
          connect();
        }, delay);
      }
    };

    ws.onerror = (error) => {
      setStatus('error');
      onError?.(error);
    };

    wsRef.current = ws;
  }, [url, token, reconnectAttempts, reconnectInterval, startHeartbeat, clearTimers, onConnect, onDisconnect, onMessage, onError]);

  // Disconnect
  const disconnect = useCallback(() => {
    clearTimers();
    reconnectCount.current = reconnectAttempts; // Prevent auto-reconnect
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [clearTimers, reconnectAttempts]);

  // Subscribe to channels
  const subscribe = useCallback((channels: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        channels,
      }));
    }
  }, []);

  // Unsubscribe from channels
  const unsubscribe = useCallback((channels: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        channels,
      }));
    }
  }, []);

  // Send arbitrary message
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    status,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    sendMessage,
    lastEvent,
    isConnected: status === 'connected',
  };
}

/**
 * Hook for specific event type listening
 */
export function useWebSocketEvent<T = any>(
  eventType: EventType | string,
  callback: (data: T) => void
) {
  const { lastEvent } = useWebSocket();

  useEffect(() => {
    if (lastEvent?.event_type === eventType) {
      callback(lastEvent.data as T);
    }
  }, [lastEvent, eventType, callback]);
}

export default useWebSocket;
