/* eslint-disable @typescript-eslint/no-explicit-any */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import InvestigationWorkspace from "@/features/dashboard/components/InvestigationWorkspace";
import type {
  DashboardWorkQueueItem,
  WorkItemDetailResponse,
} from "@/features/dashboard/types";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={typeof href === "string" ? href : "#"} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/hooks/queries/useSpecializedData", () => ({
  useWorkspaceUsers: () => ({
    data: [{ user_id: "analyst_1" }, { user_id: "analyst_2" }],
  }),
}));

vi.mock("@/features/dashboard/components/AiRecommendationCard", () => ({
  __esModule: true,
  default: () => <div data-testid="ai-card" />,
}));

vi.mock("@/features/dashboard/components/ReviewGateBanner", () => ({
  __esModule: true,
  default: () => <div data-testid="review-gate-banner" />,
}));

const caseCommentsSpy = vi.fn();
vi.mock("@/components/workbench/CaseComments", () => ({
  __esModule: true,
  default: (props: any) => {
    caseCommentsSpy(props);
    return <div data-testid="case-comments" />;
  },
}));

vi.mock("@/features/dashboard/components/WorkspaceTabs", () => ({
  __esModule: true,
  default: ({ tabs, activeTab, onTabChange }: any) => {
    const current = tabs.find((tab: any) => tab.id === activeTab) ?? tabs[0];
    return (
      <div>
        <div role="tablist">
          {tabs.map((tab: any) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div>{current?.content}</div>
      </div>
    );
  },
}));

function makeSelectedItem(
  owner: string | null = "analyst_1",
  overrides?: Partial<DashboardWorkQueueItem>,
): DashboardWorkQueueItem {
  return {
    item_id: "item_1",
    record_id: "rec_1",
    kind: "alert",
    ref_id: "ALERT-001",
    type_label: "Velocity Alert",
    severity: "high",
    entity: "user_123",
    typology: "Structuring",
    jurisdiction: "US",
    age_minutes: 42,
    sla_due_at: null,
    sla_status: "warning",
    owner,
    next_action: "review",
    risk_score: 81,
    status: "open",
    sar_required: false,
    review_requirement: { required: false, reasons: [] },
    ...overrides,
  };
}

function makeDetail(
  owner: string | null = "analyst_1",
  overrides?: Partial<WorkItemDetailResponse>,
): WorkItemDetailResponse {
  return {
    work_item: makeSelectedItem(owner),
    context_timeline: [],
    linked_entities: ["user_123"],
    linked_transactions: ["tx_1"],
    ai_recommendation: {
      summary: "Close as false positive",
      confidence: 0.77,
      rationale: ["known_pattern"],
    },
    narrative: "Initial narrative",
    evidence_checklist: [
      { id: "e1", label: "Entity reviewed", completed: true },
    ],
    action_history: [],
    review_requirement: { required: false, reasons: [] },
    allowed_actions: ["assign", "mark_in_progress", "close"],
    ...overrides,
  };
}

describe("InvestigationWorkspace", () => {
  beforeEach(() => {
    localStorage.clear();
    caseCommentsSpy.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not reset Actions tab or notes on same-item detail updates", async () => {
    const props = {
      selectedItem: makeSelectedItem("analyst_1"),
      detail: makeDetail("analyst_1"),
      onAction: vi.fn(),
      onReview: vi.fn(),
      onSaveDraft: vi.fn(),
      onSnoozeAlert: vi.fn(),
    };

    const { rerender } = render(<InvestigationWorkspace {...props} />);

    fireEvent.click(screen.getByRole("tab", { name: "Actions" }));
    expect(screen.getByRole("tab", { name: "Actions" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    const notesInput = screen.getByLabelText("Notes");
    fireEvent.change(notesInput, { target: { value: "keep my notes" } });
    expect(notesInput).toHaveValue("keep my notes");

    rerender(
      <InvestigationWorkspace
        {...props}
        selectedItem={makeSelectedItem("analyst_2")}
        detail={makeDetail("analyst_2")}
      />,
    );
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByRole("tab", { name: "Actions" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByLabelText("Notes")).toHaveValue("keep my notes");
    expect(screen.getByLabelText("Assignee")).toHaveValue("analyst_2");
  }, 10000);

  it("autosaves narrative drafts and restores them per item", async () => {
    vi.useFakeTimers();
    const onSaveDraft = vi.fn().mockResolvedValue(undefined);
    const props = {
      selectedItem: makeSelectedItem("analyst_1"),
      detail: makeDetail("analyst_1"),
      onAction: vi.fn(),
      onReview: vi.fn(),
      onSaveDraft,
      onSnoozeAlert: vi.fn(),
    };

    const { rerender } = render(<InvestigationWorkspace {...props} />);

    const narrativeInput = screen.getByPlaceholderText(
      "Editable rationale for case notes / SAR narrative",
    );
    fireEvent.change(narrativeInput, {
      target: { value: "Draft for item one" },
    });

    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    expect(onSaveDraft).toHaveBeenCalledWith(
      { narrative: "Draft for item one", notes: "" },
      { silent: true, source: "autosave" },
    );

    rerender(
      <InvestigationWorkspace
        {...props}
        selectedItem={makeSelectedItem("analyst_2", {
          item_id: "item_2",
          record_id: "rec_2",
          ref_id: "ALERT-002",
        })}
        detail={makeDetail("analyst_2", {
          work_item: makeSelectedItem("analyst_2", {
            item_id: "item_2",
            record_id: "rec_2",
            ref_id: "ALERT-002",
          }),
          narrative: "Server narrative item two",
        })}
      />,
    );
    await act(async () => {
      await Promise.resolve();
    });

    expect(
      screen.getByDisplayValue("Server narrative item two"),
    ).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText(
        "Editable rationale for case notes / SAR narrative",
      ),
      {
        target: { value: "Draft for item two" },
      },
    );

    rerender(<InvestigationWorkspace {...props} />);
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByDisplayValue("Draft for item one")).toBeInTheDocument();
    expect(
      screen.queryByDisplayValue("Draft for item two"),
    ).not.toBeInTheDocument();
  });

  it("shows a stale detail warning when freshness metadata is stale", () => {
    render(
      <InvestigationWorkspace
        selectedItem={makeSelectedItem("analyst_1")}
        detail={makeDetail("analyst_1", {
          freshness: {
            generated_at: "2020-01-01T00:00:00Z",
            stale_after_seconds: 30,
          },
        })}
        onAction={vi.fn()}
        onReview={vi.fn()}
        onSaveDraft={vi.fn()}
        onSnoozeAlert={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/Detail context may be stale/i),
    ).toBeInTheDocument();
  });

  it("passes the case record id to case comments tab", () => {
    const selectedCase = makeSelectedItem("analyst_1", {
      kind: "case",
      record_id: "case_record_123",
      ref_id: "CASE-123",
    });
    render(
      <InvestigationWorkspace
        selectedItem={selectedCase}
        detail={makeDetail("analyst_1", { work_item: selectedCase })}
        onAction={vi.fn()}
        onReview={vi.fn()}
        onSaveDraft={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Comments" }));

    expect(caseCommentsSpy).toHaveBeenCalled();
    const lastCall =
      caseCommentsSpy.mock.calls[caseCommentsSpy.mock.calls.length - 1];
    expect(lastCall?.[0]).toEqual(
      expect.objectContaining({
        caseId: "case_record_123",
      }),
    );
  });

  it("keeps triage summary visible and offers retry when detail load fails", () => {
    const onRetryDetail = vi.fn();
    render(
      <InvestigationWorkspace
        selectedItem={makeSelectedItem("analyst_1")}
        detail={null}
        error="Failed to load work item detail"
        message={{
          text: "Action completed, but detail panel failed to refresh. Retry detail.",
          type: "warning",
        }}
        onRetryDetail={onRetryDetail}
        onAction={vi.fn()}
        onReview={vi.fn()}
        onSaveDraft={vi.fn()}
        onSnoozeAlert={vi.fn()}
      />,
    );

    expect(screen.getByText("ALERT-001")).toBeInTheDocument();
    expect(
      screen.getByText(/detail panel failed to refresh/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Failed to load work item detail"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry Detail" }));
    expect(onRetryDetail).toHaveBeenCalledTimes(1);
  });

  it("flushes dirty draft immediately on tab switch before debounce window", async () => {
    vi.useFakeTimers();
    const onSaveDraft = vi.fn().mockResolvedValue(undefined);
    render(
      <InvestigationWorkspace
        selectedItem={makeSelectedItem("analyst_1")}
        detail={makeDetail("analyst_1")}
        onAction={vi.fn()}
        onReview={vi.fn()}
        onSaveDraft={onSaveDraft}
        onSnoozeAlert={vi.fn()}
      />,
    );

    fireEvent.change(
      screen.getByPlaceholderText(
        "Editable rationale for case notes / SAR narrative",
      ),
      { target: { value: "Switch tab flush me" } },
    );

    fireEvent.click(screen.getByRole("tab", { name: "Actions" }));

    expect(onSaveDraft).toHaveBeenCalledTimes(1);
    expect(onSaveDraft).toHaveBeenLastCalledWith(
      { narrative: "Switch tab flush me", notes: "" },
      { silent: true, source: "autosave" },
    );

    await act(async () => {
      vi.advanceTimersByTime(1100);
      await Promise.resolve();
    });

    expect(onSaveDraft).toHaveBeenCalledTimes(1);
  });

  it("flushes dirty draft immediately when switching selected item", async () => {
    vi.useFakeTimers();
    const onSaveDraft = vi.fn().mockResolvedValue(undefined);
    const baseProps = {
      onAction: vi.fn(),
      onReview: vi.fn(),
      onSaveDraft,
      onSnoozeAlert: vi.fn(),
    };

    const { rerender } = render(
      <InvestigationWorkspace
        {...baseProps}
        selectedItem={makeSelectedItem("analyst_1")}
        detail={makeDetail("analyst_1")}
      />,
    );

    fireEvent.change(
      screen.getByPlaceholderText(
        "Editable rationale for case notes / SAR narrative",
      ),
      { target: { value: "Flush before switch" } },
    );

    rerender(
      <InvestigationWorkspace
        {...baseProps}
        selectedItem={makeSelectedItem("analyst_2", {
          item_id: "item_2",
          record_id: "rec_2",
          ref_id: "ALERT-002",
        })}
        detail={makeDetail("analyst_2", {
          work_item: makeSelectedItem("analyst_2", {
            item_id: "item_2",
            record_id: "rec_2",
            ref_id: "ALERT-002",
          }),
          narrative: "Server narrative item two",
        })}
      />,
    );

    expect(onSaveDraft).toHaveBeenCalledTimes(1);
    expect(onSaveDraft).toHaveBeenLastCalledWith(
      { narrative: "Flush before switch", notes: "" },
      { silent: true, source: "autosave" },
    );
  });
});
