import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ReviewGateBanner from "@/features/dashboard/components/ReviewGateBanner";

describe("ReviewGateBanner", () => {
  function makeProps() {
    return {
      requirement: { required: true, reasons: ["sar_required"] },
      submittedBy: "",
      reviewNotes: "",
      proposedAction: "close" as const,
      currentUserId: "analyst_1",
      onSubmittedByChange: vi.fn(),
      onReviewNotesChange: vi.fn(),
      onApprove: vi.fn(),
      onReturn: vi.fn(),
    };
  }

  it("does not render when no review gate is required", () => {
    render(
      <ReviewGateBanner
        {...makeProps()}
        requirement={{ required: false, reasons: [] }}
      />,
    );

    expect(
      screen.queryByText(/4-eyes review required/i),
    ).not.toBeInTheDocument();
  });

  it("disables review actions until reviewer identity is provided", () => {
    render(<ReviewGateBanner {...makeProps()} submittedBy="" />);

    expect(
      screen.getByText(/Reviewer is required before submitting/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Approve review" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Return to analyst" }),
    ).toBeDisabled();
  });

  it("blocks same-user reviewer to enforce 4-eyes control in the UI", () => {
    render(<ReviewGateBanner {...makeProps()} submittedBy="analyst_1" />);

    expect(screen.getByText(/4-eyes control failed/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Approve review" }),
    ).toBeDisabled();
  });

  it("enables review actions for an independent reviewer", () => {
    const props = makeProps();
    render(<ReviewGateBanner {...props} submittedBy="reviewer_2" />);

    const approve = screen.getByRole("button", { name: "Approve review" });
    const ret = screen.getByRole("button", { name: "Return to analyst" });
    expect(approve).toBeEnabled();
    expect(ret).toBeEnabled();

    fireEvent.click(approve);
    fireEvent.click(ret);

    expect(props.onApprove).toHaveBeenCalledTimes(1);
    expect(props.onReturn).toHaveBeenCalledTimes(1);
  });
});
