import { test, expect } from "@playwright/test";
import { screenshot } from "../fixtures/base-page";
import { getTestConnectionId, TEST_CONNECTION } from "../fixtures/test-data";

test.describe("11 - Navigation", () => {
  let connId: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    connId = await getTestConnectionId(page);
    await page.close();
  });

  test("1. Sidebar shows test connection", async ({ page }) => {
    await page.goto(`/cluster/${connId}`);
    await page.waitForLoadState("domcontentloaded");

    const sidebar = page.locator("aside");
    await expect(sidebar.getByText(TEST_CONNECTION.name).first()).toBeVisible({ timeout: 15_000 });
    await screenshot(page, "11-01-sidebar-connection");
  });

  test("2. Sidebar search filters connections", async ({ page }) => {
    await page.goto(`/cluster/${connId}`);
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(2_000);

    const sidebar = page.locator("aside");
    const searchInput = sidebar.getByPlaceholder(/Search/i);

    if ((await searchInput.count()) > 0) {
      // Search for non-existent cluster
      await searchInput.fill("nonexistent_xyz");
      await page.waitForTimeout(500);

      // Should show "No clusters found" or similar
      await expect(sidebar.getByText(/No clusters found|No results/i).first()).toBeVisible({
        timeout: 5_000,
      });

      // Clear search to restore
      await searchInput.clear();
    }
    await screenshot(page, "11-02-sidebar-search");
  });

  test("3. TabBar navigation between pages", async ({ page }) => {
    await page.goto(`/cluster/${connId}`);
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(2_000);

    // Click Indexes tab
    await page
      .getByRole("button", { name: /Indexes/i })
      .last()
      .click();
    await page.waitForURL(`**/indexes/${connId}`, { timeout: 10_000 });
    await expect(page).toHaveURL(new RegExp(`/indexes/${connId}`));

    await screenshot(page, "11-03-tabbar-navigation");
  });

  test("4. Sidebar 'New Cluster' navigates to home", async ({ page }) => {
    await page.goto(`/cluster/${connId}`);
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(2_000);

    const sidebar = page.locator("aside");
    const newClusterBtn = sidebar.getByRole("button", { name: /New Cluster/i });

    if ((await newClusterBtn.count()) > 0) {
      await newClusterBtn.click();
      await page.waitForURL("**/", { timeout: 10_000 });
      await expect(page).toHaveURL(/\/$/);
    }
    await screenshot(page, "11-04-new-cluster-home");
  });

  test("5. Sidebar 'Settings' navigates to settings", async ({ page }) => {
    await page.goto(`/cluster/${connId}`);
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(2_000);

    const sidebar = page.locator("aside");
    const settingsBtn = sidebar.getByRole("button", { name: /Settings/i });

    if ((await settingsBtn.count()) > 0) {
      await settingsBtn.click();
      await page.waitForURL("**/settings", { timeout: 10_000 });
      await expect(page).toHaveURL(/\/settings/);
    }
    await screenshot(page, "11-05-settings-navigation");
  });
});
