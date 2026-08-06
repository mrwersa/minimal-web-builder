import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Switch } from "./Switch";

describe("Switch", () => {
  it("renders unchecked by default", () => {
    render(<Switch id="test" checked={false} onChange={() => {}} />);
    const switchEl = screen.getByRole("switch");
    expect(switchEl).not.toBeChecked();
  });

  it("renders checked when specified", () => {
    render(<Switch id="test" checked onChange={() => {}} />);
    const switchEl = screen.getByRole("switch");
    expect(switchEl).toBeChecked();
  });

  it("can be disabled", () => {
    render(<Switch id="test" checked={false} onChange={() => {}} disabled />);
    expect(screen.getByRole("switch")).toBeDisabled();
  });

  it("toggles on click", async () => {
    let checked = false;
    render(<Switch id="test" checked={false} onChange={(v) => (checked = v)} />);
    screen.getByRole("switch").click();
    expect(checked).toBe(true);
  });
});
