import { test, expect } from "@playwright/test";
import { K8sTemplatesPage } from "../pages/k8s-templates-page";
import { waitForK8sApi, cleanupK8sTemplates } from "../fixtures/k8s-test-data";
import { expectToast } from "../fixtures/base-page";

test.describe("K8s Templates", () => {
  let templatesPage: K8sTemplatesPage;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const available = await waitForK8sApi(page);
    if (!available) {
      test.skip(true, "K8s API not available — skipping K8s tests");
    }
    await page.close();
  });

  test.beforeEach(async ({ page }) => {
    templatesPage = new K8sTemplatesPage(page);
  });

  test.afterAll(async ({ browser }) => {
    const page = await browser.newPage();
    await cleanupK8sTemplates(page);
    await page.close();
  });

  test("should display default templates", async () => {
    await templatesPage.goto();

    // Default templates from Helm values: minimal, soft-rack, hard-rack
    await expect(templatesPage.getTemplateCard("minimal")).toBeVisible();
    await expect(templatesPage.getTemplateCard("soft-rack")).toBeVisible();
    await expect(templatesPage.getTemplateCard("hard-rack")).toBeVisible();
  });

  test("should navigate to template detail on card click", async ({ page }) => {
    await templatesPage.goto();
    await templatesPage.clickTemplate("minimal");

    await page.waitForURL("**/k8s/templates/**/minimal");
    await expect(page.getByRole("heading", { name: "minimal" })).toBeVisible();
  });

  // Create → Delete must run in order
  test.describe.serial("template CRUD", () => {
    test("should create a new template", async ({ page }) => {
      templatesPage = new K8sTemplatesPage(page);
      await templatesPage.goto();
      await templatesPage.clickNewTemplate();

      // Fill template form
      await page.locator("#tmpl-name").fill("e2e-template");
      // Select namespace
      await page.locator("#tmpl-ns").click();
      await page.getByRole("option", { name: "acko-system" }).click();

      // Submit
      await page.getByRole("button", { name: /Create AerospikeClusterTemplate/i }).click();
      await expectToast(page, /created|success/i);

      // Verify in list
      await templatesPage.goto();
      await expect(templatesPage.getTemplateCard("e2e-template")).toBeVisible();
    });

    test("should delete a template", async ({ page }) => {
      templatesPage = new K8sTemplatesPage(page);
      await templatesPage.goto();

      await expect(templatesPage.getTemplateCard("e2e-template")).toBeVisible({ timeout: 10_000 });

      await templatesPage.deleteTemplate("e2e-template");
      await expectToast(page, /deleted|success/i);

      // Verify removed from list
      await page.waitForTimeout(1_000);
      await expect(templatesPage.getTemplateCard("e2e-template")).not.toBeVisible();
    });
  });
});
