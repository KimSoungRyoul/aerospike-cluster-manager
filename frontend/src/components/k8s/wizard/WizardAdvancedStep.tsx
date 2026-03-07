import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { WizardMonitoringStep } from "./WizardMonitoringStep";
import { WizardAclStep } from "./WizardAclStep";
import { WizardRollingUpdateStep } from "./WizardRollingUpdateStep";
import { WizardRackConfigStep } from "./WizardRackConfigStep";
import type { WizardAdvancedStepProps } from "./types";

function CollapsibleSection({
  title,
  summary,
  defaultOpen = false,
  children,
}: {
  title: string;
  summary: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div>
          <span className="text-sm font-medium">{title}</span>
          <span className="text-muted-foreground ml-2 text-xs">{summary}</span>
        </div>
        {open ? (
          <ChevronDown className="text-muted-foreground h-4 w-4" />
        ) : (
          <ChevronRight className="text-muted-foreground h-4 w-4" />
        )}
      </button>
      {open && <div className="space-y-4 border-t px-4 pt-4 pb-4">{children}</div>}
    </div>
  );
}

export function WizardAdvancedStep({
  form,
  updateForm,
  k8sSecrets,
  nodes,
}: WizardAdvancedStepProps) {
  const monitoringSummary = form.monitoring?.enabled
    ? `Enabled (port ${form.monitoring.port})`
    : "Disabled";

  const aclSummary = form.acl?.enabled
    ? `${form.acl.roles.length} roles, ${form.acl.users.length} users`
    : "Disabled";

  const rollingSummary =
    form.rollingUpdate?.batchSize != null || form.rollingUpdate?.maxUnavailable
      ? "Customized"
      : "Default";

  const rackSummary =
    (form.rackConfig?.racks ?? []).length > 0
      ? `${form.rackConfig!.racks.length} rack(s)`
      : "Single rack";

  return (
    <div className="space-y-3">
      <p className="text-muted-foreground text-sm">
        Configure optional settings. All sections have sensible defaults — expand only what you
        need.
      </p>

      <CollapsibleSection title="Monitoring & Network" summary={monitoringSummary}>
        <WizardMonitoringStep form={form} updateForm={updateForm} />
      </CollapsibleSection>

      <CollapsibleSection title="Security (ACL)" summary={aclSummary}>
        <WizardAclStep form={form} updateForm={updateForm} k8sSecrets={k8sSecrets} />
      </CollapsibleSection>

      <CollapsibleSection title="Rolling Update" summary={rollingSummary}>
        <WizardRollingUpdateStep form={form} updateForm={updateForm} />
      </CollapsibleSection>

      <CollapsibleSection title="Rack Config" summary={rackSummary}>
        <WizardRackConfigStep form={form} updateForm={updateForm} nodes={nodes} />
      </CollapsibleSection>
    </div>
  );
}
