/* eslint-disable @typescript-eslint/no-explicit-any */
import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import UnifiedWorkQueue from "@/features/dashboard/components/UnifiedWorkQueue";
import type {
  DashboardWorkQueueItem,
  DashboardWorkQueueParams,
} from "@/features/dashboard/types";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={typeof href === "string" ? href : "#"} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/hooks/queries/useSpecializedData", () => ({
  useWorkspaceUsers: () => ({ data: [{ user_id: "analyst_1" }] }),
}));

vi.mock("@/components/ui/export-button", () => ({
  ExportButton: (props: any) => (
    <button type="button" aria-label="Export" disabled={props.loading}>
      Export
    </button>
  ),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ open, children }: any) => (open ? <div>{children}</div> : null),
  DialogContent: ({ children, ...props }: any) => (
    <div {...props}>{children}</div>
  ),
  DialogHeader: ({ children, ...props }: any) => (
    <div {...props}>{children}</div>
  ),
  DialogTitle: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
  DialogDescription: ({ children, ...props }: any) => (
    <p {...props}>{children}</p>
  ),
  DialogFooter: ({ children, ...props }: any) => (
    <div {...props}>{children}</div>
  ),
}));

const baseFilters: DashboardWorkQueueParams = {
  page: 1,
  pageSize: 50,
  queue: "all",
  severity: "all",
  jurisdiction: "",
  sla: "all",
  search: "",
  savedView: "all",
};

const queueItem: DashboardWorkQueueItem = {
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
  owner: null,
  next_action: "review",
  risk_score: 81,
  status: "open",
  sar_required: true,
  review_requirement: { required: false, reasons: [] },
};

const queueItemTwo: DashboardWorkQueueItem = {
  ...queueItem,
  item_id: "item_2",
  record_id: "rec_2",
  ref_id: "CASE-002",
  kind: "case",
  severity: "medium",
  entity: "user_456",
  age_minutes: 5,
  risk_score: 41,
  sar_required: false,
};

function renderQueue(
  overrides?: Partial<ComponentProps<typeof UnifiedWorkQueue>>,
) {
  const onSelectItem = vi.fn();
  const onFiltersChange = vi.fn();
  const onRefresh = vi.fn();
  const onBulkAction = vi.fn();

  render(
    <UnifiedWorkQueue
      data={{ items: [queueItem], page: 1, page_size: 50, total: 1 }}
      filters={baseFilters}
      selectedItemId={null}
      onSelectItem={onSelectItem}
      onFiltersChange={onFiltersChange}
      onRefresh={onRefresh}
      onBulkAction={onBulkAction}
      {...overrides}
    />,
  );

  return { onSelectItem, onFiltersChange, onRefresh, onBulkAction };
}

