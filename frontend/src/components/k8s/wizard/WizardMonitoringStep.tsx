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
import type { NetworkAccessType } from "@/lib/api/types";
import type { WizardMonitoringStepProps } from "./types";

export function WizardMonitoringStep({ form, updateForm }: WizardMonitoringStepProps) {
  return (
    <>
      <div className="flex items-center space-x-2">
        <Checkbox
          id="monitoring-enabled"
          checked={form.monitoring?.enabled ?? false}
          onCheckedChange={(checked) => {
            if (checked === true) {
              updateForm({ monitoring: { enabled: true, port: 9145 } });
            } else {
              updateForm({ monitoring: undefined });
            }
          }}
        />
        <Label htmlFor="monitoring-enabled" className="text-sm font-normal">
          Enable Prometheus monitoring
        </Label>
      </div>

      {form.monitoring?.enabled && (
        <div className="grid gap-2">
          <Label htmlFor="monitoring-port">Exporter Port</Label>
          <Input
            id="monitoring-port"
            type="number"
            min={1024}
            max={65535}
            value={form.monitoring.port}
            onChange={(e) =>
              updateForm({
                monitoring: {
                  enabled: true,
                  port: Math.min(65535, Math.max(1024, parseInt(e.target.value) || 9145)),
                },
              })
            }
          />
          <p className="text-muted-foreground text-xs">
            Port for the Aerospike Prometheus exporter sidecar (default: 9145).
          </p>
        </div>
      )}

      <div className="flex items-center space-x-2">
        <Checkbox
          id="dynamic-config"
          checked={form.enableDynamicConfig ?? false}
          onCheckedChange={(checked) => updateForm({ enableDynamicConfig: checked === true })}
        />
        <Label htmlFor="dynamic-config" className="text-sm font-normal">
          Enable dynamic config (apply config changes without restart)
        </Label>
      </div>

      <div className="space-y-3 rounded-lg border p-4">
        <span className="text-sm font-medium">Network Access</span>
        <p className="text-muted-foreground text-xs">
          Configure how clients and nodes communicate with the Aerospike cluster.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="grid gap-2">
            <Label htmlFor="access-type" className="text-xs">
              Client Access Type
            </Label>
            <Select
              value={form.networkPolicy?.accessType || "pod"}
              onValueChange={(v) => {
                const current = form.networkPolicy ?? { accessType: "pod" as const };
                updateForm({
                  networkPolicy:
                    v === "pod" && !current.alternateAccessType && !current.fabricType
                      ? undefined
                      : { ...current, accessType: v as NetworkAccessType },
                });
              }}
            >
              <SelectTrigger id="access-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pod">Pod IP (default)</SelectItem>
                <SelectItem value="hostInternal">Host Internal IP</SelectItem>
                <SelectItem value="hostExternal">Host External IP</SelectItem>
                <SelectItem value="configuredIP">Configured IP</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="fabric-type" className="text-xs">
              Fabric Type (inter-node)
            </Label>
            <Select
              value={form.networkPolicy?.fabricType || "pod"}
              onValueChange={(v) => {
                const current = form.networkPolicy ?? { accessType: "pod" as const };
                updateForm({
                  networkPolicy: {
                    ...current,
                    fabricType: v === "pod" ? undefined : (v as NetworkAccessType),
                  },
                });
              }}
            >
              <SelectTrigger id="fabric-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pod">Pod IP (default)</SelectItem>
                <SelectItem value="hostInternal">Host Internal IP</SelectItem>
                <SelectItem value="hostExternal">Host External IP</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </>
  );
}
