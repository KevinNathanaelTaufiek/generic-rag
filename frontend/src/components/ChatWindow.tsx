import { useEffect, useRef } from 'react'
import type { ChatMessage, SourceRef } from '../api/chat'

export interface DisplayMessage extends ChatMessage {
  sources?: SourceRef[]
}

interface Props {
  messages: DisplayMessage[]
  loading: boolean
}

function SourcesBlock({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null
  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer text-indigo-500 hover:text-indigo-700 font-medium select-none">
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </summary>
      <ul className="mt-2 space-y-2">
        {sources.map(src => (
          <li key={src.doc_id} className="rounded-lg bg-indigo-50 px-3 py-2">
            <p className="font-semibold text-indigo-700">{src.title}</p>
            <p className="text-gray-500 mt-0.5 line-clamp-2">{src.excerpt}</p>
          </li>
        ))}
      </ul>
    </details>
  )
}

export default function ChatWindow({ messages, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!messages.length && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Ask a question based on your knowledge base.
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.content}</p>
            {msg.role === 'assistant' && msg.sources && (
              <SourcesBlock sources={msg.sources} />
            )}
          </div>
        </div>
      ))}
      {loading && (
        <div className="flex justify-start">
          <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-3 shadow-sm">
            <div className="flex gap-1 items-center h-4">
              <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
