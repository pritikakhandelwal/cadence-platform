import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "@/app/page";

describe("Landing page", () => {
  it("sends every call to action into the studio", () => {
    render(<Home />);

    for (const name of ["Get started", "Start your analysis"]) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("href", "/studio/upload");
    }
  });

  it("offers log in, and anchors 'how it works' to the section that exists", () => {
    const { container } = render(<Home />);

    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute("href", "/login");
    for (const link of screen.getAllByRole("link", { name: /how it works/i })) {
      expect(link).toHaveAttribute("href", "#how-it-works");
    }
    expect(container.querySelector("#how-it-works")).not.toBeNull();
  });

  it("explains the three steps in order", () => {
    render(<Home />);

    const labels = ["Upload", "Compare", "Improve"].map((l) => screen.getByText(l));
    for (let i = 1; i < labels.length; i++) {
      expect(labels[i - 1].compareDocumentPosition(labels[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });
});
