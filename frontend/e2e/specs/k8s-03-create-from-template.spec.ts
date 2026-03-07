import { test, expect } from "@playwright/test";
import { K8sWizardPage } from "../pages/k8s-wizard-page";
import {
  waitForK8sApi,
  cleanupK8sClusters,
  K8S_NAMESPACE,
  waitForClusterPhase,
} from "../fixtures/k8s-test-data";
import { expectToast } from "../fixtures/base-page";

test.describe("K8s Create Cluster (from Template)", () => {
  const CLUSTER_NAME = "e2e-from-tmpl";

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

  test("should select template and show preview", async ({ page }) => {
    const wizard = new K8sWizardPage(page);
    await wizard.goto();

    // Step 1: Select Template mode
    await wizard.selectTemplateMode();
    await expect(page.getByText("Filter by Namespace")).toBeVisible();

    // Select "minimal" template
    await wizard.selectTemplate("minimal");

    // Preview should show template details
    await expect(page.getByText("Template Preview")).toBeVisible();
  });

  test("should pre-fill form from template and create cluster", async ({ page }) => {
    test.setTimeout(240_000);

    const wizard = new K8sWizardPage(page);
    await wizard.goto();

    // Step 1: Select template
    await wizard.selectTemplateMode();
    await wizard.selectTemplate("minimal");
    await wizard.nextStep();

    // Step 2: Name & Namespace only (template mode skips other steps)
    await wizard.expectStepVisible("Name & Namespace");
    await wizard.fillBasicStep({ name: CLUSTER_NAME, namespace: K8S_NAMESPACE });
    await wizard.nextStep();

    // Step 3: Review — should show template reference
    await wizard.expectStepVisible("Review");
    await expect(page.getByText(CLUSTER_NAME)).toBeVisible();
    await expect(page.getByText("minimal").first()).toBeVisible(); // template name in review
    await wizard.submitCreate();

    await expectToast(page, /creation initiated|success/i);

    // Wait for cluster to become Completed (operator's stable phase)
    const completed = await waitForClusterPhase(page, K8S_NAMESPACE, CLUSTER_NAME, "Completed");
    expect(completed).toBe(true);
  });
});
