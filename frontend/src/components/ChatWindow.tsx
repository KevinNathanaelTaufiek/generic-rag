import { useEffect, useRef } from 'react'
import type { ChatMessage, SourceRef, ToolCallInfo } from '../api/chat'

export interface DisplayMessage extends ChatMessage {
  sources?: SourceRef[]
  status?: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
}

interface Props {
  messages: DisplayMessage[]
  loading: boolean
  onApprove?: (threadId: string) => void
  onCancel?: (threadId: string) => void
}

function SourcesBlock({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null
  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer text-indigo-500 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium select-none">
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </summary>
      <ul className="mt-2 space-y-2">
        {sources.map(src => (
          <li key={src.doc_id} className="rounded-lg bg-indigo-50 dark:bg-indigo-900/40 px-3 py-2">
            <p className="font-semibold text-indigo-700 dark:text-indigo-300">{src.title}</p>
            <p className="text-gray-500 dark:text-slate-400 mt-0.5 line-clamp-2">{src.excerpt}</p>
          </li>
        ))}
      </ul>
    </details>
  )
}

function ToolApprovalCard({
  pending_tool,
  thread_id,
  onApprove,
  onCancel,
}: {
  pending_tool: ToolCallInfo
  thread_id: string
  onApprove: (id: string) => void
  onCancel: (id: string) => void
}) {
  return (
    <div className="rounded-xl border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm shadow-sm max-w-[75%]">
      <p className="font-semibold text-amber-800 dark:text-amber-300 mb-1">🔧 System wants to run a tool:</p>
      <p className="font-mono text-amber-900 dark:text-amber-200 text-xs mb-0.5">{pending_tool.tool_name}</p>
      <p className="text-amber-700 dark:text-amber-400 text-xs mb-3">→ {pending_tool.description}</p>
      <div className="flex gap-2">
        <button
          onClick={() => onApprove(thread_id)}
          className="px-3 py-1.5 rounded-lg bg-green-600 dark:bg-green-700 text-white text-xs font-medium hover:bg-green-700 dark:hover:bg-green-600 cursor-pointer transition-colors"
        >
          ✓ Approve
        </button>
        <button
          onClick={() => onCancel(thread_id)}
          className="px-3 py-1.5 rounded-lg bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-200 text-xs font-medium hover:bg-gray-300 dark:hover:bg-slate-500 cursor-pointer transition-colors"
        >
          ✗ Cancel
        </button>
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, loading, onApprove, onCancel }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!messages.length && !loading) {
    return (
      <div className="flex-1 overflow-y-auto flex items-center justify-center text-gray-400 dark:text-slate-500 text-sm">
        Ask a question based on your knowledge base.
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg, i) => {
        if (msg.role === 'assistant' && msg.status === 'pending_tool_approval' && msg.pending_tool && msg.thread_id) {
          return (
            <div key={i} className="flex justify-start">
              <ToolApprovalCard
                pending_tool={msg.pending_tool}
                thread_id={msg.thread_id}
                onApprove={onApprove ?? (() => {})}
                onCancel={onCancel ?? (() => {})}
              />
            </div>
          )
        }

        return (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 dark:bg-indigo-500 text-white rounded-br-sm'
                  : 'bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 text-gray-800 dark:text-slate-100 rounded-bl-sm shadow-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === 'assistant' && msg.sources && (
                <SourcesBlock sources={msg.sources} />
              )}
            </div>
          </div>
        )
      })}
      {loading && (
        <div className="flex justify-start">
          <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 px-4 py-3 shadow-sm">
            <div className="flex gap-1 items-center h-4">
              <span className="w-2 h-2 rounded-full bg-gray-300 dark:bg-slate-500 animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 rounded-full bg-gray-300 dark:bg-slate-500 animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 rounded-full bg-gray-300 dark:bg-slate-500 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
