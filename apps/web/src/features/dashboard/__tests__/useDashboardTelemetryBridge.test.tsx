import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDashboardTelemetryBridge } from "@/features/dashboard/hooks/useDashboardTelemetryBridge";

const { mockPost } = vi.hoisted(() => ({
  mockPost: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  default: {
    post: mockPost,
  },
}));

function BridgeHarness(props: {
  enabled?: boolean;
  flushIntervalMs?: number;
  maxBatchSize?: number;
}) {
  useDashboardTelemetryBridge(props);
  return null;
}

function emitTelemetry(
  event:
    | "dashboard_filter_apply"
    | "dashboard_row_select"
    | "dashboard_action_submit",
  payload: Record<string, unknown> = {},
) {
  window.dispatchEvent(
    new CustomEvent("dashboard:telemetry", {
      detail: {
        event,
        payload,
        at: "2026-02-26T12:00:00Z",
      },
    }),
  );
}

async function flushMicrotasks() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("useDashboardTelemetryBridge", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockPost.mockReset();
    mockPost.mockResolvedValue({ data: { accepted: 1, dropped: 0 } });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("flushes immediately when max batch size is reached", async () => {
    render(<BridgeHarness flushIntervalMs={1000} maxBatchSize={2} />);
    await act(async () => {
      await flushMicrotasks();
    });

    await act(async () => {
      emitTelemetry("dashboard_filter_apply", { source: "queue_controls" });
      emitTelemetry("dashboard_row_select", { source: "desktop_queue" });
      await flushMicrotasks();
    });

    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith("/api/dashboard/telemetry/events", {
      events: [
        expect.objectContaining({ event: "dashboard_filter_apply" }),
        expect.objectContaining({ event: "dashboard_row_select" }),
      ],
    });
  });

  it("requeues failed batches and retries on the next flush interval", async () => {
    mockPost
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({ data: { accepted: 1, dropped: 0 } });

    render(<BridgeHarness flushIntervalMs={300} maxBatchSize={10} />);
    await act(async () => {
      await flushMicrotasks();
    });

    await act(async () => {
      emitTelemetry("dashboard_action_submit", { mode: "single" });
      await flushMicrotasks();
    });

    await act(async () => {
      vi.advanceTimersByTime(300);
      await flushMicrotasks();
    });
    expect(mockPost).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(300);
      await flushMicrotasks();
    });

    expect(mockPost).toHaveBeenCalledTimes(2);
    expect(mockPost.mock.calls[1]?.[0]).toBe("/api/dashboard/telemetry/events");
    expect(mockPost.mock.calls[1]?.[1]).toEqual({
      events: [expect.objectContaining({ event: "dashboard_action_submit" })],
    });
  });

  it("flushes queued events on pagehide", async () => {
    render(<BridgeHarness flushIntervalMs={5000} maxBatchSize={10} />);
    await act(async () => {
      await flushMicrotasks();
    });

    await act(async () => {
      emitTelemetry("dashboard_filter_apply", { source: "pagination" });
      await flushMicrotasks();
    });

    expect(mockPost).not.toHaveBeenCalled();

    await act(async () => {
      window.dispatchEvent(new Event("pagehide"));
      await flushMicrotasks();
    });

    expect(mockPost).toHaveBeenCalledTimes(1);
  });
});
