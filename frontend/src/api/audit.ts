import api from './client'

export interface AuditRecord {
  id: number
  username: string
  tool_name: string
  ai_suggested_args: Record<string, unknown>
  user_edited_args: Record<string, unknown> | null
  result_status: 'approved' | 'rejected'
  session_id: string
  thread_id: string
  timestamp: string
}

export interface AuditFilters {
  username?: string
  tool_name?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

export async function fetchAuditLog(filters: AuditFilters = {}): Promise<{ records: AuditRecord[]; count: number }> {
  const { data } = await api.get('/audit', { params: filters })
  return data
}
