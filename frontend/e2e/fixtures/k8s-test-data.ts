import { Page } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3100";

export const K8S_NAMESPACE = "acko-system";
export const K8S_TEST_CLUSTER_PREFIX = "e2e-";
export const K8S_TEST_CLUSTER_NAME = "e2e-test";
export const K8S_TEST_TEMPLATE_NAME = "e2e-template";

export async function waitForK8sApi(page: Page, timeout = 30_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const res = await page.request.get(`${BASE_URL}/api/k8s/templates`);
      if (res.ok()) return true;
    } catch {
      // retry
    }
    await page.waitForTimeout(2_000);
  }
  return false;
}

export async function getK8sTemplates(page: Page): Promise<{ name: string; namespace: string }[]> {
  const res = await page.request.get(`${BASE_URL}/api/k8s/templates`);
  if (!res.ok()) return [];
  return res.json();
}

export async function createK8sClusterViaApi(
  page: Page,
  name: string,
  opts: {
    namespace?: string;
    size?: number;
    image?: string;
    templateRef?: { name: string; namespace?: string };
  } = {},
) {
  const res = await page.request.post(`${BASE_URL}/api/k8s/clusters`, {
    data: {
      name,
      namespace: opts.namespace ?? K8S_NAMESPACE,
      size: opts.size ?? 1,
      image: opts.image ?? "aerospike:ce-8.1.1.1",
      namespaces: [
        {
          name: "test",
          replicationFactor: 1,
          storageEngine: { type: "memory", dataSize: 1073741824 },
        },
      ],
      resources: {
        requests: { cpu: "100m", memory: "256Mi" },
        limits: { cpu: "500m", memory: "512Mi" },
      },
      autoConnect: false,
      ...(opts.templateRef ? { templateRef: opts.templateRef } : {}),
    },
  });
  if (!res.ok()) {
    throw new Error(`Failed to create cluster "${name}": ${await res.text()}`);
  }
  return res.json();
}

export async function deleteK8sCluster(page: Page, namespace: string, name: string) {
  await page.request.delete(`${BASE_URL}/api/k8s/clusters/${namespace}/${name}`);
}

export async function waitForClusterPhase(
  page: Page,
  namespace: string,
  name: string,
  targetPhase: string,
  timeout = 180_000,
): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const res = await page.request.get(`${BASE_URL}/api/k8s/clusters/${namespace}/${name}`);
      if (res.ok()) {
        const detail = await res.json();
        if (detail.phase === targetPhase) return true;
      }
    } catch {
      // retry
    }
    await page.waitForTimeout(5_000);
  }
  return false;
}

export async function cleanupK8sClusters(page: Page, prefix = K8S_TEST_CLUSTER_PREFIX) {
  try {
    const res = await page.request.get(`${BASE_URL}/api/k8s/clusters`);
    if (!res.ok()) return;
    const clusters = (await res.json()) as { name: string; namespace: string }[];
    for (const cluster of clusters) {
      if (cluster.name.startsWith(prefix)) {
        try {
          await deleteK8sCluster(page, cluster.namespace, cluster.name);
        } catch {
          // ignore cleanup errors
        }
      }
    }
  } catch {
    // ignore
  }
}

export async function cleanupK8sTemplates(page: Page, prefix = K8S_TEST_CLUSTER_PREFIX) {
  try {
    const res = await page.request.get(`${BASE_URL}/api/k8s/templates`);
    if (!res.ok()) return;
    const templates = (await res.json()) as { name: string; namespace: string }[];
    for (const tmpl of templates) {
      if (tmpl.name.startsWith(prefix)) {
        try {
          await page.request.delete(`${BASE_URL}/api/k8s/templates/${tmpl.namespace}/${tmpl.name}`);
        } catch {
          // ignore
        }
      }
    }
  } catch {
    // ignore
  }
}
