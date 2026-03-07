import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  validateK8sName,
  validateK8sCpu,
  validateK8sMemory,
  parseCpuMillis,
  parseMemoryBytes,
} from "@/lib/validations/k8s";
import { AEROSPIKE_IMAGES } from "@/lib/constants";
import type { WizardBasicStepProps } from "./types";

export function WizardBasicStep({
  form,
  updateForm,
  k8sNamespaces,
  fetchingOptions,
  defaultResources,
}: WizardBasicStepProps) {
  const updateResource = (
    section: "requests" | "limits",
    field: "cpu" | "memory",
    value: string,
  ) => {
    const current = form.resources ?? defaultResources;
    updateForm({
      resources: {
        ...current,
        [section]: { ...current[section], [field]: value },
      },
    });
  };

  const res = form.resources ?? defaultResources;

  return (
    <div className="space-y-6">
      {/* Cluster identity */}
      <div className="space-y-4">
        <div className="grid gap-2">
          <Label htmlFor="cluster-name">Cluster Name</Label>
          <Input
            id="cluster-name"
            placeholder="my-aerospike"
            value={form.name}
            onChange={(e) => updateForm({ name: e.target.value.toLowerCase() })}
          />
          {form.name.length > 0 && validateK8sName(form.name) ? (
            <p className="text-destructive text-xs">{validateK8sName(form.name)}</p>
          ) : (
            <p className="text-muted-foreground text-xs">
              Lowercase letters, numbers, and hyphens only (K8s DNS name).
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label htmlFor="k8s-namespace">Namespace</Label>
            <Select value={form.namespace} onValueChange={(v) => updateForm({ namespace: v })}>
              <SelectTrigger id="k8s-namespace" disabled={fetchingOptions}>
                <SelectValue
                  placeholder={fetchingOptions ? "Loading namespaces..." : "Select a namespace"}
                />
              </SelectTrigger>
              <SelectContent>
                {k8sNamespaces.length > 0 ? (
                  k8sNamespaces.map((ns) => (
                    <SelectItem key={ns} value={ns}>
                      {ns}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="" disabled>
                    No namespaces available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="cluster-size">Size (1-8 nodes)</Label>
            <Input
              id="cluster-size"
              type="number"
              min={1}
              max={8}
              value={form.size}
              onChange={(e) =>
                updateForm({
                  size: Math.min(8, Math.max(1, parseInt(e.target.value) || 1)),
                })
              }
            />
          </div>
        </div>

        <div className="grid gap-2">
          <Label>Aerospike Image</Label>
          <Select value={form.image} onValueChange={(v) => updateForm({ image: v })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AEROSPIKE_IMAGES.map((img) => (
                <SelectItem key={img} value={img}>
                  {img}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Resources */}
      <div className="space-y-3 rounded-lg border p-4">
        <span className="text-sm font-medium">Resources</span>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label htmlFor="cpu-request" className="text-xs">
              CPU Request
            </Label>
            <Input
              id="cpu-request"
              value={form.resources?.requests.cpu || "500m"}
              onChange={(e) => updateResource("requests", "cpu", e.target.value)}
            />
            {validateK8sCpu(form.resources?.requests.cpu || "500m") && (
              <p className="text-destructive text-xs">
                {validateK8sCpu(form.resources?.requests.cpu || "500m")}
              </p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="cpu-limit" className="text-xs">
              CPU Limit
            </Label>
            <Input
              id="cpu-limit"
              value={form.resources?.limits.cpu || "2"}
              onChange={(e) => updateResource("limits", "cpu", e.target.value)}
            />
            {validateK8sCpu(form.resources?.limits.cpu || "2") && (
              <p className="text-destructive text-xs">
                {validateK8sCpu(form.resources?.limits.cpu || "2")}
              </p>
            )}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label htmlFor="mem-request" className="text-xs">
              Memory Request
            </Label>
            <Input
              id="mem-request"
              value={form.resources?.requests.memory || "1Gi"}
              onChange={(e) => updateResource("requests", "memory", e.target.value)}
            />
            {validateK8sMemory(form.resources?.requests.memory || "1Gi") && (
              <p className="text-destructive text-xs">
                {validateK8sMemory(form.resources?.requests.memory || "1Gi")}
              </p>
            )}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="mem-limit" className="text-xs">
              Memory Limit
            </Label>
            <Input
              id="mem-limit"
              value={form.resources?.limits.memory || "4Gi"}
              onChange={(e) => updateResource("limits", "memory", e.target.value)}
            />
            {validateK8sMemory(form.resources?.limits.memory || "4Gi") && (
              <p className="text-destructive text-xs">
                {validateK8sMemory(form.resources?.limits.memory || "4Gi")}
              </p>
            )}
          </div>
        </div>

        {(() => {
          const cpuValid = !validateK8sCpu(res.requests.cpu) && !validateK8sCpu(res.limits.cpu);
          const memValid =
            !validateK8sMemory(res.requests.memory) && !validateK8sMemory(res.limits.memory);
          return (
            <>
              {cpuValid && parseCpuMillis(res.limits.cpu) < parseCpuMillis(res.requests.cpu) && (
                <p className="text-destructive text-xs">CPU limit must be &gt;= request</p>
              )}
              {memValid &&
                parseMemoryBytes(res.limits.memory) < parseMemoryBytes(res.requests.memory) && (
                  <p className="text-destructive text-xs">Memory limit must be &gt;= request</p>
                )}
            </>
          );
        })()}
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="auto-connect"
          checked={form.autoConnect}
          onCheckedChange={(checked) => updateForm({ autoConnect: checked === true })}
        />
        <Label htmlFor="auto-connect" className="text-sm font-normal">
          Auto-connect after creation
        </Label>
      </div>
    </div>
  );
}
