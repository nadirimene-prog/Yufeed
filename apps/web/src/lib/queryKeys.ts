export const complianceKeys = {
  all: ["compliance"] as const,
  obligations: () => [...complianceKeys.all, "obligations"] as const,
  obligationsList: (params: Record<string, unknown>) =>
    [...complianceKeys.obligations(), "list", params] as const,
  obligationDetail: (id: number) => [...complianceKeys.obligations(), "detail", id] as const,
  policies: () => [...complianceKeys.all, "policies"] as const,
  policiesList: (params: Record<string, unknown>) => [...complianceKeys.policies(), "list", params] as const,
  policyDetail: (id: number) => [...complianceKeys.policies(), "detail", id] as const,
  risk: () => [...complianceKeys.all, "risk"] as const,
  riskMap: () => [...complianceKeys.risk(), "map"] as const,
} as const;

