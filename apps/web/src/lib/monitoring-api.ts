import apiClient from "@/lib/http";
import type { MonitoringAlert, MonitoringCase } from "@/types/monitoring";

export async function getMonitoringAlerts(params?: {
  limit?: number;
  status?: string;
  severity?: string;
}): Promise<MonitoringAlert[]> {
  const status = typeof params?.status === "string" && params.status.length > 0 ? params.status : null;
  const severity =
    typeof params?.severity === "string" && params.severity.length > 0 ? params.severity : null;
  const response = await apiClient.get<MonitoringAlert[]>("/api/alerts/", {
    params: {
      limit: params?.limit ?? 50,
      ...(status !== null ? { status } : {}),
      ...(severity !== null ? { severity } : {}),
    },
  });

  return response.data;
}

export async function getMonitoringCases(params?: {
  limit?: number;
  status?: string;
  severity?: string;
}): Promise<MonitoringCase[]> {
  const status = typeof params?.status === "string" && params.status.length > 0 ? params.status : null;
  const severity =
    typeof params?.severity === "string" && params.severity.length > 0 ? params.severity : null;
  const response = await apiClient.get<MonitoringCase[]>("/api/cases/", {
    params: {
      limit: params?.limit ?? 50,
      ...(status !== null ? { status } : {}),
      ...(severity !== null ? { severity } : {}),
    },
  });

  return response.data;
}
