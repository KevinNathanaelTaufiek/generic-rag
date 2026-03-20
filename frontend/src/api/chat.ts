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

export interface ToolCallInfo {
  tool_name: string
  tool_args: Record<string, unknown>
  description: string
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
  status: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
}

export interface ToolApprovalRequest {
  thread_id: string
  session_id: string
  approved: boolean
}

export interface ToolApprovalResponse {
  answer: string
  sources: SourceRef[]
  session_id: string
  status: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
}

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', req)
  return data
}

export async function approveToolCall(req: ToolApprovalRequest): Promise<ToolApprovalResponse> {
  const { data } = await api.post<ToolApprovalResponse>('/chat/tool-approval', req)
  return data
}
