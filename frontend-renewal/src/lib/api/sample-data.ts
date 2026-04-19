/**
 * Sample-data seeder — populates a namespace with sample records + indexes.
 * Endpoint base: /api/sample-data
 */

import type {
  CreateSampleDataRequest,
  CreateSampleDataResponse,
} from "../types/sample-data"
import { apiPost } from "./client"

/** POST /api/sample-data/{conn_id} — create sample records and (optionally) indexes. */
export function createSampleData(
  connId: string,
  body: CreateSampleDataRequest,
): Promise<CreateSampleDataResponse> {
  return apiPost(`/sample-data/${encodeURIComponent(connId)}`, body, {
    timeoutMs: 60_000,
  })
}
