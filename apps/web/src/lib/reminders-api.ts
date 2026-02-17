/**
 * Reminders API Client
 *
 * API endpoints for deadline reminders and notifications.
 */
import apiClient from "./http";

// Types
export interface UpcomingDeadline {
  obligation_id: string;
  obligation_text: string;
  deadline: string;
  days_remaining: number;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  related_documents: Array<{
    celex: string;
    title: string;
  }>;
}

export interface ReminderStatistics {
  total_upcoming: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_category: Record<string, number>;
}

export interface ReminderHistoryItem {
  id: string;
  reminder_type: string;
  sent_at: string;
  channel: string;
  status: "sent" | "delivered" | "failed";
  opened_at?: string;
  clicked_at?: string;
}

export interface ReminderSubscription {
  id: string;
  obligation_id?: string;
  category?: string;
  reminder_days: number[];
  channels: string[];
  is_active: boolean;
  created_at: string;
}

export interface CreateSubscriptionRequest {
  obligation_id?: string;
  category?: string;
  reminder_days?: number[];
  channels?: string[];
}

export interface SnoozeRequest {
  hours: number;
  reason?: string;
}

export interface AdminLogEntry {
  id: string;
  reminder_id: string;
  event_type: string;
  timestamp: string;
  details: Record<string, unknown>;
}

// API Functions

/**
 * Get upcoming deadlines with reminders
 */
export const getUpcomingDeadlines = async (params?: {
  days?: number;
  category?: string;
  severity?: "critical" | "high" | "medium" | "low";
  scope?: string[];
}): Promise<UpcomingDeadline[]> => {
  const response = await apiClient.get<UpcomingDeadline[]>(
    "/api/reminders/upcoming",
    {
      params,
    },
  );
  return response.data;
};

/**
 * Get reminder statistics
 */
export const getReminderStatistics = async (): Promise<ReminderStatistics> => {
  const response = await apiClient.get<ReminderStatistics>(
    "/api/reminders/statistics",
  );
  return response.data;
};

/**
 * Get reminder history for an obligation
 */
export const getReminderHistory = async (
  obligationId: string,
): Promise<ReminderHistoryItem[]> => {
  const response = await apiClient.get<ReminderHistoryItem[]>(
    `/api/reminders/history/${obligationId}`,
  );
  return response.data;
};

/**
 * Send reminder immediately
 */
export const sendReminderNow = async (
  obligationId: string,
  channels?: string[],
): Promise<{ message: string; reminder_id: string }> => {
  const response = await apiClient.post(
    `/api/reminders/send-now/${obligationId}`,
    {
      channels,
    },
  );
  return response.data;
};

/**
 * Snooze reminders for an obligation
 */
export const snoozeReminders = async (
  obligationId: string,
  hours: number,
  reason?: string,
): Promise<{ message: string; snoozed_until: string }> => {
  const response = await apiClient.post(
    `/api/reminders/snooze/${obligationId}`,
    {
      hours,
      reason,
    },
  );
  return response.data;
};

/**
 * Get all reminder subscriptions
 */
export const getReminderSubscriptions = async (): Promise<
  ReminderSubscription[]
> => {
  const response = await apiClient.get<ReminderSubscription[]>(
    "/api/reminders/subscriptions",
  );
  return response.data;
};

/**
 * Create a reminder subscription
 */
export const createReminderSubscription = async (
  data: CreateSubscriptionRequest,
): Promise<ReminderSubscription> => {
  const response = await apiClient.post<ReminderSubscription>(
    "/api/reminders/subscriptions",
    data,
  );
  return response.data;
};

/**
 * Delete a reminder subscription
 */
export const deleteReminderSubscription = async (
  subscriptionId: string,
): Promise<{ message: string }> => {
  const response = await apiClient.delete(
    `/api/reminders/subscriptions/${subscriptionId}`,
  );
  return response.data;
};

/**
 * Get admin logs (admin only)
 */
export const getAdminLogs = async (params?: {
  skip?: number;
  limit?: number;
  event_type?: string;
}): Promise<{ logs: AdminLogEntry[]; total: number }> => {
  const response = await apiClient.get("/api/reminders/admin/logs", { params });
  return response.data;
};
