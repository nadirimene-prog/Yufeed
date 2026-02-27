/* eslint-disable @typescript-eslint/no-explicit-any */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardHub from "@/features/dashboard/DashboardHub";

const mockReplace = vi.fn();
const {
  dashboardHookState,
  dashboardActionHookState,
  dashboardSettingsHookState,
} = vi.hoisted(() => ({
  dashboardHookState: {
    overview: null as any,
    queue: null as any,
    detail: null as any,
  },
  dashboardActionHookState: {
    performActionMutateAsync: vi.fn(),
    reviewActionMutateAsync: vi.fn(),
    bulkActionMutateAsync: vi.fn(),
    saveDraftMutateAsync: vi.fn(),
    snoozeAlertMutateAsync: vi.fn(),
  },
  dashboardSettingsHookState: {
    savedViewsQuery: null as any,
    preferencesQuery: null as any,
    createSavedViewMutateAsync: vi.fn(),
    updateSavedViewMutateAsync: vi.fn(),
    deleteSavedViewMutateAsync: vi.fn(),
    updatePreferencesMutateAsync: vi.fn(),
    updatePreferencesMutate: vi.fn(),
  },
}));

function buildOverviewQueryMock() {
  return {
    data: {
      critical_bar: {
        p1_sla_breaches: 0,
        p2_sla_breaches: 0,
        sanctions_hits_unreviewed: 0,
        sar_due_24h: 0,
        high_risk_cases_unassigned: 0,
        ingestion_lag_minutes: 0,
      },
      queue_summary: {
        alerts_open: 0,
        cases_open: 0,
        approvals_pending: 0,
        reg_tasks_due: 0,
      },
      governance: {
        rule_drift_score: 0,
        alert_to_case_rate: 0,
        fp_proxy_rate: 0,
        audit_completeness_rate: 0,
      },
      system_health: {
        status: "healthy",
        stuck_alerts: 0,
        unprocessed_transactions: 0,
      },
      throughput: {
        median_time_to_first_action_minutes: 0,
        median_case_resolution_hours: 0,
      },
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  };
}

function buildQueueQueryMock() {
  return {
    data: {
      page: 1,
      page_size: 50,
      total: 1,
      items: [
        {
          item_id: "item_1",
          record_id: "rec_1",
          kind: "alert",
          ref_id: "ALERT-001",
          type_label: "Alert",
          severity: "high",
          entity: "user_1",
          typology: "structuring",
          jurisdiction: "US",
          age_minutes: 10,
          sla_due_at: null,
          sla_status: "warning",
          owner: null,
          next_action: "review",
          risk_score: 70,
          status: "open",
          sar_required: false,
          review_requirement: { required: false, reasons: [] },
        },
      ],
    },
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  };
}

function buildDetailQueryMock() {
  return {
    data: null,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  };
}

function buildSavedViewsQueryMock() {
  return {
    data: { items: [], resolved_default_view_id: null },
    isLoading: false,
    isFetching: false,
    isSuccess: true,
    isError: false,
    isFetched: true,
    error: null,
    refetch: vi.fn(),
  };
}

function buildPreferencesQueryMock() {
  return {
    data: {
      layout_prefs: {},
      default_saved_view_id: null,
      updated_at: null,
    },
    isLoading: false,
    isFetching: false,
    isSuccess: true,
    isError: false,
    isFetched: true,
    error: null,
    refetch: vi.fn(),
  };
}

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={typeof href === "string" ? href : "#"} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams("view=operations&range=7d"),
}));

vi.mock("@/lib/auth", () => ({
  getAuthToken: () => "tok",
  getAuthUserProfile: () => ({ userId: "analyst_1" }),
}));

vi.mock("@/features/dashboard/useDashboardOverview", () => ({
  useDashboardOverview: () => dashboardHookState.overview,
}));

vi.mock("@/features/dashboard/useWorkQueue", () => ({
  useWorkQueue: () => dashboardHookState.queue,
}));

vi.mock("@/features/dashboard/useWorkItemDetail", () => ({
  useWorkItemDetail: () => dashboardHookState.detail,
}));

