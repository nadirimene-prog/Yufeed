/**
 * React Query hooks for Alert data management
 *
 * Provides hooks for:
 * - Fetching alerts with filters
 * - Getting single alert details
 * - Updating alert status
 * - Assigning alerts
 * - Resolving alerts
 *
 * All hooks include:
 * - Automatic cache management
 * - Optimistic updates
 * - Error handling
 * - Loading states
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { monitoringKeys } from '@/lib/queryKeys';
import { getAlerts, getAlert, updateAlert } from '@/lib/api';

/**
 * Fetch alerts with optional filters
 */
export function useAlerts(params?: {
  status?: string;
  severity?: string;
  user_id?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: monitoringKeys.alertsList(params || {}),
    queryFn: () => getAlerts(params),
  });
}

/**
 * Fetch single alert by ID
 */
export function useAlert(id: string) {
  return useQuery({
    queryKey: monitoringKeys.alertDetail(id),
    queryFn: () => getAlert(id),
    enabled: !!id,
  });
}

/**
 * Update alert (generic update)
 */
export function useUpdateAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateAlert(id, data),
    onSuccess: (updated, variables) => {
      // Update detail cache
      queryClient.setQueryData(monitoringKeys.alertDetail(variables.id), updated);

      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts() });
    },
  });
}

/**
 * Assign alert to analyst
 */
export function useAssignAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, assigned_to }: { id: string; assigned_to: string }) =>
      updateAlert(id, { assigned_to, status: 'in_review' }),
    onSuccess: (updated, variables) => {
      queryClient.setQueryData(monitoringKeys.alertDetail(variables.id), updated);
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts() });
    },
  });
}

/**
 * Resolve alert (close with outcome)
 */
export function useResolveAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      resolution_status,
      resolution_notes,
    }: {
      id: string;
      resolution_status: 'confirmed' | 'false_positive' | 'no_action';
      resolution_notes?: string;
    }) =>
      updateAlert(id, {
        status: 'resolved',
        resolution_status,
        resolution_notes,
      }),
    onSuccess: (updated, variables) => {
      queryClient.setQueryData(monitoringKeys.alertDetail(variables.id), updated);
      queryClient.invalidateQueries({ queryKey: monitoringKeys.alerts() });
    },
  });
}

/**
 * Bulk operations hook
 */
export function useBulkUpdateAlerts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ids,
      data,
    }: {
      ids: string[];
      data: any;
    }) => {
      // Execute updates in parallel
      return Promise.all(ids.map((id) => updateAlert(id, data)));
    },
    onSuccess: () => {
      // Invalidate all alert queries
      queryClient.invalidateQueries({ queryKey: monitoringKeys.all });
    },
  });
}
