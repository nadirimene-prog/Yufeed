# React Query Migration Status

**Last Updated:** 2026-02-06
**Overall Progress:** 60% Complete

---

## ✅ Completed Infrastructure

### 1. Provider Setup (COMPLETE)
- ✅ QueryClientProvider configured in `ReactQueryProvider.tsx`
- ✅ DevTools enabled for development
- ✅ Sensible defaults (1min stale, 5min GC, retry:1)

### 2. Query Keys (COMPLETE)
- ✅ `complianceKeys` - Obligations, policies, risk map
- ✅ `monitoringKeys` - Alerts, cases, rules, metrics, dashboard
- ✅ `watchlistKeys` - Watchlists and entries (NEW)
- ✅ `amlOfficerKeys` - Briefing, alerts, SAR, sanctions (NEW)
- ✅ `modelRegistryKeys` - Model registry (NEW)

### 3. Custom Hooks (COMPLETE)
- ✅ `useComplianceData.ts` - Obligations, policies
- ✅ `useComplianceWorkflowData.ts` - Rules, mappings
- ✅ `useMonitoringData.ts` - Basic monitoring
- ✅ `useAlertData.ts` - Full alert CRUD (NEW)

### 4. API Layer (COMPLETE)
- ✅ Centralized axios client in `http.ts`
- ✅ Domain-specific API modules
- ✅ Error interceptors and auth handling

---

## 🔧 Hooks Created (NEW)

### useAlertData.ts
```typescript
✅ useAlerts(params)          // Fetch with filters
✅ useAlert(id)                // Single alert
✅ useUpdateAlert()            // Generic update
✅ useAssignAlert()            // Assign to analyst
✅ useResolveAlert()           // Resolve with outcome
✅ useBulkUpdateAlerts()       // Bulk operations
```

### Query Keys Added
```typescript
✅ watchlistKeys.*             // Watchlist management
✅ amlOfficerKeys.*            // AML officer dashboard
✅ modelRegistryKeys.*         // Model registry
✅ monitoringKeys.rules        // Monitoring rules
✅ monitoringKeys.metrics      // Metrics dashboard
```

---

## 🚧 Pages Needing Migration (16 Total)

### High Priority (Frequently Used)

#### 1. `/app/alerts/page.tsx`
**Current:** Manual `getAlerts()` + useState
**Migrate To:** `useAlerts()` hook
**Complexity:** Low

```typescript
// BEFORE
const [alerts, setAlerts] = useState([]);
useEffect(() => {
  const load = async () => {
    const data = await getAlerts();
    setAlerts(data);
  };
  load();
}, []);

// AFTER
const { data: alerts, isLoading, error } = useAlerts();
```

#### 2. `/app/monitoring/page.tsx`
**Current:** Multiple `fetchWithAuth()` calls
**Migrate To:** Custom dashboard hook
**Complexity:** Medium

**Needs:** Create `useMonitoringDashboard()` hook combining:
- Alerts query
- Metrics query
- Cases query

#### 3. `/app/compliance/page.tsx`
**Current:** Manual fetch for cases
**Migrate To:** Existing `useComplianceDashboard()`
**Complexity:** Low (hook exists!)

#### 4. `/app/watchlists/page.tsx`
**Current:** Manual `getWatchlists()` + useState
**Migrate To:** NEW `useWatchlists()` hook
**Complexity:** Medium

**Needs:** Create `useWatchlistData.ts`:
```typescript
export function useWatchlists(params?: {})
export function useWatchlist(id: string)
export function useCreateWatchlist()
export function useAddWatchlistEntry()
export function useRemoveWatchlistEntry()
```

#### 5. `/app/transaction-monitoring/rules/page.tsx`
**Current:** Manual `fetchWithAuth('/api/monitoring_rules')`
**Migrate To:** NEW `useRules()` hook
**Complexity:** Medium

**Needs:** Create `useRulesData.ts`:
```typescript
export function useRules(params?: {})
export function useRule(id: string)
export function useCreateRule()
export function useUpdateRule()
export function useDeleteRule()
```

