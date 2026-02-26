import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardHub from "@/features/dashboard/DashboardHub";

const mockReplace = vi.fn();

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
  useDashboardOverview: () => ({
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
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/dashboard/useWorkQueue", () => ({
  useWorkQueue: () => ({
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
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/dashboard/useWorkItemDetail", () => ({
  useWorkItemDetail: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/dashboard/useWorkItemActions", () => ({
  useWorkItemActions: () => ({
    performAction: { isPending: false, mutateAsync: vi.fn() },
    reviewAction: { isPending: false, mutateAsync: vi.fn() },
    bulkAction: { mutateAsync: vi.fn() },
    saveDraft: { isPending: false, mutateAsync: vi.fn() },
    snoozeAlert: { mutateAsync: vi.fn() },
  }),
}));

vi.mock("@/features/dashboard/components/CriticalDecisionBar", () => ({
  __esModule: true,
  default: () => <div data-testid="critical-decision-bar" />,
}));

vi.mock("@/features/dashboard/components/UnifiedWorkQueue", () => ({
  __esModule: true,
  default: () => (
    <div data-testid="work-queue">
      <input
        data-dashboard-queue-search-input
        aria-label="Queue search"
        defaultValue=""
      />
    </div>
  ),
}));

vi.mock("@/features/dashboard/components/InvestigationWorkspace", () => ({
  __esModule: true,
  default: () => (
    <div data-testid="investigation-workspace">
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
      <button type="button" data-dashboard-action-next-primary="true" data-dashboard-action-next="close">
        + Next
      </button>
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
            actions.find((action) => action.id === "focus-workspace")?.onSelect()
          }
        >
          Run Focus Workspace
        </button>
      </div>
    ) : null,
}));

describe("DashboardHub", () => {
  beforeEach(() => {
    localStorage.clear();
    mockReplace.mockReset();
  });

  it("defaults insights rail to collapsed and persists toggle state", () => {
    render(<DashboardHub />);

    expect(screen.getByTestId("insights-panel-state")).toHaveTextContent(
      "closed",
    );
    expect(screen.getByRole("button", { name: "Insights" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Insights" }));

    expect(screen.getByTestId("insights-panel-state")).toHaveTextContent("open");
    expect(screen.getByRole("button", { name: "Hide Insights" })).toBeInTheDocument();
    expect(localStorage.getItem("dashboard:insights-open")).toBe("1");
  });

  it("hydrates insights rail from localStorage preference", () => {
    localStorage.setItem("dashboard:insights-open", "1");

    render(<DashboardHub />);

    expect(screen.getByTestId("insights-panel-state")).toHaveTextContent("open");
    expect(screen.getByRole("button", { name: "Hide Insights" })).toBeInTheDocument();
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

    const workspacePanel = screen.getByTestId("investigation-workspace").querySelector(
      "[data-dashboard-workspace-panel]",
    ) as HTMLElement;
    expect(workspacePanel).toBeTruthy();
    expect(document.activeElement).not.toBe(workspacePanel);

    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "d" });

    expect(document.activeElement).toBe(workspacePanel);
  });

  it("executes command palette action handlers", () => {
    render(<DashboardHub />);

    const workspacePanel = screen.getByTestId("investigation-workspace").querySelector(
      "[data-dashboard-workspace-panel]",
    ) as HTMLElement;

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    fireEvent.click(screen.getByRole("button", { name: "Run Focus Workspace" }));

    expect(document.activeElement).toBe(workspacePanel);
  });
});
