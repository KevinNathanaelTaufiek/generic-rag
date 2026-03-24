import api from './client'

export interface AuditRecord {
  id: number
  username: string
  action: string
  details: Record<string, unknown>
  changes: Record<string, unknown> | null
  status: string
  session_id: string
  thread_id: string
  timestamp: string
}

export interface AuditFilters {
  username?: string
  action?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

export async function fetchAuditLog(filters: AuditFilters = {}): Promise<{ records: AuditRecord[]; count: number }> {
  const { data } = await api.get('/audit', { params: filters })
  return data
}
