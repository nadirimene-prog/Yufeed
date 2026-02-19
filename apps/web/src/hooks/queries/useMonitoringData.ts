"use client";

import { useQuery } from "@tanstack/react-query";
import { getMonitoringAlerts, getMonitoringCases } from "@/lib/monitoring-api";
import { monitoringKeys } from "@/lib/queryKeys";

export function useMonitoringAlerts(params?: {
  limit?: number;
  status?: string;
  severity?: string;
  include_snoozed?: boolean;
}) {
  const queryParams = {
    limit: params?.limit ?? 50,
    ...(params?.status ? { status: params.status } : {}),
    ...(params?.severity ? { severity: params.severity } : {}),
    ...(typeof params?.include_snoozed === "boolean"
      ? { include_snoozed: params.include_snoozed }
      : {}),
  };

  return useQuery({
    queryKey: monitoringKeys.alertsList(queryParams),
    queryFn: () => getMonitoringAlerts(queryParams),
  });
}

export function useMonitoringCases(params?: {
  limit?: number;
  status?: string;
  priority?: string;
}) {
  const queryParams = {
    limit: params?.limit ?? 50,
    ...(params?.status ? { status: params.status } : {}),
    ...(params?.priority ? { priority: params.priority } : {}),
  };

  return useQuery({
    queryKey: monitoringKeys.casesList(queryParams),
    queryFn: () => getMonitoringCases(queryParams),
  });
}
