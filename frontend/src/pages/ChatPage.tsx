import { useState } from 'react'
import { sendMessage, approveToolCall } from '../api/chat'
import ChatWindow from '../components/ChatWindow'
import type { DisplayMessage } from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'

export default function ChatPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [strictMode, setStrictMode] = useState(true)
  const [pendingApproval, setPendingApproval] = useState(false)

  async function handleSend(text: string) {
    const userMsg: DisplayMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const history = messages
        .filter(m => m.status !== 'pending_tool_approval')
        .map(m => ({ role: m.role, content: m.content }))

      const res = await sendMessage({
        message: text,
        session_id: sessionId,
        history,
        strict_mode: strictMode,
      })
      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            status: 'pending_tool_approval',
            pending_tool: res.pending_tool,
            thread_id: res.thread_id,
          },
        ])
        setPendingApproval(true)
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
        ])
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleApprove(threadId: string) {
    if (!sessionId) return
    setPendingApproval(false)
    setLoading(true)

    setMessages(prev =>
      prev.map(m =>
        m.thread_id === threadId
          ? { ...m, content: '⏳ Executing tool...', status: 'done' as const, pending_tool: undefined }
          : m
      )
    )

    try {
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: true })
      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            status: 'pending_tool_approval',
            pending_tool: res.pending_tool,
            thread_id: res.thread_id,
          },
        ])
        setPendingApproval(true)
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
        ])
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Tool execution failed. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleCancel(threadId: string) {
    if (!sessionId) return
    setPendingApproval(false)
    setLoading(true)

    setMessages(prev =>
      prev.map(m =>
        m.thread_id === threadId
          ? { ...m, content: '✗ Tool execution cancelled.', status: 'done' as const, pending_tool: undefined }
          : m
      )
    )

    try {
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: false })
      setSessionId(res.session_id)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong after cancellation. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleNewChat() {
    setMessages([])
    setSessionId(undefined)
    setPendingApproval(false)
  }

  const inputDisabled = loading || pendingApproval

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col h-screen">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chat</h1>
          <p className="text-sm text-gray-500">Ask questions based on your knowledge base.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`flex items-center gap-2 text-sm border rounded-lg px-3 py-1.5 cursor-pointer transition-colors ${
              strictMode
                ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                : 'bg-gray-50 border-gray-200 text-gray-500'
            }`}
            onClick={() => setStrictMode(prev => !prev)}
            title={strictMode ? 'Strict: hanya jawab dari knowledge base' : 'Bebas: boleh jawab dari general knowledge'}
          >
            {strictMode ? '🔒 Strict' : '💬 Bebas'}
          </button>
          {messages.length > 0 && (
            <button
              className="text-sm text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 cursor-pointer"
              onClick={handleNewChat}
            >
              New chat
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col flex-1 rounded-2xl border border-gray-200 bg-gray-50 overflow-hidden shadow-sm">
        <ChatWindow
          messages={messages}
          loading={loading}
          onApprove={handleApprove}
          onCancel={handleCancel}
        />
        <ChatInput onSend={handleSend} disabled={inputDisabled} />
      </div>
    </div>
  )
}
