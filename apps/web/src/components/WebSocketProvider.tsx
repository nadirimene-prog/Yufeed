'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { useQueryClient } from "@tanstack/react-query";
import { useWebSocket, UseWebSocketReturn } from '@/hooks/useWebSocket';
import { useApiHealth } from '@/hooks/useApiHealth';
import { complianceKeys, monitoringKeys } from "@/lib/queryKeys";

/**
 * WebSocket Provider and Context
 * Phase 4B: Task 6.3 - Frontend WebSocket Integration
 *
 * Provides WebSocket connection and notifications throughout the app
 */

const WebSocketContext = createContext<UseWebSocketReturn | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
  enabled?: boolean;
}

export function WebSocketProvider({ children, enabled = true }: WebSocketProviderProps) {
  const { status } = useApiHealth();
  const isApiHealthy = status === "ok";
  const queryClient = useQueryClient();
  const websocket = useWebSocket({
    enabled: enabled && isApiHealthy,
    showToasts: true,
    onNotification: (notification) => {
      const eventType = notification.event_type || "";

      // Compliance events are globally shared by design.
      if (eventType.startsWith("obligation.") || eventType === "internal_rule.created") {
        queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
      }
      if (eventType.startsWith("policy.")) {
        queryClient.invalidateQueries({ queryKey: complianceKeys.policies() });
      }
      if (eventType.startsWith("risk.")) {
        queryClient.invalidateQueries({ queryKey: complianceKeys.risk() });
      }

      // Tenant-scoped monitoring events. The backend ensures tenant isolation per WS connection.
      if (eventType.startsWith("alert.")) {
        queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts() });
      }
      if (eventType.startsWith("case.")) {
        queryClient.invalidateQueries({ queryKey: monitoringKeys.cases() });
      }
      if (eventType.startsWith("transaction.")) {
        queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts() });
      }
    },
    onConnected: () => {
      console.log('[WebSocketProvider] Connected to real-time notifications');
    },
    onDisconnected: () => {
      console.log('[WebSocketProvider] Disconnected from real-time notifications');
    },
  });

  return (
    <WebSocketContext.Provider value={websocket}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocketContext(): UseWebSocketReturn {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider');
  }
  return context;
}

// Optional: export a version that doesn't throw if used outside provider
export function useOptionalWebSocket(): UseWebSocketReturn | null {
  return useContext(WebSocketContext);
}
