import { Page, Locator, expect } from "@playwright/test";

export class K8sTemplatesPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly newTemplateBtn: Locator;
  readonly refreshBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByText("AerospikeClusterTemplates").first();
    this.newTemplateBtn = page.getByRole("button", { name: /New Template/i });
    this.refreshBtn = page.getByRole("button", { name: /Refresh/i });
  }

  async goto() {
    await this.page.goto("/k8s/templates");
    await expect(this.heading).toBeVisible({ timeout: 15_000 });
  }

  getTemplateCard(name: string): Locator {
    return this.page.getByRole("button", { name: new RegExp(name) }).first();
  }

  async clickTemplate(name: string) {
    await this.getTemplateCard(name).click();
  }

  async deleteTemplate(name: string) {
    const card = this.getTemplateCard(name);
    await card.hover();
    // Click the trash icon button inside the card
    await card
      .getByRole("button")
      .filter({ has: this.page.locator("svg") })
      .click();
    // Confirm deletion in dialog
    await expect(this.page.getByText("Delete AerospikeClusterTemplate")).toBeVisible();
    await this.page.getByRole("button", { name: "Delete" }).click();
  }

  async clickNewTemplate() {
    await this.newTemplateBtn.click();
    await this.page.waitForURL("**/k8s/templates/new");
  }
}
