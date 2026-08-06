import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Spinner } from "./Spinner";

describe("Spinner", () => {
  it("renders with default size", () => {
    const { container } = render(<Spinner />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain("animate-spin");
    expect(spinner.className).toContain("h-6 w-6");
  });

  it("renders with sm size", () => {
    const { container } = render(<Spinner size="sm" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain("h-4 w-4");
  });

  it("renders with lg size", () => {
    const { container } = render(<Spinner size="lg" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain("h-10 w-10");
  });

  it("applies custom className", () => {
    const { container } = render(<Spinner className="text-accent" />);
    const spinner = container.firstChild as HTMLElement;
    expect(spinner.className).toContain("text-accent");
  });
});
