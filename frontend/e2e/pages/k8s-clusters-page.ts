import { Page, Locator, expect } from "@playwright/test";

export class K8sClustersPage {
  readonly page: Page;
  readonly createClusterBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.createClusterBtn = page.getByRole("button", { name: /Create Cluster/i });
  }

  async goto() {
    // K8s clusters are listed on the home page (/) alongside connections
    await this.page.goto("/");
    await this.page.waitForLoadState("domcontentloaded");
  }

  getClusterCard(name: string): Locator {
    return this.page.getByRole("button", { name: new RegExp(name) }).first();
  }

  async clickCluster(name: string) {
    await this.getClusterCard(name).click();
  }

  async clickCreateCluster() {
    await this.createClusterBtn.click();
    await this.page.waitForURL("**/k8s/clusters/new");
  }

  async expectClusterVisible(name: string, timeout = 15_000) {
    await expect(this.getClusterCard(name)).toBeVisible({ timeout });
  }

  async expectClusterNotVisible(name: string, timeout = 15_000) {
    await expect(this.getClusterCard(name)).not.toBeVisible({ timeout });
  }

  async waitForClusterPhaseInUI(name: string, phase: string, timeout = 180_000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const card = this.getClusterCard(name);
      const text = await card.textContent();
      if (text && text.includes(phase)) return;
      await this.page.waitForTimeout(5_000);
      await this.page.reload();
    }
    throw new Error(`Cluster "${name}" did not reach phase "${phase}" within ${timeout}ms`);
  }
}
