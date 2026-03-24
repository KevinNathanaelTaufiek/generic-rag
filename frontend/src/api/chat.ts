import api from './client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SourceRef {
  doc_id: string
  title: string
  excerpt: string
  url?: string
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
  enabled_tools?: string[]
}

export interface ChatResponse {
  answer: string
  sources: SourceRef[]
  session_id: string
  status: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
  from_general_knowledge?: boolean
}

export interface ProgressEvent {
  event: 'thinking' | 'searching' | 'tool_executing' | 'generating'
  label: string
}

export interface ToolApprovalRequest {
  thread_id: string
  session_id: string
  approved: boolean
  modified_args?: Record<string, unknown>
}

export interface ToolApprovalResponse {
  answer: string
  sources: SourceRef[]
  session_id: string
  status: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
  from_general_knowledge?: boolean
}

const BASE_URL = 'http://localhost:8000/api/v1'

export async function sendMessage(
  req: ChatRequest,
  signal?: AbortSignal,
  onProgress?: (p: ProgressEvent) => void,
): Promise<ChatResponse> {
  const username = localStorage.getItem('rag_username') ?? 'anonymous'

  const response = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Username': username,
    },
    body: JSON.stringify(req),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Parse SSE frames from buffer
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''  // last chunk may be incomplete

    for (const frame of frames) {
      if (!frame.trim()) continue

      let eventType = 'message'
      let dataLine = ''

      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLine = line.slice(6)
      }

      if (!dataLine) continue

      try {
        const parsed = JSON.parse(dataLine)
        if (eventType === 'progress' && onProgress) {
          onProgress(parsed as ProgressEvent)
        } else if (eventType === 'done') {
          return parsed as ChatResponse
        }
      } catch {
        // skip malformed frames
      }
    }
  }

  throw new Error('SSE stream ended without a done event')
}

export async function approveToolCall(req: ToolApprovalRequest): Promise<ToolApprovalResponse> {
  const { data } = await api.post<ToolApprovalResponse>('/chat/tool-approval', req)
  return data
}

export interface ToolInfo {
  name: string
  description: string
}

export async function fetchTools(): Promise<ToolInfo[]> {
  const { data } = await api.get<{ tools: ToolInfo[] }>('/chat/tools')
  return data.tools
}
