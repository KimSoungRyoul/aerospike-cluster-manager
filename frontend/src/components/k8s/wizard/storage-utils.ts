import type {
  StorageVolumeConfig,
  StorageSpec,
  VolumeSpec,
  VolumeSourceType,
} from "@/lib/api/types";

/** Type guard to check if storage is StorageSpec (multi-volume). */
export function isStorageSpec(s: StorageVolumeConfig | StorageSpec | undefined): s is StorageSpec {
  return !!s && "volumes" in s;
}

/** Create a default PVC volume. */
export function makeDefaultPvcVolume(
  name: string,
  storageClass: string,
  size: string,
  mountPath: string,
): VolumeSpec {
  return {
    name,
    source: "persistentVolume",
    persistentVolume: {
      storageClass,
      size,
      volumeMode: "Filesystem",
      accessModes: ["ReadWriteOnce"],
    },
    aerospike: { path: mountPath },
    cascadeDelete: true,
  };
}

/** Create a default emptyDir volume. */
export function makeDefaultEmptyDirVolume(name: string, mountPath: string): VolumeSpec {
  return {
    name,
    source: "emptyDir",
    emptyDir: {},
    aerospike: { path: mountPath },
  };
}

export const SOURCE_TYPE_LABELS: Record<VolumeSourceType, string> = {
  persistentVolume: "Persistent Volume (PVC)",
  emptyDir: "Empty Dir",
  secret: "Secret",
  configMap: "ConfigMap",
  hostPath: "Host Path",
};

/**
 * Reset a volume's source-specific fields when switching source type.
 * Returns a new VolumeSpec with the correct source defaults and all other
 * source fields cleared.
 */
export function resetVolumeSource(
  vol: VolumeSpec,
  newSource: VolumeSourceType,
  defaultStorageClass?: string,
): VolumeSpec {
  const updated: VolumeSpec = {
    ...vol,
    source: newSource,
    persistentVolume: undefined,
    emptyDir: undefined,
    secret: undefined,
    configMap: undefined,
    hostPath: undefined,
  };

  switch (newSource) {
    case "persistentVolume":
      updated.persistentVolume = {
        ...(defaultStorageClass ? { storageClass: defaultStorageClass } : {}),
        size: "10Gi",
        volumeMode: "Filesystem",
        accessModes: ["ReadWriteOnce"],
      };
      break;
    case "emptyDir":
      updated.emptyDir = {};
      break;
    case "secret":
      updated.secret = { secretName: "" };
      break;
    case "configMap":
      updated.configMap = { name: "" };
      break;
    case "hostPath":
      updated.hostPath = { path: "", type: "DirectoryOrCreate" };
      break;
  }

  return updated;
}