vi.mock("@/features/dashboard/useWorkItemActions", () => ({
  useWorkItemActions: () => ({
    performAction: {
      isPending: false,
      mutateAsync: dashboardActionHookState.performActionMutateAsync,
    },
    reviewAction: {
      isPending: false,
      mutateAsync: dashboardActionHookState.reviewActionMutateAsync,
    },
    bulkAction: { mutateAsync: dashboardActionHookState.bulkActionMutateAsync },
    saveDraft: {
      isPending: false,
      mutateAsync: dashboardActionHookState.saveDraftMutateAsync,
    },
    snoozeAlert: {
      mutateAsync: dashboardActionHookState.snoozeAlertMutateAsync,
    },
  }),
}));

vi.mock("@/features/dashboard/hooks/useDashboardTelemetryBridge", () => ({
  useDashboardTelemetryBridge: vi.fn(),
}));

vi.mock("@/features/dashboard/useDashboardSettings", () => ({
  useDashboardSavedViews: () => dashboardSettingsHookState.savedViewsQuery,
  useDashboardPreferences: () => dashboardSettingsHookState.preferencesQuery,
  useDashboardSavedViewMutations: () => ({
    createSavedView: {
      isPending: false,
      mutateAsync: dashboardSettingsHookState.createSavedViewMutateAsync,
    },
    updateSavedView: {
      isPending: false,
      mutateAsync: dashboardSettingsHookState.updateSavedViewMutateAsync,
    },
    deleteSavedView: {
      isPending: false,
      mutateAsync: dashboardSettingsHookState.deleteSavedViewMutateAsync,
    },
  }),
  useDashboardPreferencesMutation: () => ({
    isPending: false,
    mutateAsync: dashboardSettingsHookState.updatePreferencesMutateAsync,
    mutate: dashboardSettingsHookState.updatePreferencesMutate,
  }),
}));

vi.mock("@/features/dashboard/components/CriticalDecisionBar", () => ({
  __esModule: true,
  default: () => <div data-testid="critical-decision-bar" />,
}));

vi.mock("@/features/dashboard/components/UnifiedWorkQueue", () => ({
  __esModule: true,
  default: ({
    data,
    onSelectItem,
  }: {
    data?: { items?: any[] } | null;
    onSelectItem?: (item: any) => void;
  }) => (
    <div data-testid="work-queue">
      <input
        data-dashboard-queue-search-input
        aria-label="Queue search"
        defaultValue=""
      />
      <button
        type="button"
        onClick={() => {
          const first = data?.items?.[0];
          if (first) onSelectItem?.(first);
        }}
      >
        Select First Queue Item
      </button>
    </div>
  ),
}));

vi.mock("@/features/dashboard/components/InvestigationWorkspace", () => ({
  __esModule: true,
  default: ({
    selectedItem,
    message,
    onAction,
    onActionAndNext,
    onReview,
    onReviewAndNext,
  }: {
    selectedItem?: { item_id?: string } | null;
    message?: { text: string; type: string } | null;
    onAction?: (payload: any) => void;
    onActionAndNext?: (payload: any) => void;
    onReview?: (payload: any) => void;
    onReviewAndNext?: (payload: any) => void;
  }) => (
    <div data-testid="investigation-workspace">
      <div data-testid="selected-item-id">
        {selectedItem?.item_id ?? "none"}
      </div>
      <button type="button" role="tab">
        Overview
      </button>
      <button type="button" role="tab">
        Actions
      </button>
      <div data-dashboard-workspace-panel tabIndex={-1} />
      <input data-dashboard-assignee-input aria-label="Assignee" />
      <button type="button" data-dashboard-action="escalate">
        Escalate
      </button>
      <button
        type="button"
        data-dashboard-action-next-primary="true"
        data-dashboard-action-next="close"
      >
        + Next
      </button>
      <button
        type="button"
        onClick={() => onAction?.({ action: "mark_in_progress" })}
      >
        Trigger Action
      </button>
      <button
        type="button"
        onClick={() =>
          onActionAndNext?.({ action: "escalate", notes: "Escalate now" })
        }
      >
        Trigger Action Next
      </button>
      <button
        type="button"
        onClick={() =>
          onReview?.({
            proposed_action: "close",
            decision: "approve",
            submitted_by: "analyst_maker",
            review_notes: "LGTM",
          })
        }
      >
        Trigger Review
      </button>
      <button
        type="button"
        onClick={() =>
          onReviewAndNext?.({
            proposed_action: "close",
            decision: "return",
            submitted_by: "analyst_maker",
            review_notes: "Need more evidence",
          })
        }
      >
        Trigger Review Next
      </button>
      {message ? (
        <div data-testid="workspace-message">{message.text}</div>
      ) : null}
    </div>
  ),
}));

