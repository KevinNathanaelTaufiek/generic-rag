import api from './client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SourceRef {
  doc_id: string
  title: string
  excerpt: string
}

export interface ChatRequest {
  message: string
  session_id?: string
  history?: ChatMessage[]
  strict_mode?: boolean
}

export interface ChatResponse {
  answer: string
  sources: SourceRef[]
  session_id: string
}

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', req)
  return data
}
