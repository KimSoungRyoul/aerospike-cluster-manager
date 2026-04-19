import type { BinDataType } from "@/lib/types/query"
import type { AerospikeRecord } from "@/lib/types/record"

/**
 * Detect bin data types from a sample of records.
 * Uses first non-null value for each bin to determine type.
 */
export function detectBinTypes(
  records: AerospikeRecord[],
): Record<string, BinDataType> {
  const types: Record<string, BinDataType> = {}

  for (const record of records) {
    for (const [bin, value] of Object.entries(record.bins)) {
      if (types[bin]) continue
      if (value === null || value === undefined) continue

      if (typeof value === "boolean") {
        types[bin] = "bool"
      } else if (typeof value === "number") {
        types[bin] = Number.isInteger(value) ? "integer" : "float"
      } else if (typeof value === "string") {
        types[bin] = "string"
      } else if (Array.isArray(value)) {
        types[bin] = "list"
      } else if (typeof value === "object") {
        const obj = value as Record<string, unknown>
        if ("type" in obj && "coordinates" in obj) {
          types[bin] = "geo"
        } else {
          types[bin] = "map"
        }
      }
    }
  }

  return types
}
