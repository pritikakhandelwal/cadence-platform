import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ScoreGauge } from "@/components/ScoreGauge";
import { VideoToggle } from "@/components/VideoToggle";
import { Toast } from "@/components/Toast";
import { ISSUE_TYPES } from "@/lib/issueTypes";

describe("ScoreGauge", () => {
  it("shows the score rounded to one decimal place", () => {
    const { unmount } = render(<ScoreGauge score={38.6458} />);
    expect(screen.getByText("38.6")).toBeInTheDocument();
    unmount();

    render(<ScoreGauge score={38.66} />);
    expect(screen.getByText("38.7")).toBeInTheDocument();
  });

  it("shows a dash, not a made-up number, when there is no score", () => {
    render(<ScoreGauge score={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("fills the ring in proportion to the score", () => {
    const { container } = render(<ScoreGauge score={25} size={140} />);
    const arc = container.querySelectorAll("circle")[1];
    const circumference = Number(arc.getAttribute("stroke-dasharray"));
    expect(Number(arc.getAttribute("stroke-dashoffset"))).toBeCloseTo(circumference * 0.75);
  });

  it("clamps out-of-range scores so the ring can't over- or under-draw", () => {
    const { container } = render(<ScoreGauge score={250} />);
    const arc = container.querySelectorAll("circle")[1];
    expect(Number(arc.getAttribute("stroke-dashoffset"))).toBeCloseTo(0);
  });
});

describe("VideoToggle", () => {
  it("reports which side was picked", async () => {
    const onChange = vi.fn();
    render(<VideoToggle value="mine" onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /reference/i }));
    expect(onChange).toHaveBeenCalledWith("reference");

    await userEvent.click(screen.getByRole("button", { name: /your video/i }));
    expect(onChange).toHaveBeenLastCalledWith("mine");
  });
});

describe("Toast", () => {
  it("shows the reason and can be dismissed", async () => {
    const onDismiss = vi.fn();
    render(<Toast message="Too few reliable frames." onDismiss={onDismiss} />);

    expect(screen.getByText("Too few reliable frames.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});

describe("ISSUE_TYPES", () => {
  it("has an entry for every issue type the backend can emit", () => {
    // If the schema gains a type and this map doesn't, the Results page would
    // crash reading `.color` off undefined -- keep them in lockstep.
    for (const type of ["angle", "timing", "path", "occlusion", "tempo", "energy", "balance"] as const) {
      expect(ISSUE_TYPES[type].label).toBeTruthy();
      expect(ISSUE_TYPES[type].color).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });
});
