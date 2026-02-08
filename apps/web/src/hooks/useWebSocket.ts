"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { getAuthToken } from "@/lib/auth";
import toast from "react-hot-toast";
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
  priority?: "low" | "medium" | "high" | "critical";
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
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";
  notifications: WebSocketNotification[];
  lastMessage: WebSocketMessage | null;
  sendMessage: (
    message: WebSocketMessage | Record<string, unknown> | string,
  ) => void;
  clearNotifications: () => void;
  reconnect: () => void;
}

const DEFAULT_OPTIONS: UseWebSocketOptions = {
  enabled: true,
  showToasts: true,
  apiUrl: getApiBaseUrl(),
};

export function useWebSocket(
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const opts = useMemo(() => ({ ...DEFAULT_OPTIONS, ...options }), [options]);

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "disconnected" | "error"
  >("disconnected");
  const [notifications, setNotifications] = useState<WebSocketNotification[]>(
    [],
  );
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const errorLoggedRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});
  const heartbeatRef = useRef<NodeJS.Timeout | null>(null);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000; // 1 second
  const heartbeatIntervalMs = 25000;

  const getValidToken = useCallback(() => {
    const token = getAuthToken();
    if (!token) return null;
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    try {
      const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      const payload = JSON.parse(atob(normalized));
      if (payload?.exp && typeof payload.exp === "number") {
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp <= now) return null;
      }
      return token;
    } catch {
      return null;
    }
  }, []);

  const getWebSocketUrl = useCallback(() => {
    const wsOverride = process.env.NEXT_PUBLIC_WS_URL;
    if (wsOverride) {
      return wsOverride.replace(/\/$/, "");
    }
    const wsProtocol = opts.apiUrl?.startsWith("https") ? "wss" : "ws";
    const baseUrl =
      opts.apiUrl?.replace(/^https?:\/\//, "") || "localhost:8000";
    return `${wsProtocol}://${baseUrl}/api/ws`;
  }, [opts.apiUrl]);

  const showNotificationToast = useCallback(
    (notification: WebSocketNotification) => {
      if (!opts.showToasts) return;

      const message = notification.title
        ? `${notification.title}: ${notification.message}`
        : notification.message;

      switch (notification.priority) {
        case "critical":
        case "high":
          toast.error(message, { duration: 6000 });
          break;
        case "medium":
          toast(message, {
            duration: 4000,
            icon: "⚠️",
          });
          break;
        case "low":
        default:
          toast.success(message, { duration: 3000 });
          break;
      }
    },
    [opts.showToasts],
  );

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Handle different message types
        switch (message.type) {
          case "notification":
            const notification = message as WebSocketNotification;
            setNotifications((prev) => [notification, ...prev].slice(0, 50)); // Keep last 50
            showNotificationToast(notification);
            opts.onNotification?.(notification);
            break;

          case "connection.established":
            if (process.env.NODE_ENV === "development") {
              console.log(
                "[WebSocket] Connection established:",
                message.message,
              );
            }
            break;

          case "ping":
            // Respond to ping with pong
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(
                JSON.stringify({
                  type: "pong",
                  timestamp: new Date().toISOString(),
                }),
              );
            }
            break;

          case "system.alert":
            const systemAlert = message as WebSocketNotification;
            showNotificationToast(systemAlert);
            break;

          default:
            if (process.env.NODE_ENV === "development") {
              console.log("[WebSocket] Received message:", message);
            }
        }
      } catch (error) {
        if (process.env.NODE_ENV === "development") {
          console.error("[WebSocket] Failed to parse message:", error);
        }
      }
    },
    [showNotificationToast, opts],
  );

  const connect = useCallback(() => {
    if (!opts.enabled) return;
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    try {
      const token = getValidToken();
      if (!token) {
        setIsConnected(false);
        setConnectionStatus("disconnected");
        return;
      }
      const wsUrl = getWebSocketUrl();
      if (process.env.NODE_ENV === "development") {
        console.log("[WebSocket] Connecting to:", wsUrl);
      }

      setConnectionStatus("connecting");
      errorLoggedRef.current = false;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (process.env.NODE_ENV === "development") {
          console.log("[WebSocket] Connected");
        }
        setIsConnected(true);
        setConnectionStatus("connected");
        reconnectAttemptsRef.current = 0;

        // Authenticate by sending token as first message
        const authToken = getValidToken();
        if (authToken) {
          ws.send(JSON.stringify({ type: "authenticate", token: authToken }));
        }
        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current);
        }
        heartbeatRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "ping" }));
          }
        }, heartbeatIntervalMs);
        opts.onConnected?.();
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        if (!errorLoggedRef.current && process.env.NODE_ENV === "development") {
          console.warn("[WebSocket] Error:", error);
          errorLoggedRef.current = true;
        }
        errorLoggedRef.current = true;
        setConnectionStatus("error");
      };

      ws.onclose = (event) => {
        if (process.env.NODE_ENV === "development") {
          console.log("[WebSocket] Disconnected:", event.code, event.reason);
        }
        setIsConnected(false);
        setConnectionStatus("disconnected");
        wsRef.current = null;
        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current);
          heartbeatRef.current = null;
        }
        opts.onDisconnected?.();

        const shouldRetry =
          opts.enabled &&
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          event.code !== 1008; // Policy violation (likely invalid/missing token)

        // Auto-reconnect with exponential backoff
        if (shouldRetry) {
          const delay = Math.min(
            baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
            30000, // Max 30 seconds
          );
          reconnectAttemptsRef.current += 1;

          if (process.env.NODE_ENV === "development") {
            console.log(
              `[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`,
            );
          }

          reconnectTimeoutRef.current = setTimeout(() => {
            connectRef.current();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          if (process.env.NODE_ENV === "development") {
            console.error("[WebSocket] Max reconnection attempts reached");
          }
          toast.error("Lost connection to server. Please refresh the page.", {
            duration: 10000,
          });
        } else if (event.code === 1008) {
          toast.error("WebSocket authentication failed. Please log in again.", {
            duration: 8000,
          });
        }
      };

      wsRef.current = ws;
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.error("[WebSocket] Connection failed:", error);
      }
      setConnectionStatus("error");
    }
  }, [opts, getValidToken, getWebSocketUrl, handleMessage]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus("disconnected");
  }, []);

  const sendMessage = useCallback(
    (message: WebSocketMessage | Record<string, unknown> | string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const payload =
          typeof message === "string" ? message : JSON.stringify(message);
        wsRef.current.send(payload);
      } else if (process.env.NODE_ENV === "development") {
        console.warn("[WebSocket] Cannot send message: not connected");
      }
    },
    [],
  );

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(() => connect(), 100);
  }, [connect, disconnect]);

  useEffect(() => {
    let frameId: number | null = null;
    if (opts.enabled) {
      frameId = requestAnimationFrame(() => connect());
    }

    return () => {
      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }
      disconnect();
    };
  }, [opts.enabled, connect, disconnect]);

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
