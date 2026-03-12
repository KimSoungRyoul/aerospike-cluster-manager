import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { validateK8sName } from "@/lib/validations/k8s";
import type { CreateK8sClusterRequest } from "@/lib/api/types";

interface WizardTemplateNameStepProps {
  form: CreateK8sClusterRequest;
  updateForm: (updates: Partial<CreateK8sClusterRequest>) => void;
  k8sNamespaces: string[];
  fetchingOptions: boolean;
}

export function WizardTemplateNameStep({
  form,
  updateForm,
  k8sNamespaces,
  fetchingOptions,
}: WizardTemplateNameStepProps) {
  return (
    <div className="space-y-4">
      <p className="text-base-content/60 text-sm">
        All other settings are pre-filled from the template. Just provide a name and namespace.
      </p>

      <div className="grid gap-2">
        <Label htmlFor="cluster-name">Cluster Name</Label>
        <Input
          id="cluster-name"
          placeholder="my-aerospike"
          value={form.name}
          onChange={(e) => updateForm({ name: e.target.value.toLowerCase() })}
        />
        {form.name.length > 0 && validateK8sName(form.name) ? (
          <p className="text-error text-xs">{validateK8sName(form.name)}</p>
        ) : (
          <p className="text-base-content/60 text-xs">
            Lowercase letters, numbers, and hyphens only (K8s DNS name).
          </p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="k8s-namespace">Namespace</Label>
        <Select
          value={form.namespace}
          onChange={(e) => updateForm({ namespace: e.target.value })}
          id="k8s-namespace"
          disabled={fetchingOptions}
        >
          <option value="">
            {fetchingOptions ? "Loading namespaces..." : "Select a namespace"}
          </option>
          {k8sNamespaces.map((ns) => (
            <option key={ns} value={ns}>
              {ns}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}
