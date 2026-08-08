import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { useStore } from "../store";
import ProjectPanel from "./ProjectPanel";

const summary: api.ProjectSummary = {
  id: "project-1",
  name: "Launch",
  page_count: 1,
  created_at: "2026-08-08T00:00:00Z",
  updated_at: "2026-08-08T00:00:00Z",
  archived_at: null,
};

describe("ProjectPanel", () => {
  beforeEach(() => {
    useStore.setState({
      projects: [summary],
      projectName: "",
      projectSearch: "",
      activeProjectId: null,
      activePageId: null,
      revisions: [],
      error: null,
    });
    vi.spyOn(api, "fetchProjects").mockResolvedValue([summary]);
  });

  afterEach(() => vi.restoreAllMocks());

  it("renames a project through the inline editor", async () => {
    const renamed = { ...summary, name: "Product Launch", pages: [] };
    vi.spyOn(api, "renameProject").mockResolvedValue(renamed);
    vi.mocked(api.fetchProjects).mockResolvedValue([
      { ...summary, name: "Product Launch" },
    ]);
    render(<ProjectPanel />);

    fireEvent.click(screen.getByRole("button", { name: "Rename Launch" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Rename Launch" }), {
      target: { value: "Product Launch" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(api.renameProject).toHaveBeenCalledWith("project-1", "Product Launch"),
    );
    expect(await screen.findByText("Product Launch")).toBeInTheDocument();
  });
});