vi.mock("@/features/dashboard/components/GovernancePanel", () => ({
  __esModule: true,
  default: () => <div data-testid="governance-panel" />,
}));

vi.mock("@/features/dashboard/components/TrendStrip", () => ({
  __esModule: true,
  default: () => <div data-testid="trend-strip" />,
}));

vi.mock("@/features/dashboard/components/InsightsPanel", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) => (
    <div data-testid="insights-panel-state">{open ? "open" : "closed"}</div>
  ),
}));

vi.mock("@/features/dashboard/components/ShortcutHelpDialog", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="shortcut-help-open">help-open</div> : null,
}));

vi.mock("@/features/dashboard/components/CommandPalette", () => ({
  __esModule: true,
  default: ({ open, actions }: { open: boolean; actions: any[] }) =>
    open ? (
      <div data-testid="command-palette-open">
        palette-open
        <button
          type="button"
          onClick={() =>
            actions
              .find((action) => action.id === "focus-workspace")
              ?.onSelect()
          }
        >
          Run Focus Workspace
        </button>
      </div>
    ) : null,
}));

vi.mock("@/features/dashboard/components/DashboardSavedViewsDialog", () => ({
  __esModule: true,
  default: ({ open }: { open: boolean }) =>
    open ? <div data-testid="saved-views-dialog-open">views-open</div> : null,
}));

