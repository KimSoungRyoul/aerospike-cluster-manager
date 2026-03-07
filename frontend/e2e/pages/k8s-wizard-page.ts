import { Page, Locator, expect } from "@playwright/test";

export class K8sWizardPage {
  readonly page: Page;
  readonly nextBtn: Locator;
  readonly backBtn: Locator;
  readonly createBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.nextBtn = page.getByRole("button", { name: "Next" });
    this.backBtn = page.getByRole("button", { name: "Back" });
    this.createBtn = page.getByRole("main").getByRole("button", { name: "Create Cluster" });
  }

  async goto() {
    await this.page.goto("/k8s/clusters/new");
    await expect(
      this.page.locator("[aria-current='step']", { hasText: "Creation Mode" }),
    ).toBeVisible({ timeout: 15_000 });
  }

  // Step 0: Creation Mode
  async selectScratchMode() {
    await this.page.getByText("Start from Scratch").click();
  }

  async selectTemplateMode() {
    await this.page.getByText("Start from Template").click();
  }

  async selectTemplate(name: string) {
    await this.page.locator("button", { hasText: name }).first().click();
    // Wait for template detail to load (preview panel)
    await expect(this.page.getByText("Template Preview")).toBeVisible({ timeout: 10_000 });
  }

  // Step 1: Basic
  async fillBasicStep(opts: { name: string; namespace?: string; size?: number }) {
    await this.page.locator("#cluster-name").fill(opts.name);
    if (opts.namespace) {
      await this.page.locator("#k8s-namespace").click();
      await this.page.getByRole("option", { name: opts.namespace }).click();
    }
    if (opts.size != null) {
      await this.page.locator("#cluster-size").fill(String(opts.size));
    }
  }

  async nextStep() {
    await this.nextBtn.click();
  }

  async prevStep() {
    await this.backBtn.click();
  }

  async submitCreate() {
    await this.createBtn.click();
  }

  async getCurrentStepText(): Promise<string> {
    const stepEl = this.page.locator("[aria-current='step']");
    return (await stepEl.textContent()) ?? "";
  }

  async expectStepVisible(stepName: string) {
    // CardTitle renders as div.leading-none.font-semibold.tracking-tight
    await expect(
      this.page.locator(".font-semibold.tracking-tight, h3", { hasText: stepName }).first(),
    ).toBeVisible({ timeout: 5_000 });
  }
}
