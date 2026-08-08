import { expect, test } from "@playwright/test";

const initialHtml = "<!doctype html><html><body><h1>Fern Coffee</h1></body></html>";
const editedHtml =
  "<!doctype html><html><body><h1>Fern Coffee Roasters</h1></body></html>";

test("generate, edit, undo, and export the page", async ({ page }) => {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ json: { id: "user-1", email: "owner@example.test" } }),
  );
  await page.route("**/api/conversations/**", (route) =>
    route.fulfill({ status: 404, json: { detail: "Conversation not found" } }),
  );
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
        tokens: {},
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
  await page.route("**/api/generate", (route) =>
    route.fulfill({
      json: {
        html: initialHtml,
        notes: [],
        safety_alerts: [],
        settings: {
          tone: "minimal",
          complexity: "balanced",
          strict_minimal: false,
          profile: null,
        },
      },
    }),
  );
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      json: {
        html: editedHtml,
        message: "Updated the heading.",
        intent: "refine",
        validation_errors: [],
        validation_notes: [],
        error: null,
      },
    }),
  );
  await page.route("**/api/export", async (route) => {
    const request = route.request().postDataJSON() as { html: string; mode: string };
    expect(request.html).toBe(initialHtml);
    await route.fulfill({
      json: { mode: request.mode, files: { "index.html": request.html } },
    });
  });

  await page.goto("/");
  await page.getByPlaceholder("Describe the website you want to create…").fill("Coffee shop");
  await page.getByRole("button", { name: "Generate", exact: true }).click();

  const preview = page.frameLocator('iframe[title="preview"]');
  await expect(preview.getByRole("heading", { name: "Fern Coffee", exact: true })).toBeVisible();

  const chatInput = page.getByPlaceholder("Describe a change or ask a question…");
  await chatInput.fill("Change the heading");
  await chatInput.press("Enter");
  await expect(
    preview.getByRole("heading", { name: "Fern Coffee Roasters", exact: true }),
  ).toBeVisible();

  await page.getByTitle("Undo (Ctrl+Z)").click();
  await expect(preview.getByRole("heading", { name: "Fern Coffee", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Code" }).click();
  await page.getByRole("button", { name: "Prepare export" }).click();
  await expect(page.getByRole("button", { name: "index.html" })).toBeVisible();
});
