// === Connection ===
export interface ConnectionProfile {
  id: string;
  name: string;
  hosts: string[];
  port: number;
  clusterName?: string;
  username?: string;
  password?: string;
  color: string;
  createdAt: string;
  updatedAt: string;
  description?: string;
}

export type HealthErrorType =
  | "timeout"
  | "connection_refused"
  | "cluster_error"
  | "auth_error"
  | "unknown";

export interface ConnectionStatus {
  connected: boolean;
  nodeCount: number;
  namespaceCount: number;
  build?: string;
  edition?: string;
  memoryUsed?: number;
  memoryTotal?: number;
  diskUsed?: number;
  diskTotal?: number;
  tendHealthy?: boolean;
  error?: string;
  errorType?: HealthErrorType;
}

export interface ConnectionWithStatus extends ConnectionProfile {
  status?: ConnectionStatus;
}
