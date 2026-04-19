// Re-export facade. Stream A originally inlined these helpers; Stream E
// now owns the canonical versions in `src/lib/*`. Keep this file as a thin
// barrel so A's import paths continue to work without sprawling edits.
// New code should import directly from the sources referenced below.

export { detectBinTypes } from "@/lib/bin-type-detector"
export {
  buildBinEntriesFromRecord,
  createEmptyBinEntry,
  detectBinType,
  parseBinValue,
  serializeBinValue,
} from "@/lib/bin-utils"
export {
  NEVER_EXPIRE_TTL,
  formatNumber,
  formatTTLAsExpiry,
  formatTTLHuman,
  formatUptime,
  truncateMiddle,
} from "@/lib/formatters"
export { getErrorMessage, uuid } from "@/lib/utils"
export type { BinEntry } from "@/lib/types/record"