describe("DashboardHub", () => {
  beforeEach(() => {
    dashboardHookState.overview = buildOverviewQueryMock();
    dashboardHookState.queue = buildQueueQueryMock();
    dashboardHookState.detail = buildDetailQueryMock();
    dashboardActionHookState.performActionMutateAsync.mockReset();
    dashboardActionHookState.reviewActionMutateAsync.mockReset();
    dashboardActionHookState.bulkActionMutateAsync.mockReset();
    dashboardActionHookState.saveDraftMutateAsync.mockReset();
    dashboardActionHookState.snoozeAlertMutateAsync.mockReset();
    dashboardSettingsHookState.savedViewsQuery = buildSavedViewsQueryMock();
    dashboardSettingsHookState.preferencesQuery = buildPreferencesQueryMock();
    dashboardSettingsHookState.createSavedViewMutateAsync.mockReset();
    dashboardSettingsHookState.updateSavedViewMutateAsync.mockReset();
    dashboardSettingsHookState.deleteSavedViewMutateAsync.mockReset();
    dashboardSettingsHookState.updatePreferencesMutateAsync.mockReset();
    dashboardSettingsHookState.updatePreferencesMutate.mockReset();
    dashboardActionHookState.performActionMutateAsync.mockResolvedValue({
      success: true,
      message: "Action completed",
      updated_status: "open",
      next_recommended_item_id: null,
    });
    dashboardActionHookState.reviewActionMutateAsync.mockResolvedValue({
      success: true,
      message: "Review completed",
      review_status: "approved",
      updated_status: "open",
      next_recommended_item_id: null,
    });
    dashboardActionHookState.bulkActionMutateAsync.mockResolvedValue({
      success: true,
      count: 1,
    });
    dashboardActionHookState.saveDraftMutateAsync.mockResolvedValue({});
    dashboardActionHookState.snoozeAlertMutateAsync.mockResolvedValue({});
    dashboardSettingsHookState.createSavedViewMutateAsync.mockResolvedValue({});
    dashboardSettingsHookState.updateSavedViewMutateAsync.mockResolvedValue({});
    dashboardSettingsHookState.deleteSavedViewMutateAsync.mockResolvedValue({});
    dashboardSettingsHookState.updatePreferencesMutateAsync.mockResolvedValue(
      {},
    );
    localStorage.clear();
    mockReplace.mockReset();
  });

  it("defaults insights rail to collapsed and persists toggle state", () => {
    render(<DashboardHub />);

    expect(screen.getByTestId("insights-panel-state")).toHaveTextContent(
      "closed",
    );
    expect(
      screen.getByRole("button", { name: "Insights" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Insights" }));

    expect(screen.getByTestId("insights-panel-state")).toHaveTextContent(
      "open",
    );
    expect(
      screen.getByRole("button", { name: "Hide Insights" }),
    ).toBeInTheDocument();
    expect(localStorage.getItem("dashboard:insights-open")).toBe("1");
  }, 10000);

  it("hydrates insights rail from localStorage preference", () => {
    localStorage.setItem("dashboard:insights-open", "1");

    render(<DashboardHub />);

    expect(screen.getByTestId("insights-panel-state")).toHaveTextContent(
      "open",
    );
    expect(
      screen.getByRole("button", { name: "Hide Insights" }),
    ).toBeInTheDocument();
  });

  it("auto-applies server default saved view when URL has no explicit queue filters", async () => {
    dashboardSettingsHookState.savedViewsQuery = {
      ...buildSavedViewsQueryMock(),
      data: {
        items: [
          {
            id: "dsv_1",
            name: "Approvals Backlog",
            scope: "team",
            owner_user_id: "manager_1",
            team_id: "default",
            is_default_for_role: true,
            role: "manager",
            filters: {
              page: 1,
              pageSize: 50,
              queue: "approvals",
              severity: "high",
              jurisdiction: "",
              sla: "all",
              search: "",
              savedView: "all",
            },
            layout_prefs: {
              insightsOpen: true,
              queueDensity: "compact",
              defaultWorkspaceTab: "actions",
            },
            created_at: "2026-02-26T12:00:00Z",
            updated_at: "2026-02-26T12:00:00Z",
            updated_by_user_id: "manager_1",
          },
        ],
        resolved_default_view_id: "dsv_1",
      },
    };

    render(<DashboardHub />);

    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith(
        expect.stringContaining("queue=approvals"),
      ),
    );
    expect(mockReplace).toHaveBeenCalledWith(
      expect.stringContaining("severity=high"),
    );
  });

  it("shows partial outage summary when work queue fails", () => {
    dashboardHookState.queue = {
      ...buildQueueQueryMock(),
      data: null,
      isError: true,
      error: new Error("queue unavailable"),
    };

    render(<DashboardHub />);

    expect(
      screen.getByTestId("dashboard-partial-outage-banner"),
    ).toHaveTextContent("Work queue failed to load");
  });

  it("keeps overview metrics visible and offers retry when overview refresh fails with cached data", () => {
    const overviewRefetch = vi.fn();
    dashboardHookState.overview = {
      ...buildOverviewQueryMock(),
      isError: true,
      error: new Error("overview refresh failed"),
      refetch: overviewRefetch,
    };

    render(<DashboardHub />);

    expect(screen.getByTestId("critical-decision-bar")).toBeInTheDocument();
    expect(
      screen.getByTestId("overview-degraded-inline-banner"),
    ).toHaveTextContent(/showing last loaded metrics/i);

    fireEvent.click(screen.getByRole("button", { name: "Retry overview" }));
    expect(overviewRefetch).toHaveBeenCalledTimes(1);
  });

  it("shows partial outage summary when selected detail fails", () => {
    dashboardHookState.detail = {
      ...buildDetailQueryMock(),
      isError: true,
      error: new Error("detail unavailable"),
    };

    render(<DashboardHub />);

    expect(
      screen.getByTestId("dashboard-partial-outage-banner"),
    ).toHaveTextContent("Selected item detail failed to load");
  });

  it("surfaces a warning when an action succeeds but detail refresh fails", async () => {
    dashboardHookState.detail = {
      ...buildDetailQueryMock(),
      refetch: vi.fn().mockResolvedValue({
        isError: true,
        error: new Error("detail refresh failed"),
      }),
    };

    render(<DashboardHub />);

    fireEvent.click(screen.getByRole("button", { name: "Trigger Action" }));

    await waitFor(() =>
      expect(screen.getByTestId("workspace-message")).toHaveTextContent(
        /detail panel failed to refresh/i,
      ),
    );
  });

  it("opens shortcut help and command palette from keyboard shortcuts", () => {
    render(<DashboardHub />);

    fireEvent.keyDown(window, { key: "?" });
    expect(screen.getByTestId("shortcut-help-open")).toHaveTextContent(
      "help-open",
    );

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(screen.getByTestId("command-palette-open")).toHaveTextContent(
      "palette-open",
    );
  });

  it("supports go-to shortcut sequence for queue search focus", () => {
    render(<DashboardHub />);

    const queueSearch = screen.getAllByLabelText("Queue search")[0];
    expect(document.activeElement).not.toBe(queueSearch);

    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "q" });

    expect(document.activeElement).toBe(queueSearch);
  });

  it("supports go-to shortcut sequence for workspace focus", () => {
    render(<DashboardHub />);

    const workspacePanel = screen
      .getByTestId("investigation-workspace")
      .querySelector("[data-dashboard-workspace-panel]") as HTMLElement;
    expect(workspacePanel).toBeTruthy();
    expect(document.activeElement).not.toBe(workspacePanel);

    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "d" });

    expect(document.activeElement).toBe(workspacePanel);
  });

  it("executes command palette action handlers", () => {
    render(<DashboardHub />);

    const workspacePanel = screen
      .getByTestId("investigation-workspace")
      .querySelector("[data-dashboard-workspace-panel]") as HTMLElement;

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    fireEvent.click(
      screen.getByRole("button", { name: "Run Focus Workspace" }),
    );

    expect(document.activeElement).toBe(workspacePanel);
  });

  it("shows a notice instead of silently selecting another item when selection disappears from queue", () => {
    const { rerender } = render(<DashboardHub />);

    fireEvent.click(
      screen.getAllByRole("button", { name: "Select First Queue Item" })[0],
    );
    expect(screen.getByTestId("selected-item-id")).toHaveTextContent("item_1");

    dashboardHookState.queue = {
      ...buildQueueQueryMock(),
      data: {
        page: 1,
        page_size: 50,
        total: 1,
        items: [
          {
            ...buildQueueQueryMock().data.items[0],
            item_id: "item_2",
            record_id: "rec_2",
            ref_id: "ALERT-002",
          },
        ],
      },
    };

    rerender(<DashboardHub />);

    expect(
      screen.getByTestId("dashboard-selection-missing-banner"),
    ).toHaveTextContent(/no longer in the current queue/i);
    expect(screen.getByTestId("selected-item-id")).toHaveTextContent("none");
  });

  it("executes action requests through the dashboard action hook", async () => {
    render(<DashboardHub />);

    fireEvent.click(screen.getByRole("button", { name: "Trigger Action" }));

    await waitFor(() =>
      expect(
        dashboardActionHookState.performActionMutateAsync,
      ).toHaveBeenCalledWith(
        expect.objectContaining({ action: "mark_in_progress" }),
      ),
    );
  });

  it("executes review requests through the dashboard review hook", async () => {
    render(<DashboardHub />);

    fireEvent.click(screen.getByRole("button", { name: "Trigger Review" }));

    await waitFor(() =>
      expect(
        dashboardActionHookState.reviewActionMutateAsync,
      ).toHaveBeenCalledWith(
        expect.objectContaining({
          proposed_action: "close",
          decision: "approve",
          submitted_by: "analyst_maker",
        }),
      ),
    );
  });
});
