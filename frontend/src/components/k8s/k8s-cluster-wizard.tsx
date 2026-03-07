"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingButton } from "@/components/common/loading-button";
import { InlineAlert } from "@/components/common/inline-alert";
import { useK8sClusterStore } from "@/stores/k8s-cluster-store";
import { api } from "@/lib/api/client";
import { getErrorMessage } from "@/lib/utils";
import {
  validateK8sName,
  validateK8sCpu,
  validateK8sMemory,
  validateNamespaces,
  parseCpuMillis,
  parseMemoryBytes,
} from "@/lib/validations/k8s";
import { AEROSPIKE_IMAGES } from "@/lib/constants";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import type {
  CreateK8sClusterRequest,
  MonitoringConfig,
  ACLConfig,
  RollingUpdateConfig,
  TemplateOverrides,
  K8sNodeInfo,
  StorageVolumeConfig,
} from "@/lib/api/types";
import {
  WizardBasicStep,
  WizardNamespaceStorageStep,
  WizardMonitoringStep,
  WizardResourcesStep,
  WizardAclStep,
  WizardRollingUpdateStep,
  WizardRackConfigStep,
  WizardReviewStep,
} from "./wizard";

const STEPS = [
  "Basic",
  "Namespace & Storage",
  "Monitoring & Options",
  "Resources",
  "Security (ACL)",
  "Rolling Update",
  "Rack Config",
  "Review",
];

