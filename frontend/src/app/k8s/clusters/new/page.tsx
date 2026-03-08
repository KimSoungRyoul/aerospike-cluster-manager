"use client";

import dynamic from "next/dynamic";
import { PageHeader } from "@/components/common/page-header";
import { Skeleton } from "@/components/ui/skeleton";

const K8sClusterWizard = dynamic(
  () => import("@/components/k8s/k8s-cluster-wizard").then((m) => m.K8sClusterWizard),
  {
    loading: () => (
      <div className="space-y-4">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    ),
  },
);

export default function CreateK8sClusterPage() {
  return (
    <div className="animate-fade-in space-y-6 p-6 lg:p-8">
      <PageHeader
        title="Create Cluster"
        description="Deploy a new Aerospike CE cluster on Kubernetes"
      />
      <K8sClusterWizard />
    </div>
  );
}
