/**
 * Sample-data seeder types mirrored from backend Pydantic models.
 * See: backend/src/aerospike_cluster_manager_api/routers/sample_data.py
 */

export interface CreateSampleDataRequest {
  namespace: string
  setName?: string
  recordCount?: number
  createIndexes?: boolean
}

export interface CreateSampleDataResponse {
  recordsCreated: number
  indexesCreated: string[]
  indexesSkipped: string[]
  elapsedMs: number
}