export function K8sClusterWizard() {
  const router = useRouter();
  const { createCluster, templates, fetchTemplates } = useK8sClusterStore();
  const [step, setStep] = useState(0);
  const [creating, setCreating] = useState(false);
  const [k8sNamespaces, setK8sNamespaces] = useState<string[]>([]);
  const [storageClasses, setStorageClasses] = useState<string[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [fetchingOptions, setFetchingOptions] = useState(true);
  const [creationError, setCreationError] = useState<string | null>(null);
  const [k8sSecrets, setK8sSecrets] = useState<string[]>([]);
  const [overridesOpen, setOverridesOpen] = useState(false);
  const [templateOverrides, setTemplateOverrides] = useState<TemplateOverrides>({});

  const DEFAULT_RESOURCES = {
    requests: { cpu: "500m", memory: "1Gi" },
    limits: { cpu: "2", memory: "4Gi" },
  };

  const DEFAULT_STORAGE: StorageVolumeConfig = {
    storageClass: "standard",
    size: "10Gi",
    mountPath: "/opt/aerospike/data",
  };

  const [form, setForm] = useState<CreateK8sClusterRequest>({
    name: "",
    namespace: "",
    size: 1,
    image: AEROSPIKE_IMAGES[0],
    namespaces: [
      {
        name: "test",
        replicationFactor: 1,
        storageEngine: { type: "memory", dataSize: 1073741824 },
      },
    ],
    resources: DEFAULT_RESOURCES,
    monitoring: undefined as MonitoringConfig | undefined,
    templateRef: undefined as string | undefined,
    enableDynamicConfig: false,
    autoConnect: true,
    acl: undefined as ACLConfig | undefined,
    rollingUpdate: undefined as RollingUpdateConfig | undefined,
    rackConfig: { racks: [] },
  });

  const [nodes, setNodes] = useState<K8sNodeInfo[]>([]);

  useEffect(() => {
    setFetchingOptions(true);
    const errors: string[] = [];
    Promise.allSettled([
      api
        .getK8sNamespaces()
        .then((ns) => {
          setK8sNamespaces(ns);
          if (ns.length > 0) {
            const preferred = ns.includes("default") ? "default" : ns[0];
            setForm((prev) => ({ ...prev, namespace: preferred }));
          }
        })
        .catch((err) => {
          errors.push(`Failed to fetch K8s namespaces: ${getErrorMessage(err)}`);
        }),
      api
        .getK8sStorageClasses()
        .then((sc) => setStorageClasses(sc))
        .catch((err) => {
          errors.push(`Failed to fetch storage classes: ${getErrorMessage(err)}`);
        }),
      fetchTemplates().catch(() => {
        // Templates are optional, silently ignore fetch failures
      }),
    ]).finally(() => {
      setFetchError(errors.length > 0 ? `${errors.join(". ")}. Using defaults.` : null);
      setFetchingOptions(false);
    });
  }, [fetchTemplates]);

  // Fetch K8s secrets when on the ACL step and namespace is available
  useEffect(() => {
    if (step === 4 && form.acl?.enabled && form.namespace) {
      api
        .getK8sSecrets(form.namespace)
        .then(setK8sSecrets)
        .catch(() => setK8sSecrets([]));
    }
  }, [step, form.acl?.enabled, form.namespace]);

  // Fetch K8s nodes when on the Rack Config step
  useEffect(() => {
    if (step === 6) {
      api
        .getK8sNodes()
        .then(setNodes)
        .catch((err) => {
          console.error("Failed to fetch K8s nodes:", err);
          toast.error("Failed to load node information for zone selection");
        });
    }
  }, [step]);

  const updateForm = (updates: Partial<CreateK8sClusterRequest>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  };

  const canProceed = () => {
    if (step === 0) {
      return validateK8sName(form.name) === null && form.namespace.length > 0;
    }
    if (step === 1) {
      return validateNamespaces(form.namespaces, form.size) === null;
    }
    if (step === 2) {
      return true;
    }
    if (step === 3) {
      const res = form.resources ?? DEFAULT_RESOURCES;
      if (validateK8sCpu(res.requests.cpu) !== null) return false;
      if (validateK8sCpu(res.limits.cpu) !== null) return false;
      if (validateK8sMemory(res.requests.memory) !== null) return false;
      if (validateK8sMemory(res.limits.memory) !== null) return false;
      if (parseCpuMillis(res.limits.cpu) < parseCpuMillis(res.requests.cpu)) return false;
      if (parseMemoryBytes(res.limits.memory) < parseMemoryBytes(res.requests.memory)) return false;
      return true;
    }
    if (step === 4) {
      if (form.acl?.enabled) {
        if (form.acl.users.length === 0) return false;
        for (const user of form.acl.users) {
          if (!user.name.trim() || !user.secretName.trim() || user.roles.length === 0) return false;
        }
        for (const role of form.acl.roles) {
          if (!role.name.trim() || role.privileges.length === 0) return false;
        }
      }
      return true;
    }
    if (step === 5) {
      return true;
    }
    if (step === 6) {
      return true;
    }
    return true;
  };

  const handleCreate = async () => {
    setCreationError(null);
    setCreating(true);
    try {
      const payload = { ...form };
      if (payload.rollingUpdate) {
        const ru = payload.rollingUpdate;
        if (ru.batchSize == null && !ru.maxUnavailable && !ru.disablePDB) {
          payload.rollingUpdate = undefined;
        }
      }
      if (
        payload.networkPolicy &&
        payload.networkPolicy.accessType === "pod" &&
        !payload.networkPolicy.alternateAccessType &&
        !payload.networkPolicy.fabricType
      ) {
        payload.networkPolicy = undefined;
      }
      if (payload.rackConfig && payload.rackConfig.racks.length > 0) {
        payload.rackConfig = {
          racks: payload.rackConfig.racks.map((r) => ({
            id: r.id,
            ...(r.zone ? { zone: r.zone } : {}),
            ...(r.region ? { region: r.region } : {}),
            ...(r.maxPodsPerNode != null ? { maxPodsPerNode: r.maxPodsPerNode } : {}),
          })),
        } as typeof payload.rackConfig;
      } else {
        payload.rackConfig = undefined;
      }
      await createCluster(payload);
      toast.success(`Cluster "${form.name}" creation initiated`);
      router.push("/k8s/clusters");
    } catch (err) {
      const msg = getErrorMessage(err);
      setCreationError(msg);
      toast.error("Failed to create cluster");
    } finally {
      setCreating(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(0)} GiB`;
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(0)} MiB`;
    return `${bytes} bytes`;
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <InlineAlert message={fetchError} variant="warning" />
      <InlineAlert message={creationError} variant="error" />

      {/* Step indicator */}
      <nav aria-label="Wizard steps" className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground text-sm font-medium">
            Step {step + 1} of {STEPS.length}
            <span className="text-muted-foreground/60 mx-1.5">—</span>
            <span className="text-foreground">{STEPS[step]}</span>
          </p>
        </div>
        <Progress value={((step + 1) / STEPS.length) * 100} className="h-1" />
        <div className="flex items-center gap-2" role="tablist">
          {STEPS.map((label, i) => (
            <button
              key={label}
              onClick={() => i < step && setStep(i)}
              disabled={i > step}
              role="tab"
              aria-selected={i === step}
              aria-label={`Step ${i + 1}: ${label}`}
              aria-current={i === step ? "step" : undefined}
              className="flex items-center gap-2"
            >
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
                  i === step
                    ? "bg-accent text-accent-foreground"
                    : i < step
                      ? "bg-accent/20 text-accent"
                      : "bg-muted text-muted-foreground"
                }`}
              >
                {i + 1}
              </span>
              <span
                className={`hidden text-sm sm:inline ${
                  i === step ? "text-foreground font-medium" : "text-muted-foreground"
                }`}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && <span className="bg-border mx-1 h-px w-4 sm:w-8" />}
            </button>
          ))}
        </div>
      </nav>

      {fetchingOptions && (
        <div className="flex items-center justify-center gap-2 py-4">
          <div className="border-accent h-5 w-5 animate-spin rounded-full border-2 border-t-transparent" />
          <span className="text-muted-foreground text-sm">Loading K8s options...</span>
        </div>
      )}

      {/* Step content */}
      <Card>
        <CardHeader>
          <CardTitle>{STEPS[step]}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 0 && (
            <WizardBasicStep
              form={form}
              updateForm={updateForm}
              k8sNamespaces={k8sNamespaces}
              fetchingOptions={fetchingOptions}
            />
          )}

          {step === 1 && (
            <WizardNamespaceStorageStep
              form={form}
              updateForm={updateForm}
              storageClasses={storageClasses}
              defaultStorage={DEFAULT_STORAGE}
            />
          )}

          {step === 2 && (
            <WizardMonitoringStep
              form={form}
              updateForm={updateForm}
              templates={templates}
              overridesOpen={overridesOpen}
              setOverridesOpen={setOverridesOpen}
              templateOverrides={templateOverrides}
              setTemplateOverrides={setTemplateOverrides}
            />
          )}

          {step === 3 && (
            <WizardResourcesStep
              form={form}
              updateForm={updateForm}
              defaultResources={DEFAULT_RESOURCES}
            />
          )}

          {step === 4 && (
            <WizardAclStep form={form} updateForm={updateForm} k8sSecrets={k8sSecrets} />
          )}

          {step === 5 && <WizardRollingUpdateStep form={form} updateForm={updateForm} />}

          {step === 6 && <WizardRackConfigStep form={form} updateForm={updateForm} nodes={nodes} />}

          {step === 7 && <WizardReviewStep form={form} formatBytes={formatBytes} />}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => (step === 0 ? router.back() : setStep(step - 1))}
          disabled={creating}
        >
          {step === 0 ? "Cancel" : "Back"}
        </Button>
        {step < STEPS.length - 1 ? (
          <Button onClick={() => setStep(step + 1)} disabled={!canProceed()}>
            Next
          </Button>
        ) : (
          <LoadingButton onClick={handleCreate} loading={creating} disabled={creating}>
            Create Cluster
          </LoadingButton>
        )}
      </div>
    </div>
  );
}
