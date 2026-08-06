import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "./Button";

describe("Button", () => {
  it("renders with text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button")).toHaveTextContent("Click me");
  });

  it("applies variant classes", () => {
    render(<Button variant="outline">Test</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("border-border2");
  });

  it("can be disabled", () => {
    render(<Button disabled>Test</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls onClick when clicked", async () => {
    let clicked = false;
    render(<Button onClick={() => (clicked = true)}>Test</Button>);
    screen.getByRole("button").click();
    expect(clicked).toBe(true);
  });
});
