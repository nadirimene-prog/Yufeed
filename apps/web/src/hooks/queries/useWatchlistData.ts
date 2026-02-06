/**
 * React Query hooks for Watchlist data management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { watchlistKeys } from '@/lib/queryKeys';
import { getWatchlists, createWatchlist, addWatchlistEntry, removeWatchlistEntry } from '@/lib/api';

export function useWatchlists(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: watchlistKeys.list(params || {}),
    queryFn: () => getWatchlists(params),
  });
}

export function useWatchlist(id: string) {
  return useQuery({
    queryKey: watchlistKeys.detail(id),
    queryFn: () => getWatchlists({ id }),
    enabled: !!id,
  });
}

export function useCreateWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: any) => createWatchlist(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.all });
    },
  });
}

export function useAddWatchlistEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ watchlistId, entry }: { watchlistId: string; entry: any }) =>
      addWatchlistEntry(watchlistId, entry),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.detail(variables.watchlistId) });
      queryClient.invalidateQueries({ queryKey: watchlistKeys.entries(variables.watchlistId) });
    },
  });
}

export function useRemoveWatchlistEntry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ watchlistId, entryId }: { watchlistId: string; entryId: string }) =>
      removeWatchlistEntry(watchlistId, entryId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: watchlistKeys.detail(variables.watchlistId) });
      queryClient.invalidateQueries({ queryKey: watchlistKeys.entries(variables.watchlistId) });
    },
  });
}
