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
  rules: () => [...monitoringKeys.all, "rules"] as const,
  rulesList: (params: Record<string, unknown>) => [...monitoringKeys.rules(), "list", params] as const,
  ruleDetail: (id: number | string) => [...monitoringKeys.rules(), "detail", id] as const,
  metrics: () => [...monitoringKeys.all, "metrics"] as const,
  dashboard: () => [...monitoringKeys.all, "dashboard"] as const,
} as const;

export const watchlistKeys = {
  all: ["watchlists"] as const,
  lists: () => [...watchlistKeys.all, "list"] as const,
  list: (params: Record<string, unknown>) => [...watchlistKeys.lists(), params] as const,
  details: () => [...watchlistKeys.all, "detail"] as const,
  detail: (id: number | string) => [...watchlistKeys.details(), id] as const,
  entries: (watchlistId: number | string) => [...watchlistKeys.detail(watchlistId), "entries"] as const,
} as const;

export const amlOfficerKeys = {
  all: ["aml-officer"] as const,
  briefing: () => [...amlOfficerKeys.all, "briefing"] as const,
  alerts: () => [...amlOfficerKeys.all, "alerts"] as const,
  sar: () => [...amlOfficerKeys.all, "sar"] as const,
  sarList: (params: Record<string, unknown>) => [...amlOfficerKeys.sar(), "list", params] as const,
  sanctions: () => [...amlOfficerKeys.all, "sanctions"] as const,
} as const;

export const modelRegistryKeys = {
  all: ["model-registry"] as const,
  models: () => [...modelRegistryKeys.all, "models"] as const,
  modelsList: (params: Record<string, unknown>) => [...modelRegistryKeys.models(), "list", params] as const,
  modelDetail: (id: number | string) => [...modelRegistryKeys.models(), "detail", id] as const,
} as const;
