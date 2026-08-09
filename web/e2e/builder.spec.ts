import { expect, test } from "@playwright/test";

/**
 * Generation is asynchronous: the POST returns a job id and the client polls.
 * These helpers keep the mocks honest about that lifecycle.
 */
let nextJobId = 0;
const jobResults = new Map<string, unknown>();

function queueJob(result: unknown): { job_id: string; status: string } {
  const jobId = `job-${(nextJobId += 1)}`;
  jobResults.set(jobId, result);
  return { job_id: jobId, status: "queued" };
}

const initialHtml = "<!doctype html><html><body><h1>Fern Coffee</h1></body></html>";
const editedHtml =
  "<!doctype html><html><body><h1>Fern Coffee Roasters</h1></body></html>";

test("generate, edit, undo, and export the page", async ({ page }) => {
  let conversationHtml: string | null = null;
  let conversationDocument: unknown = null;
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ json: { id: "user-1", email: "owner@example.test" } }),
  );
  await page.route("**/api/conversations/**", (route) => {
    if (route.request().method() === "PUT") {
      const body = route.request().postDataJSON() as {
        code: string;
        document: unknown;
      };
      conversationHtml = body.code;
      conversationDocument = body.document;
      return route.fulfill({ json: { saved: true } });
    }
    if (!conversationHtml) {
      return route.fulfill({ status: 404, json: { detail: "Conversation not found" } });
    }
    const threadId = new URL(route.request().url()).pathname.split("/").pop();
    return route.fulfill({
      json: {
        thread_id: threadId,
        messages: [
          { role: "user", content: "Change the heading" },
          { role: "assistant", content: "Updated the heading." },
        ],
        current_code: conversationHtml,
        document: conversationDocument,
      },
    });
  });
  await page.route("**/api/options", (route) =>
    route.fulfill({
      json: {
        profiles: [],
        custom_profile_id: "custom",
        tones: [{ key: "minimal", label: "Minimal" }],
        complexities: [{ key: "balanced", label: "Balanced" }],
        refine_aspects: [{ key: "general", label: "General" }],
        sections: [{ key: "hero", label: "Hero" }],
        color_limits: [{ key: "single-accent", label: "Single accent" }],
      },
    }),
  );
  await page.route("**/api/templates", (route) =>
    route.fulfill({ json: { templates: [] } }),
  );
  await page.route("**/api/layout-dnas", (route) =>
    route.fulfill({ json: { dnas: [] } }),
  );
  await page.route("**/api/projects**", (route) =>
    route.fulfill({ json: { projects: [] } }),
  );
  await page.route("**/api/sections", (route) =>
    route.fulfill({ json: { sections: [{ index: 0, tag: "body", snippet: "Fern" }] } }),
  );
  await page.route("**/api/generate", (route) => {
    conversationHtml = initialHtml;
    return route.fulfill({
      status: 202,
      json: queueJob({
        html: initialHtml,
        notes: [],
        safety_alerts: [],
        settings: {
          tone: "minimal",
          complexity: "balanced",
          strict_minimal: false,
          profile: null,
        },
      }),
    });
  });
  await page.route("**/api/chat", (route) => {
    const request = route.request().postDataJSON() as {
      current_code: string;
      target_node_id?: string;
    };
    const responseHtml = request.target_node_id
      ? request.current_code.replace(">Fern Coffee<", ">Fern Ember<")
      : editedHtml;
    if (request.target_node_id) {
      expect(request.current_code).toContain(
        `data-mwb-id="${request.target_node_id}"`,
      );
    }
    conversationHtml = responseHtml;
    return route.fulfill({
      status: 202,
      json: queueJob({
        html: responseHtml,
        message: "Updated the heading.",
        intent: "refine",
        validation_errors: [],
        validation_notes: [],
        error: null,
      }),
    });
  });
  await page.route("**/api/export", async (route) => {
    const request = route.request().postDataJSON() as { html: string; mode: string };
    expect(request.html).toContain("Fern Coffee");
    expect(request.html).toContain("@media (max-width: 639px)");
    expect(request.html).toContain("font-size: 24px;");
    expect(request.html).toContain("--mwb-color-primary: #c2410c;");
    expect(request.html).toContain("color: var(--mwb-color-primary)");
    expect(request.html).toContain("outline: 2px solid rebeccapurple");
    expect(request.html).toContain("window.advancedReady = true");
    expect(request.html).toContain("mwb-node-");
    expect(request.html).not.toContain("data-mwb-id");
    await route.fulfill({
      json: { mode: request.mode, files: { "index.html": request.html } },
    });
  });

  await page.route("**/api/generation-jobs/active", (route) =>
    route.fulfill({ json: { job: null } }),
  );
  await page.route("**/api/generation-jobs/*", (route) => {
    const jobId = new URL(route.request().url()).pathname.split("/").pop() ?? "";
    return route.fulfill({
      json: {
        id: jobId,
        operation: "generate",
        status: "succeeded",
        result: jobResults.get(jobId) ?? null,
        error: null,
        failure_kind: null,
        duration_ms: 12,
        metrics: null,
        cancel_requested: false,
      },
    });
  });

  await page.goto("/");
  await page.getByPlaceholder("Describe the website you want to create…").fill("Coffee shop");
  await page.getByRole("button", { name: "Generate", exact: true }).click();

  const preview = page.frameLocator('iframe[title="preview"]');
  await expect(preview.getByRole("heading", { name: "Fern Coffee", exact: true })).toBeVisible();

  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
  await page.getByLabel("Search commands").fill("Show code");
  await page.getByLabel("Search commands").press("Enter");
  await expect(page.getByRole("button", { name: "Prepare export" })).toBeVisible();
  await page.keyboard.press("Control+1");
  await expect(preview.getByRole("heading", { name: "Fern Coffee", exact: true })).toBeVisible();

  await page.keyboard.press("Control+.");
  await expect(page.getByLabel("WYSIWYG editing")).toBeChecked();
  await page.getByRole("treeitem", { name: /h1 · Fern Coffee/ }).click();
  await page.getByLabel("Text content").fill("Fern Studio");
  await page.getByLabel("Text content").press("Tab");
  await expect(page.getByRole("treeitem", { name: /h1 · Fern Studio/ })).toBeVisible();
  await page.getByLabel("WYSIWYG editing").click();
  await expect(page.locator('iframe[title="preview"]')).toHaveAttribute(
    "srcdoc",
    /Fern Studio/,
  );
  await expect(
    page.frameLocator('iframe[title="preview"]').getByRole("heading", {
      name: "Fern Studio",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByTitle("Undo (Ctrl+Z)").click();
  await expect(preview.getByRole("heading", { name: "Fern Coffee", exact: true })).toBeVisible();

  await page.getByLabel("WYSIWYG editing").click();
  await page.getByRole("button", { name: "Global design tokens" }).click();
  await page.getByLabel("Primary color").fill("#c2410c");
  await page.getByLabel("Primary color").press("Tab");
  await page.getByRole("treeitem", { name: /h1 · Fern Coffee/ }).click();
  await page
    .getByLabel("Text color token")
    .selectOption("var(--mwb-color-primary)");
  await expect
    .poll(async () =>
      page
        .frameLocator("iframe.gjs-frame")
        .getByRole("heading", { name: "Fern Coffee" })
        .evaluate((element) => getComputedStyle(element).color),
    )
    .toBe("rgb(194, 65, 12)");
  await page.getByLabel("Element AI instruction").fill("Make this name warmer");
  await page.getByLabel("Apply AI edit to selected element").click();
  await expect(page.getByRole("treeitem", { name: /h1 · Fern Ember/ })).toBeVisible();
  await page.getByTitle("Undo (Ctrl+Z)").click();
  await expect(page.getByRole("treeitem", { name: /h1 · Fern Coffee/ })).toBeVisible();
  await page.getByLabel("Tablet viewport").click();
  await expect(page.getByText("768px", { exact: true })).toBeVisible();
  await page.getByLabel("Mobile viewport").click();
  await expect(page.getByText("390px", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Zoom out" }).click();
  await expect(page.getByText("75%", { exact: true })).toBeVisible();
  await page.getByLabel("Font size", { exact: true }).fill("24px");
  await page.getByLabel("Font size", { exact: true }).press("Tab");
  await expect
    .poll(async () =>
      page
        .frameLocator("iframe.gjs-frame")
        .getByRole("heading", { name: "Fern Coffee" })
        .evaluate((element) => getComputedStyle(element).fontSize),
    )
    .toBe("24px");
  await page.getByLabel("WYSIWYG editing").click();

  await page.getByRole("tab", { name: "Chat" }).click();
  const chatInput = page.getByPlaceholder("Describe a change or ask a question…");
  await chatInput.fill("Change the heading");
  await chatInput.press("Enter");
  await expect(
    preview.getByRole("heading", { name: "Fern Coffee Roasters", exact: true }),
  ).toBeVisible();

  const draftSaved = page.waitForRequest(
    (request) =>
      request.method() === "PUT" && request.url().includes("/api/conversations/"),
  );
  await page.getByTitle("Undo (Ctrl+Z)").click();
  await expect(preview.getByRole("heading", { name: "Fern Coffee", exact: true })).toBeVisible();
  await draftSaved;

  await page.getByRole("tab", { name: "Code" }).click();
  const advancedSaved = page.waitForRequest(
    (request) =>
      request.method() === "PUT" && request.url().includes("/api/conversations/"),
  );
  await page.getByRole("button", { name: "Advanced" }).click();
  await page
    .getByLabel("Custom CSS")
    .fill("body { outline: 2px solid rebeccapurple; }");
  await page.getByLabel("Custom CSS").press("Control+Enter");
  await page
    .getByLabel("Body script HTML")
    .fill("<script>window.advancedReady = true;</script>");
  await page.getByLabel("Body script HTML").press("Control+Enter");
  await page.getByRole("button", { name: "Compiled output" }).click();
  await advancedSaved;
  await page.getByRole("button", { name: "Prepare export" }).click();
  await expect(page.getByRole("button", { name: "index.html" })).toBeVisible();

  await page.reload();
  await expect(
    page.frameLocator('iframe[title="preview"]').getByRole("heading", {
      name: "Fern Coffee",
      exact: true,
    }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page
        .frameLocator('iframe[title="preview"]')
        .locator("body")
        .evaluate(() => Boolean((window as typeof window & { advancedReady?: boolean }).advancedReady)),
    )
    .toBe(true);
});
