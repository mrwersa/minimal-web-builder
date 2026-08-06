import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Select } from "./Select";

describe("Select", () => {
  const options = [
    { value: "a", label: "Option A" },
    { value: "b", label: "Option B" },
  ];

  it("renders with options", () => {
    render(<Select value="a" options={options} onChange={() => {}} />);
    expect(screen.getByText("Option A")).toBeInTheDocument();
    expect(screen.getByText("Option B")).toBeInTheDocument();
  });

  it("shows selected value", () => {
    render(<Select value="b" options={options} onChange={() => {}} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("b");
  });

  it("can be disabled", () => {
    render(<Select value="a" options={options} onChange={() => {}} disabled />);
    expect(screen.getByRole("combobox")).toBeDisabled();
  });
});
