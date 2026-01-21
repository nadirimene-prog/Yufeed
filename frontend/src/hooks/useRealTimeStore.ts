/**
 * Real-Time State Store
 *
 * Zustand store for managing real-time data from WebSocket
 * and REST API endpoints.
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

// Types
export interface LiveMetrics {
  transactions_per_minute: number;
  active_alerts: number;
  critical_alerts: number;
  pending_reviews: number;
  sars_this_month: number;
  false_positive_rate: number;
  high_risk_users: number;
  open_cases: number;
  timestamp: string;
}

export interface SystemHealth {
  overall_status: 'operational' | 'degraded' | 'partial' | 'down';
  uptime_percentage: number;
  services: Record<string, {
    status: string;
    latency_ms: number;
  }>;
  latency: {
    p50: number;
    p95: number;
    p99: number;
  };
  queue: {
    alert_queue: number;
    triage_queue: number;
    sar_queue: number;
  };
}

export interface GeoDistribution {
  country_code: string;
  count: number;
  total_amount: number;
  avg_risk_score: number;
  is_high_risk: boolean;
}

export interface RecentAlert {
  alert_id: string;
  alert_type: string;
  severity: string;
  status: string;
  user_id: string;
  created_at: string;
  description?: string;
}

export interface ConnectionStatus {
  websocket: 'connected' | 'connecting' | 'disconnected' | 'error';
  lastUpdate: string | null;
}

interface RealTimeState {
  // Data
  metrics: LiveMetrics | null;
  systemHealth: SystemHealth | null;
  geoDistribution: GeoDistribution[];
  recentAlerts: RecentAlert[];
  connectionStatus: ConnectionStatus;

  // Actions
  setMetrics: (metrics: LiveMetrics) => void;
  setSystemHealth: (health: SystemHealth) => void;
  setGeoDistribution: (distribution: GeoDistribution[]) => void;
  addRecentAlert: (alert: RecentAlert) => void;
  setRecentAlerts: (alerts: RecentAlert[]) => void;
  setConnectionStatus: (status: Partial<ConnectionStatus>) => void;
  reset: () => void;
}

const initialState = {
  metrics: null,
  systemHealth: null,
  geoDistribution: [],
  recentAlerts: [],
  connectionStatus: {
    websocket: 'disconnected' as const,
    lastUpdate: null,
  },
};

export const useRealTimeStore = create<RealTimeState>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    setMetrics: (metrics) =>
      set({
        metrics,
        connectionStatus: {
          ...get().connectionStatus,
          lastUpdate: new Date().toISOString(),
        },
      }),

    setSystemHealth: (systemHealth) =>
      set({ systemHealth }),

    setGeoDistribution: (geoDistribution) =>
      set({ geoDistribution }),

    addRecentAlert: (alert) =>
      set((state) => ({
        recentAlerts: [alert, ...state.recentAlerts.slice(0, 49)],
      })),

    setRecentAlerts: (recentAlerts) =>
      set({ recentAlerts }),

    setConnectionStatus: (status) =>
      set((state) => ({
        connectionStatus: {
          ...state.connectionStatus,
          ...status,
        },
      })),

    reset: () => set(initialState),
  }))
);

// Selectors
export const selectMetrics = (state: RealTimeState) => state.metrics;
export const selectSystemHealth = (state: RealTimeState) => state.systemHealth;
export const selectGeoDistribution = (state: RealTimeState) => state.geoDistribution;
export const selectRecentAlerts = (state: RealTimeState) => state.recentAlerts;
export const selectConnectionStatus = (state: RealTimeState) => state.connectionStatus;

// Derived selectors
export const selectIsConnected = (state: RealTimeState) =>
  state.connectionStatus.websocket === 'connected';

export const selectCriticalAlertCount = (state: RealTimeState) =>
  state.metrics?.critical_alerts ?? 0;

export const selectPendingReviewCount = (state: RealTimeState) =>
  state.metrics?.pending_reviews ?? 0;

export default useRealTimeStore;
