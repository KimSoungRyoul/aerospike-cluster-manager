import type { BinDataType, FilterOperator } from "@/lib/api/types";

export const CE_LIMITS = {
  MAX_NODES: 8,
  MAX_NAMESPACES: 2,
  MAX_DATA_TB: 5,
  DURABLE_DELETE: false,
  XDR: false,
} as const;

export const BRAND_COLORS = {
  yellow: "#ffe600",
  blue: "#0097D3",
  navy: "#0D1B32",
  red: "#c4373a",
} as const;

export const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;

export const DEFAULT_PAGE_SIZE = 25;

export const METRIC_HISTORY_POINTS = 60;
export const METRIC_INTERVAL_MS = 2000;

export const K8S_DETAIL_POLL_INTERVAL_MS = 5_000;
export const K8S_DETAIL_POLL_MAX_BACKOFF_MS = 60_000;
export const SIDEBAR_HEALTH_POLL_INTERVAL_MS = 30_000;

export const PRESET_COLORS = [
  "#0097D3",
  "#c4373a",
  "#22c55e",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
] as const;

export const BIN_TYPES = [
  "string",
  "integer",
  "float",
  "bool",
  "list",
  "map",
  "bytes",
  "geojson",
] as const;

export type BinType = (typeof BIN_TYPES)[number];

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
};

/** Operators that require NO value input */
export const NO_VALUE_OPERATORS: FilterOperator[] = ["exists", "not_exists", "is_true", "is_false"];

/** Operators that require TWO value inputs */
export const DUAL_VALUE_OPERATORS: FilterOperator[] = ["between"];

export const AEROSPIKE_IMAGES = ["aerospike:ce-8.1.1.1"] as const;

export const BIN_TYPE_COLORS: Record<BinType, string> = {
  string: "bg-success/10 text-success border-success/20",
  integer: "bg-info/10 text-info border-info/20",
  float: "bg-info/10 text-info border-info/20",
  bool: "bg-secondary/10 text-secondary border-secondary/20",
  list: "bg-warning/10 text-warning border-warning/20",
  map: "bg-accent/15 text-accent border-accent/25",
  bytes: "bg-base-200 text-muted-foreground border-base-300",
  geojson: "bg-info/10 text-info border-info/20",
};

export const BIN_TYPE_BORDER_COLORS: Record<BinType, string> = {
  string: "border-l-success/40",
  integer: "border-l-info/40",
  float: "border-l-info/40",
  bool: "border-l-secondary/40",
  list: "border-l-warning/40",
  map: "border-l-accent/40",
  bytes: "border-l-muted-foreground/20",
  geojson: "border-l-info/40",
};
