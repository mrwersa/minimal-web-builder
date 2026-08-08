import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { InlineError } from "./InlineError";

it("shows an actionable error and retries", () => {
  const onRetry = vi.fn();
  render(<InlineError message="Projects unavailable" onRetry={onRetry} />);

  expect(screen.getByRole("alert")).toHaveTextContent("Projects unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));

  expect(onRetry).toHaveBeenCalledOnce();
});
