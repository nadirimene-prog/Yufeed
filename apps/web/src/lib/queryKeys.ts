export const complianceKeys = {
  all: ["compliance"] as const,
  obligations: () => [...complianceKeys.all, "obligations"] as const,
  obligationsList: (params: Record<string, unknown>) =>
    [...complianceKeys.obligations(), "list", params] as const,
  obligationDetail: (id: number) => [...complianceKeys.obligations(), "detail", id] as const,
  obligationInternalRules: (id: number) =>
    [...complianceKeys.obligationDetail(id), "internal_rules"] as const,
  policies: () => [...complianceKeys.all, "policies"] as const,
  policiesList: (params: Record<string, unknown>) => [...complianceKeys.policies(), "list", params] as const,
  policyDetail: (id: number) => [...complianceKeys.policies(), "detail", id] as const,
  policySections: (id: number) => [...complianceKeys.policyDetail(id), "sections"] as const,
  risk: () => [...complianceKeys.all, "risk"] as const,
  riskMap: () => [...complianceKeys.risk(), "map"] as const,
} as const;

export const monitoringKeys = {
  all: ["monitoring"] as const,
  alerts: () => [...monitoringKeys.all, "alerts"] as const,
  alertsList: (params: Record<string, unknown>) =>
    [...monitoringKeys.alerts(), "list", params] as const,
  alertDetail: (id: number | string) => [...monitoringKeys.alerts(), "detail", id] as const,
  cases: () => [...monitoringKeys.all, "cases"] as const,
  casesList: (params: Record<string, unknown>) => [...monitoringKeys.cases(), "list", params] as const,
  caseDetail: (id: number | string) => [...monitoringKeys.cases(), "detail", id] as const,
} as const;
