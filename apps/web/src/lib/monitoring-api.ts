import apiClient from "@/lib/http";
import type { MonitoringAlert, MonitoringCase } from "@/types/monitoring";

export async function getMonitoringAlerts(params?: {
  limit?: number;
  status?: string;
  severity?: string;
}): Promise<MonitoringAlert[]> {
  const response = await apiClient.get<MonitoringAlert[]>("/api/alerts/", {
    params: {
      limit: params?.limit ?? 50,
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.severity ? { severity: params.severity } : {}),
    },
  });

  return response.data;
}

export async function getMonitoringCases(params?: {
  limit?: number;
  status?: string;
  severity?: string;
}): Promise<MonitoringCase[]> {
  const response = await apiClient.get<MonitoringCase[]>("/api/cases/", {
    params: {
      limit: params?.limit ?? 50,
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.severity ? { severity: params.severity } : {}),
    },
  });

  return response.data;
}

