import { test, expect } from "@playwright/test";
import { K8sWizardPage } from "../pages/k8s-wizard-page";
import {
  waitForK8sApi,
  cleanupK8sClusters,
  K8S_NAMESPACE,
  waitForClusterPhase,
} from "../fixtures/k8s-test-data";
import { expectToast } from "../fixtures/base-page";

test.describe("K8s Create Cluster (Scratch)", () => {
  const CLUSTER_NAME = "e2e-scratch";

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const available = await waitForK8sApi(page);
    if (!available) {
      test.skip(true, "K8s API not available");
    }
    await cleanupK8sClusters(page);
    await page.close();
  });

  test.afterAll(async ({ browser }) => {
    const page = await browser.newPage();
    await cleanupK8sClusters(page);
    await page.close();
  });

  test("should show Creation Mode as Step 1", async ({ page }) => {
    const wizard = new K8sWizardPage(page);
    await wizard.goto();

    await expect(page.locator("[aria-current='step']", { hasText: "Creation Mode" })).toBeVisible();
    await expect(page.getByText("Start from Scratch")).toBeVisible();
    await expect(page.getByText("Start from Template")).toBeVisible();
  });

  test("should create a cluster from scratch", async ({ page }) => {
    test.setTimeout(240_000); // Allow time for cluster to become Running

    const wizard = new K8sWizardPage(page);
    await wizard.goto();

    // Step 1: Creation Mode — select Scratch
    await wizard.selectScratchMode();
    await wizard.nextStep();

    // Step 2: Basic & Resources
    await wizard.expectStepVisible("Basic & Resources");
    await wizard.fillBasicStep({ name: CLUSTER_NAME, namespace: K8S_NAMESPACE, size: 1 });
    await wizard.nextStep();

    // Step 3: Namespace & Storage (accept defaults — in-memory)
    await wizard.expectStepVisible("Namespace & Storage");
    await wizard.nextStep();

    // Step 4: Advanced (skip — all defaults)
    await wizard.expectStepVisible("Advanced");
    await wizard.nextStep();

    // Step 5: Review
    await wizard.expectStepVisible("Review");
    await expect(page.getByText(CLUSTER_NAME)).toBeVisible();
    await wizard.submitCreate();

    await expectToast(page, /creation initiated|success/i);

    // Wait for cluster to become Completed (operator's stable phase)
    const completed = await waitForClusterPhase(page, K8S_NAMESPACE, CLUSTER_NAME, "Completed");
    expect(completed).toBe(true);
  });
});