---

### Medium Priority (AML Officer Dashboard)

#### 6. `/app/aml-officer/page.tsx`
**Current:** `amlOfficerApi.getBriefing()` + useState
**Migrate To:** NEW `useAMLOfficerBriefing()` hook
**Complexity:** Low

#### 7. `/app/aml-officer/ask/page.tsx`
**Current:** Manual API call
**Migrate To:** NEW `useAMLOfficerAsk()` hook
**Complexity:** Low

#### 8. `/app/aml-officer/sar/page.tsx`
**Current:** Manual SAR fetch
**Migrate To:** NEW `useSARReports()` hook
**Complexity:** Medium

#### 9. `/app/aml-officer/sanctions/page.tsx`
**Current:** Manual sanctions check
**Migrate To:** NEW `useSanctionsCheck()` hook
**Complexity:** Low

**Needs:** Create `useAMLOfficerData.ts`:
```typescript
export function useAMLOfficerBriefing()
export function useAMLOfficerAlerts(params?: {})
export function useSARReports(params?: {})
export function useCreateSAR()
export function useSanctionsCheck()
```

---

### Lower Priority (Specialized Features)

#### 10. `/app/onchain-risk/page.tsx`
**Current:** Manual fetch
**Migrate To:** NEW `useOnchainRisk()` hook
**Complexity:** Low

#### 11. `/app/travel-rule/page.tsx`
**Current:** Manual fetch
**Migrate To:** NEW `useTravelRule()` hook
**Complexity:** Low

#### 12. `/app/cases/[id]/page.tsx`
**Current:** Manual case detail fetch
**Migrate To:** Existing `useCase(id)` from monitoring
**Complexity:** Low (hook may exist!)

#### 13. `/app/compliance/aml-scope/page.tsx`
**Current:** Manual scope analysis fetch
**Migrate To:** NEW `useAMLScope()` hook
**Complexity:** Medium

#### 14. `/app/compliance-report/page.tsx`
**Current:** Manual report generation
**Migrate To:** NEW `useComplianceReport()` hook
**Complexity:** Medium

#### 15. `/app/sar/prepare/page.tsx`
**Current:** Manual SAR preparation
**Migrate To:** NEW `useSARPreparation()` hook
**Complexity:** High (complex workflow)

#### 16. `/app/model-registry/page.tsx`
**Current:** Manual model registry fetch
**Migrate To:** NEW `useModelRegistry()` hook
**Complexity:** Low

---

## 📋 Migration Checklist per Page

For each page migration:

1. **Create Hook** (if not exists)
   - [ ] Define in appropriate hook file
   - [ ] Add query key to queryKeys.ts
   - [ ] Implement useQuery with proper config
   - [ ] Add mutations if needed (create/update/delete)
   - [ ] Test cache invalidation

2. **Update Page Component**
   - [ ] Remove useState for data
   - [ ] Remove useState for loading
   - [ ] Remove useState for error
   - [ ] Remove useEffect with fetch
   - [ ] Import and use React Query hook
   - [ ] Use LoadingBoundary component
   - [ ] Handle error state properly

3. **Test**
   - [ ] Page loads data correctly
   - [ ] Loading state displays
   - [ ] Error state displays
   - [ ] Cache invalidation works on mutations
   - [ ] Optimistic updates work (if applicable)
   - [ ] DevTools shows queries

---

## 🎯 Implementation Plan

### Phase 1: Complete Missing Hooks (1-2 days)
- [ ] Create `useWatchlistData.ts`
- [ ] Create `useRulesData.ts`
- [ ] Create `useAMLOfficerData.ts`
- [ ] Create `useModelRegistryData.ts`
- [ ] Create `useOnchainRiskData.ts`
- [ ] Create `useTravelRuleData.ts`
- [ ] Create `useComplianceReportsData.ts`
- [ ] Create `useSARData.ts`

