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

export interface DocumentContent {
  doc_id: string
  title: string
  source_type: string
  content: string
  created_at: string
}

export interface PreviewResponse {
  title: string
  source_type: string
  content: string
  estimated_chunks: number
  char_count: number
}

export async function previewText(content: string, title?: string): Promise<PreviewResponse> {
  const { data } = await api.post<PreviewResponse>('/knowledge/preview/text', { content, title })
  return data
}

export async function previewFile(file: File): Promise<PreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<PreviewResponse>('/knowledge/preview/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
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

export async function getDocumentContent(docId: string): Promise<DocumentContent> {
  const { data } = await api.get<DocumentContent>(`/knowledge/${docId}/content`)
  return data
}

export async function deleteDocument(docId: string): Promise<void> {
  await api.delete(`/knowledge/${docId}`)
}

export async function reindex(): Promise<{ reindexed_count: number; message: string }> {
  const { data } = await api.post('/knowledge/reindex')
  return data
}
