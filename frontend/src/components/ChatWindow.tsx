import { useEffect, useRef, useState } from 'react'
import type { ChatMessage, SourceRef, ToolCallInfo } from '../api/chat'

export type StepStatus =
  | 'tool_requested' | 'tool_approved' | 'tool_cancelled' | 'tool_executing' | 'tool_done'
  | 'progress'

export interface AgentStep {
  status: StepStatus
  tool_name: string
  description?: string
  round?: number
  // progress-specific fields
  label?: string
  durationMs?: number
  startedAt?: number  // Date.now() when step started
}

export interface DisplayMessage extends ChatMessage {
  sources?: SourceRef[]
  status?: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
  steps?: AgentStep[]
  timestamp?: string
  from_general_knowledge?: boolean
}

interface Props {
  messages: DisplayMessage[]
  loading: boolean
  loadingStatus?: string
  onApprove?: (threadId: string, modifiedArgs: Record<string, unknown>) => void
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
            {src.url ? (
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-indigo-700 dark:text-indigo-300 hover:underline"
              >
                {src.title} ↗
              </a>
            ) : (
              <p className="font-semibold text-indigo-700 dark:text-indigo-300">{src.title}</p>
            )}
            <p className="text-gray-500 dark:text-slate-400 mt-0.5 line-clamp-2">{src.excerpt}</p>
          </li>
        ))}
      </ul>
    </details>
  )
}

const TOOL_STEP_CONFIG: Record<Exclude<StepStatus, 'progress'>, { icon: string; label: string; color: string }> = {
  tool_requested: { icon: '🤔', label: 'LLM meminta tool', color: 'text-amber-600 dark:text-amber-400' },
  tool_approved:  { icon: '✓',  label: 'Disetujui',        color: 'text-green-600 dark:text-green-400' },
  tool_cancelled: { icon: '✗',  label: 'Dibatalkan',       color: 'text-red-500 dark:text-red-400' },
  tool_executing: { icon: '⏳', label: 'Menjalankan tool', color: 'text-blue-500 dark:text-blue-400' },
  tool_done:      { icon: '✔',  label: 'Tool selesai',     color: 'text-gray-500 dark:text-slate-400' },
}