### Phase 2: Migrate High Priority Pages (2-3 days)
- [ ] Alerts page
- [ ] Monitoring dashboard
- [ ] Compliance dashboard
- [ ] Watchlists page
- [ ] Rules page

### Phase 3: Migrate Medium Priority Pages (2 days)
- [ ] AML Officer dashboard
- [ ] AML Officer ask
- [ ] SAR reports
- [ ] Sanctions check

### Phase 4: Migrate Lower Priority Pages (1-2 days)
- [ ] Onchain risk
- [ ] Travel rule
- [ ] Case details
- [ ] AML scope
- [ ] Compliance reports
- [ ] SAR preparation
- [ ] Model registry

### Phase 5: Testing & Optimization (1 day)
- [ ] Integration tests for all hooks
- [ ] Performance testing
- [ ] Cache strategy review
- [ ] Error handling review
- [ ] Documentation updates

---

## 🐛 Known Issues & Anti-Patterns

### Issue 1: Manual Polling in useApiHealth
**Location:** `hooks/useApiHealth.ts`
**Problem:** Custom polling with setTimeout instead of React Query
**Solution:** Migrate to useQuery with refetchInterval

```typescript
// BEFORE
useEffect(() => {
  const interval = setInterval(checkHealth, 30000);
  return () => clearInterval(interval);
}, []);

// AFTER
const { data: health } = useQuery({
  queryKey: ['api-health'],
  queryFn: checkHealth,
  refetchInterval: 30000,
});
```

### Issue 2: Direct API Calls in Components
**Problem:** Components import API functions directly
**Solution:** Always use custom hooks

```typescript
// BAD
import { getAlerts } from '@/lib/api';
const alerts = await getAlerts();

// GOOD
import { useAlerts } from '@/hooks/queries/useAlertData';
const { data: alerts } = useAlerts();
```

### Issue 3: Manual Cache Invalidation
**Problem:** Components manually clearing cache
**Solution:** Let mutations handle invalidation

```typescript
// BAD
await updateAlert(id, data);
setAlerts(alerts.map(a => a.id === id ? data : a));

// GOOD
const { mutate: updateAlert } = useUpdateAlert();
updateAlert({ id, data }); // Automatically invalidates
```

---

## 📊 Expected Benefits After Full Migration

1. **Performance**
   - 50% reduction in redundant API calls (deduplication)
   - Instant navigation with cached data
   - Background refetching for fresh data

2. **Developer Experience**
   - 70% less boilerplate code
   - Automatic loading/error states
   - Type-safe API calls

3. **User Experience**
   - Faster page loads
   - Optimistic updates
   - Consistent loading indicators

4. **Maintainability**
   - Centralized data fetching logic
   - Easier testing
   - Better error handling

---

## 🚀 Quick Start for New Migrations

1. Check if hook exists in `hooks/queries/`
2. If not, create following template:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { yourDomainKeys } from '@/lib/queryKeys';
import { yourApi } from '@/lib/your-api';

export function useYourData(params?: {}) {
  return useQuery({
    queryKey: yourDomainKeys.list(params || {}),
    queryFn: () => yourApi.getList(params),
  });
}

export function useCreateYour() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => yourApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: yourDomainKeys.all });
    },
  });
}
```

3. Update page component:

```typescript
'use client';

import { useYourData } from '@/hooks/queries/useYourData';
import { LoadingBoundary } from '@/components/shared';

export default function YourPage() {
  const { data, isLoading, error } = useYourData();

  return (
    <LoadingBoundary loading={isLoading} error={error} isEmpty={!data?.length}>
      {/* Your component */}
    </LoadingBoundary>
  );
}
```

---

## 📞 Need Help?

- Check existing hooks in `hooks/queries/` for patterns
- Refer to React Query docs: https://tanstack.com/query/latest
- Use DevTools to debug queries
- Ask team for code review

---

**Last Updated:** 2026-02-06
**Next Review:** After Phase 2 completion
