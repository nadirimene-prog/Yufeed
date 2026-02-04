'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { useWebSocket, UseWebSocketReturn } from '@/hooks/useWebSocket';
import { useApiHealth } from '@/hooks/useApiHealth';

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
  const websocket = useWebSocket({
    enabled: enabled && isApiHealthy,
    showToasts: true,
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
