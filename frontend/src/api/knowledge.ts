import api from './client'

export interface DocumentInfo {
  doc_id: string
  title: string
  source_type: string
  created_at: string
  chunk_count: number
}

export interface DocumentListResponse {
  documents: DocumentInfo[]
  total: number
}

export async function addText(content: string, title?: string): Promise<DocumentInfo> {
  const { data } = await api.post<DocumentInfo>('/knowledge/text', { content, title })
  return data
}

export async function uploadFile(file: File): Promise<DocumentInfo> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<DocumentInfo>('/knowledge/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const { data } = await api.get<DocumentListResponse>('/knowledge')
  return data
}

export async function deleteDocument(docId: string): Promise<void> {
  await api.delete(`/knowledge/${docId}`)
}

export async function reindex(): Promise<{ reindexed_count: number; message: string }> {
  const { data } = await api.post('/knowledge/reindex')
  return data
}