const PROGRESS_ICONS: Record<string, string> = {
  'Thinking…': '💭',
  'Searching knowledge base…': '🔍',
  'Searching the web…': '🌐',
  'Generating response…': '✍️',
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function AgentStepsLog({ steps }: { steps: AgentStep[] }) {
  const progressSteps = steps.filter(s => s.status === 'progress')
  const toolSteps = steps.filter(s => s.status !== 'progress')

  if (!steps.length) return null

  const hasActiveStep = progressSteps.some(s => s.durationMs === undefined)

  return (
    <details className="mb-3" open={hasActiveStep}>
      <summary className="cursor-pointer text-xs text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 select-none font-medium">
        {steps.length} step{steps.length > 1 ? 's' : ''}
      </summary>
      <ol className="mt-2 space-y-1.5 border-l-2 border-gray-100 dark:border-slate-600 pl-3">
        {progressSteps.map((step, i) => {
          const icon = PROGRESS_ICONS[step.label ?? ''] ?? '●'
          const isActive = step.durationMs === undefined
          const time = step.durationMs !== undefined ? formatDuration(step.durationMs) : null
          return (
            <li key={`p-${i}`} className="text-xs flex items-center gap-1.5">
              {isActive ? (
                <span className="inline-block w-3 h-3 border-2 border-gray-300 dark:border-slate-500 border-t-indigo-500 dark:border-t-indigo-400 rounded-full animate-spin flex-shrink-0" />
              ) : (
                <span className="text-base leading-none">{icon}</span>
              )}
              <span className={isActive ? 'text-indigo-500 dark:text-indigo-400 animate-pulse' : 'text-gray-600 dark:text-slate-300'}>
                {step.label}
              </span>
              {time && (
                <span className="text-gray-400 dark:text-slate-500 ml-auto pl-2">· {time}</span>
              )}
            </li>
          )
        })}
        {toolSteps.map((step, i) => {
          const cfg = TOOL_STEP_CONFIG[step.status as Exclude<StepStatus, 'progress'>]
          return (
            <li key={`t-${i}`} className="text-xs">
              <span className={`font-medium ${cfg.color}`}>
                {cfg.icon} {cfg.label}
              </span>
              <span className="text-gray-400 dark:text-slate-500 ml-1">
                — <code className="font-mono">{step.tool_name}</code>
                {step.description && <span className="italic"> ({step.description})</span>}
              </span>
            </li>
          )
        })}
      </ol>
    </details>
  )
}

function ArgEditor({
  name,
  value,
  onChange,
}: {
  name: string
  value: unknown
  onChange: (v: unknown) => void
}) {
  const inputClass =
    'w-full text-xs px-2 py-1 border border-amber-300 dark:border-amber-600 rounded bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-amber-400'

  if (typeof value === 'boolean') {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={value}
          onChange={(e) => onChange(e.target.checked)}
          className="accent-amber-500"
        />
        <span className="text-xs text-gray-600 dark:text-gray-300">{name}</span>
      </label>
    )
  }

  if (typeof value === 'number') {
    return (
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={inputClass}
        aria-label={name}
      />
    )
  }

  if (typeof value === 'object' || Array.isArray(value)) {
    return (
      <textarea
        rows={3}
        defaultValue={JSON.stringify(value, null, 2)}
        onChange={(e) => {
          try {
            onChange(JSON.parse(e.target.value))
          } catch {
            // keep raw string so validation on submit catches it
            onChange(e.target.value)
          }
        }}
        className={`${inputClass} font-mono resize-y`}
        aria-label={name}
      />
    )
  }

  return (
    <input
      type="text"
      value={String(value)}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
      aria-label={name}
    />
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
  onApprove: (id: string, modifiedArgs: Record<string, unknown>) => void
  onCancel: (id: string) => void
}) {
  const [editedArgs, setEditedArgs] = useState<Record<string, unknown>>(() => ({ ...pending_tool.tool_args }))
  const [jsonError, setJsonError] = useState<string | null>(null)

  function handleArgChange(key: string, val: unknown) {
    setEditedArgs((prev) => ({ ...prev, [key]: val }))
    setJsonError(null)
  }

  function handleApprove() {
    // Validate any string values that should be JSON (e.g. object fields)
    for (const [key, val] of Object.entries(editedArgs)) {
      if (typeof val === 'string' && typeof pending_tool.tool_args[key] === 'object') {
        try {
          JSON.parse(val)
        } catch {
          setJsonError(`"${key}" contains invalid JSON`)
          return
        }
      }
    }
    onApprove(thread_id, editedArgs)
  }

  const argEntries = Object.entries(pending_tool.tool_args)

  return (
    <div className="rounded-xl border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm shadow-sm max-w-[75%]">
      <p className="font-semibold text-amber-800 dark:text-amber-300 mb-1">🔧 System wants to run a tool:</p>
      <p className="font-mono text-amber-900 dark:text-amber-200 text-xs mb-0.5">{pending_tool.tool_name}</p>
      <p className="text-amber-700 dark:text-amber-400 text-xs mb-3">→ {pending_tool.description}</p>

      {argEntries.length > 0 && (
        <div className="mb-3 space-y-2">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400">Parameters (editable):</p>
          {argEntries.map(([key]) => (
            <div key={key}>
              <label className="block text-xs text-amber-600 dark:text-amber-500 mb-0.5 font-mono">{key}</label>
              <ArgEditor
                name={key}
                value={editedArgs[key]}
                onChange={(v) => handleArgChange(key, v)}
              />
            </div>
          ))}
          {jsonError && (
            <p className="text-xs text-red-600 dark:text-red-400">{jsonError}</p>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleApprove}
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

export default function ChatWindow({ messages, loading, loadingStatus, onApprove, onCancel }: Props) {
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
            <div key={i} className="flex justify-start flex-col gap-1">
              {msg.steps && msg.steps.length > 0 && (
                <div className="max-w-[75%]">
                  <AgentStepsLog steps={msg.steps} />
                </div>
              )}
              <ToolApprovalCard
                pending_tool={msg.pending_tool}
                thread_id={msg.thread_id}
                onApprove={onApprove ?? (() => {})}
                onCancel={onCancel ?? (() => {})}
              />

            </div>
          )
        }

        // Skip empty placeholder messages (no content and no steps yet)
        if (msg.role === 'assistant' && !msg.content && (!msg.steps || msg.steps.length === 0)) {
          return null
        }

        const actor = msg.role === 'user' ? 'You' : 'Assistant'
        const timeLabel = msg.timestamp
          ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : null

        return (
          <div
            key={i}
            className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <span className="text-xs text-gray-400 dark:text-slate-500 px-1">
              {actor}{timeLabel && ` · ${timeLabel}`}
            </span>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 dark:bg-indigo-500 text-white rounded-br-sm'
                  : 'bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 text-gray-800 dark:text-slate-100 rounded-bl-sm shadow-sm'
              }`}
            >
              {msg.role === 'assistant' && msg.steps && msg.steps.length > 0 && (
                <AgentStepsLog steps={msg.steps} />
              )}
              {msg.content && <p className="whitespace-pre-wrap">{msg.content}</p>}
              {msg.role === 'assistant' && msg.from_general_knowledge && (
                <p className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                  <span>⚠</span> Jawaban dari general knowledge LLM, bukan dari knowledge base.
                </p>
              )}
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
            <div className="flex items-center gap-2">
              <span className="inline-block w-3.5 h-3.5 border-2 border-gray-300 dark:border-slate-500 border-t-indigo-500 dark:border-t-indigo-400 rounded-full animate-spin flex-shrink-0" />
              <span className="text-sm text-gray-400 dark:text-slate-400 animate-pulse">
                {loadingStatus || 'Thinking…'}
              </span>
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