describe("UnifiedWorkQueue", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps advanced filters collapsed by default and toggles them", () => {
    renderQueue();

    expect(screen.queryByLabelText("Severity filter")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Advanced filters/i }));

    expect(screen.getByLabelText("Severity filter")).toBeInTheDocument();
    expect(screen.getByLabelText("SLA filter")).toBeInTheDocument();
    expect(localStorage.getItem("dashboard:queue-advanced-open")).toBe("1");
  }, 10000);

  it("shows bulk action toolbar only when rows are selected", () => {
    renderQueue();

    expect(screen.queryByText(/1 selected/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Select ALERT-001"));

    expect(screen.getByText("1 selected")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Bulk assign" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Escalate" }),
    ).toBeInTheDocument();
  });

  it("does not trigger row selection from checkbox keyboard events", () => {
    const { onSelectItem } = renderQueue();

    fireEvent.keyDown(screen.getByLabelText("Select ALERT-001"), { key: " " });

    expect(onSelectItem).not.toHaveBeenCalled();
  });

  it("does not trigger row selection from entity link Enter key events", () => {
    const { onSelectItem } = renderQueue();

    fireEvent.keyDown(screen.getByRole("link", { name: "user_123" }), {
      key: "Enter",
    });

    expect(onSelectItem).not.toHaveBeenCalled();
  });

  it("supports j/k queue navigation shortcuts when focus is not in an input", () => {
    const { onSelectItem } = renderQueue({
      data: {
        items: [queueItem, queueItemTwo],
        page: 1,
        page_size: 50,
        total: 2,
      },
      selectedItemId: "item_1",
    });

    fireEvent.keyDown(window, { key: "j" });
    expect(onSelectItem).toHaveBeenCalledWith(
      expect.objectContaining({ item_id: "item_2" }),
    );

    fireEvent.keyDown(window, { key: "k" });
    expect(onSelectItem).toHaveBeenCalledWith(
      expect.objectContaining({ item_id: "item_1" }),
    );
  });

  it("ignores j/k queue shortcuts while typing in queue search", () => {
    const { onSelectItem } = renderQueue({
      data: {
        items: [queueItem, queueItemTwo],
        page: 1,
        page_size: 50,
        total: 2,
      },
      selectedItemId: "item_1",
    });

    const searchInput = screen.getByLabelText("Queue search");
    searchInput.focus();

    fireEvent.keyDown(searchInput, { key: "j" });

    expect(onSelectItem).not.toHaveBeenCalled();
  });

  it("toggles selected row checkbox with x shortcut", () => {
    renderQueue();

    const checkbox = screen.getByLabelText(
      "Select ALERT-001",
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    fireEvent.keyDown(window, { key: "x" });
    expect(checkbox.checked).toBe(true);

    fireEvent.keyDown(window, { key: "x" });
    expect(checkbox.checked).toBe(false);
  });

  it("loads compact density from localStorage and persists changes", () => {
    localStorage.setItem("dashboard:queue-density", "compact");
    renderQueue();

    const row = screen.getByRole("button", { name: "Queue item ALERT-001" });
    expect(row.className).toContain("px-2.5");

    fireEvent.click(screen.getByRole("button", { name: "Comfortable" }));

    expect(localStorage.getItem("dashboard:queue-density")).toBe("comfortable");
  });

  it("does not double-fire search filter change when Enter commits before debounce", () => {
    vi.useFakeTimers();
    const { onFiltersChange } = renderQueue();

    const searchInput = screen.getByLabelText("Queue search");
    fireEvent.change(searchInput, { target: { value: "alice" } });
    fireEvent.keyDown(searchInput, { key: "Enter" });

    expect(onFiltersChange).toHaveBeenCalledTimes(1);
    expect(onFiltersChange).toHaveBeenLastCalledWith({
      search: "alice",
      page: 1,
    });

    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(onFiltersChange).toHaveBeenCalledTimes(1);
  });

  it("does not double-fire jurisdiction filter change when blur commits before debounce", () => {
    vi.useFakeTimers();
    const { onFiltersChange } = renderQueue();

    fireEvent.click(screen.getByRole("button", { name: /Advanced filters/i }));
    const jurisdictionInput = screen.getByLabelText("Jurisdiction filter");

    fireEvent.change(jurisdictionInput, { target: { value: "fr" } });
    fireEvent.blur(jurisdictionInput);

    expect(onFiltersChange).toHaveBeenCalledTimes(1);
    expect(onFiltersChange).toHaveBeenLastCalledWith({
      jurisdiction: "FR",
      page: 1,
    });

    act(() => {
      vi.advanceTimersByTime(400);
    });

    expect(onFiltersChange).toHaveBeenCalledTimes(1);
  });

  it("opens and cancels bulk action confirmation without executing action", () => {
    const { onBulkAction } = renderQueue();

    fireEvent.click(screen.getByLabelText("Select ALERT-001"));
    fireEvent.click(screen.getByRole("button", { name: "Escalate" }));

    expect(screen.getByText("Confirm Bulk Action")).toBeInTheDocument();
    expect(
      screen.getByText(/Apply 'Escalate' to 1 selected item/),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByText("Confirm Bulk Action")).not.toBeInTheDocument();
    expect(onBulkAction).not.toHaveBeenCalled();
  });

  it("confirms bulk action dialog and executes selected action", () => {
    const { onBulkAction } = renderQueue();

    fireEvent.click(screen.getByLabelText("Select ALERT-001"));
    fireEvent.click(screen.getByRole("button", { name: "Escalate" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect(onBulkAction).toHaveBeenCalledTimes(1);
    const [items, action] = onBulkAction.mock.calls[0];
    expect(action).toBe("escalate");
    expect(items).toHaveLength(1);
    expect(items[0].item_id).toBe("item_1");
    expect(screen.queryByText("Confirm Bulk Action")).not.toBeInTheDocument();
  });
});
