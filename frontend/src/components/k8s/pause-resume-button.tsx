import { Button } from "@/components/ui/button";
import { useToastStore } from "@/stores/toast-store";
import { getErrorMessage } from "@/lib/utils";
import type { K8sClusterPhase } from "@/lib/api/types";

interface PauseResumeButtonProps {
  namespace: string;
  name: string;
  phase: K8sClusterPhase;
  disabled?: boolean;
  pauseCluster: (namespace: string, name: string) => Promise<void>;
  resumeCluster: (namespace: string, name: string) => Promise<void>;
}

export function PauseResumeButton({
  namespace,
  name,
  phase,
  disabled,
  pauseCluster,
  resumeCluster,
}: PauseResumeButtonProps) {
  if (phase === "Paused") {
    return (
      <Button
        variant="success"
        size="sm"
        disabled={disabled}
        onClick={async () => {
          try {
            await resumeCluster(namespace, name);
            useToastStore.getState().addToast("success", "Reconciliation resumed");
          } catch (err) {
            useToastStore.getState().addToast("error", getErrorMessage(err));
          }
        }}
      >
        Resume
      </Button>
    );
  }

  return (
    <Button
      variant="neutral"
      size="sm"
      disabled={disabled}
      onClick={async () => {
        try {
          await pauseCluster(namespace, name);
          useToastStore.getState().addToast("success", "Reconciliation paused");
        } catch (err) {
          useToastStore.getState().addToast("error", getErrorMessage(err));
        }
      }}
    >
      Pause
    </Button>
  );
}
