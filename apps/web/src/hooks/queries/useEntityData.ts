"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { entityKeys } from "@/lib/queryKeys";
import type { EntityProfile, EntityType } from "@/types/entity";

export function useEntityProfile(entityType?: string, entityId?: string) {
  const normalizedType = (entityType ?? "") as EntityType;
  const normalizedId = entityId ?? "";

  return useQuery({
    queryKey: entityKeys.profile(normalizedType, normalizedId),
    queryFn: async () => {
      const response = await apiClient.get<EntityProfile>(
        `/api/entities/${encodeURIComponent(normalizedType)}/${encodeURIComponent(normalizedId)}`,
      );
      return response.data;
    },
    enabled: Boolean(normalizedType && normalizedId),
  });
}
