import type { BinDataType, FilterOperator } from "@/lib/types/query"

export const CE_LIMITS = {
  MAX_NODES: 8,
  MAX_NAMESPACES: 2,
  MAX_DATA_TB: 5,
  DURABLE_DELETE: false,
  XDR: false,
} as const

export const BRAND_COLORS = {
  primary: "#2563EB",
  accent: "#F59E0B",
  navy: "#111827",
  success: "#059669",
  error: "#DC2626",
} as const

export const PAGE_SIZE_OPTIONS = [25, 50, 100] as const

export const DEFAULT_PAGE_SIZE = 25

export const MAX_QUERY_RECORDS = 10_000

export const METRIC_HISTORY_POINTS = 60
export const METRIC_INTERVAL_MS = 5000

export const K8S_DETAIL_POLL_INTERVAL_MS = 5_000
export const K8S_DETAIL_POLL_MAX_BACKOFF_MS = 60_000
export const SIDEBAR_HEALTH_POLL_INTERVAL_MS = 30_000

// SSE (Server-Sent Events) streaming
export const SSE_RECONNECT_BASE_MS = 1_000
export const SSE_RECONNECT_MAX_MS = 30_000
export const SSE_HEARTBEAT_TIMEOUT_MS = 45_000
export const SSE_MAX_RETRIES_BEFORE_FALLBACK = 3

export const PRESET_COLORS = [
  "#0097D3",
  "#c4373a",
  "#22c55e",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
] as const

export const BIN_TYPES = [
  "string",
  "integer",
  "float",
  "bool",
  "list",
  "map",
  "bytes",
  "geojson",
] as const

export type BinType = (typeof BIN_TYPES)[number]

export const FILTER_OPERATORS_BY_TYPE: Record<
  BinDataType,
  { value: FilterOperator; label: string }[]
> = {
  integer: [
    { value: "eq", label: "=" },
    { value: "ne", label: "≠" },
    { value: "gt", label: ">" },
    { value: "ge", label: "≥" },
    { value: "lt", label: "<" },
    { value: "le", label: "≤" },
    { value: "between", label: "Between" },
    { value: "exists", label: "Exists" },
    { value: "not_exists", label: "Not Exists" },
  ],
  float: [
    { value: "eq", label: "=" },
    { value: "ne", label: "≠" },
    { value: "gt", label: ">" },
    { value: "ge", label: "≥" },
    { value: "lt", label: "<" },
    { value: "le", label: "≤" },
    { value: "between", label: "Between" },
    { value: "exists", label: "Exists" },
    { value: "not_exists", label: "Not Exists" },
  ],
  string: [
    { value: "eq", label: "Equals" },
    { value: "ne", label: "Not Equals" },
    { value: "contains", label: "Contains" },
    { value: "not_contains", label: "Not Contains" },
    { value: "regex", label: "Regex" },
    { value: "exists", label: "Exists" },
    { value: "not_exists", label: "Not Exists" },
  ],
  bool: [
    { value: "is_true", label: "Is True" },
    { value: "is_false", label: "Is False" },
    { value: "exists", label: "Exists" },
  ],
  geo: [
    { value: "geo_within", label: "Within Region" },
    { value: "geo_contains", label: "Contains Point" },
    { value: "exists", label: "Exists" },
  ],
  list: [
    { value: "exists", label: "Exists" },
    { value: "not_exists", label: "Not Exists" },
  ],
  map: [
    { value: "exists", label: "Exists" },
    { value: "not_exists", label: "Not Exists" },
  ],
}

/** Operators that require NO value input */
export const NO_VALUE_OPERATORS: FilterOperator[] = [
  "exists",
  "not_exists",
  "is_true",
  "is_false",
]

/** Operators that require TWO value inputs */
export const DUAL_VALUE_OPERATORS: FilterOperator[] = ["between"]

export const AEROSPIKE_IMAGES = ["aerospike:ce-8.1.1.1"] as const
