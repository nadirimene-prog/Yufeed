import apiClient from "@/lib/http";
import type { MonitoringAlert, MonitoringCase } from "@/types/monitoring";

export async function getMonitoringAlerts(params?: {
  limit?: number;
  status?: string;
  severity?: string;
  include_snoozed?: boolean;
}): Promise<MonitoringAlert[]> {
  const status =
    typeof params?.status === "string" && params.status.length > 0
      ? params.status
      : null;
  const severity =
    typeof params?.severity === "string" && params.severity.length > 0
      ? params.severity
      : null;
  const includeSnoozed =
    typeof params?.include_snoozed === "boolean"
      ? params.include_snoozed
      : null;
  const response = await apiClient.get<MonitoringAlert[]>("/api/alerts/", {
    params: {
      limit: params?.limit ?? 50,
      ...(status !== null ? { status } : {}),
      ...(severity !== null ? { severity } : {}),
      ...(includeSnoozed !== null ? { include_snoozed: includeSnoozed } : {}),
    },
  });

  return response.data;
}

export async function getMonitoringCases(params?: {
  limit?: number;
  status?: string;
  priority?: string;
}): Promise<MonitoringCase[]> {
  const status =
    typeof params?.status === "string" && params.status.length > 0
      ? params.status
      : null;
  const priority =
    typeof params?.priority === "string" && params.priority.length > 0
      ? params.priority
      : null;
  const response = await apiClient.get<MonitoringCase[]>("/api/cases/", {
    params: {
      limit: params?.limit ?? 50,
      ...(status !== null ? { status } : {}),
      ...(priority !== null ? { priority } : {}),
    },
  });

  return response.data;
}
