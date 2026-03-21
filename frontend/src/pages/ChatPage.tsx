import { useState, useEffect, useRef } from 'react'
import { sendMessage, approveToolCall } from '../api/chat'
import ChatWindow from '../components/ChatWindow'
import type { DisplayMessage, AgentStep } from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'

const ALL_TOOLS = ['search_knowledge', 'search_web', 'send_notification', 'get_random_number', 'crud_data']

const TOOL_LABELS: Record<string, string> = {
  search_knowledge: 'Knowledge Base',
  search_web: 'Search Web',
  send_notification: 'Send Notification',
  get_random_number: 'Random Number',
  crud_data: 'CRUD Data',
}

const TOOL_DESCRIPTIONS: Record<string, string> = {
  search_knowledge: 'Cari jawaban dari dokumen yang sudah ditambahkan ke knowledge base.',
  search_web: 'Cari informasi dari internet jika tidak ada di knowledge base.',
  send_notification: 'Kirim notifikasi atau pesan ke penerima.',
  get_random_number: 'Generate angka acak dalam rentang tertentu.',
  crud_data: 'Buat, baca, update, atau hapus data di sistem eksternal.',
}

interface Props {
  messages: DisplayMessage[]
  setMessages: React.Dispatch<React.SetStateAction<DisplayMessage[]>>
  sessionId: string | undefined
  setSessionId: React.Dispatch<React.SetStateAction<string | undefined>>
}

export default function ChatPage({ messages, setMessages, sessionId, setSessionId }: Props) {
  const [loading, setLoading] = useState(false)
  const [strictMode, setStrictMode] = useState(false)
  const [pendingApproval, setPendingApproval] = useState(false)
  const [enabledTools, setEnabledTools] = useState<string[]>(['search_knowledge'])
  const [toolsBeforeStrict, setToolsBeforeStrict] = useState<string[]>(['search_knowledge'])
  const [showToolMenu, setShowToolMenu] = useState(false)
  const toolMenuRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (toolMenuRef.current && !toolMenuRef.current.contains(e.target as Node)) {
        setShowToolMenu(false)
      }
    }
    if (showToolMenu) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showToolMenu])

  function toggleStrictMode() {
    if (!strictMode) {
      setToolsBeforeStrict(enabledTools)
      setEnabledTools(['search_knowledge'])
    } else {
      setEnabledTools(toolsBeforeStrict)
    }
    setStrictMode(prev => !prev)
  }

  function toggleTool(name: string) {
    setEnabledTools(prev =>
      prev.includes(name) ? prev.filter(t => t !== name) : [...prev, name]
    )
  }

  async function handleSend(text: string) {
    const userMsg: DisplayMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const history = messages
        .filter(m => m.status !== 'pending_tool_approval')
        .map(m => ({ role: m.role, content: m.content }))

      const res = await sendMessage({
        message: text,
        session_id: sessionId,
        history,
        strict_mode: strictMode,
        enabled_tools: enabledTools,
      }, controller.signal)
      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        const steps: AgentStep[] = res.pending_tool
          ? [{ status: 'tool_requested', tool_name: res.pending_tool.tool_name, description: res.pending_tool.description }]
          : []
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            status: 'pending_tool_approval',
            pending_tool: res.pending_tool,
            thread_id: res.thread_id,
            steps,
          },
        ])
        setPendingApproval(true)
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
        ])
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'CanceledError') return
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

    // Capture current steps and approved tool name before mutating
    let accumulatedSteps: AgentStep[] = []
    setMessages(prev =>
      prev.map(m => {
        if (m.thread_id !== threadId) return m
        const approvedStep: AgentStep = {
          status: 'tool_approved',
          tool_name: m.pending_tool?.tool_name ?? '',
        }
        const executingStep: AgentStep = {
          status: 'tool_executing',
          tool_name: m.pending_tool?.tool_name ?? '',
        }
        accumulatedSteps = [...(m.steps ?? []), approvedStep, executingStep]
        return { ...m, content: '', status: 'done' as const, pending_tool: undefined, steps: accumulatedSteps }
      })
    )

    try {
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: true })
      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        const doneStep: AgentStep = {
          status: 'tool_done',
          tool_name: accumulatedSteps.find(s => s.status === 'tool_executing')?.tool_name ?? '',
        }
        const nextRequestedStep: AgentStep = res.pending_tool
          ? { status: 'tool_requested', tool_name: res.pending_tool.tool_name, description: res.pending_tool.description }
          : { status: 'tool_requested', tool_name: '' }
        const nextSteps = [...accumulatedSteps, doneStep, nextRequestedStep]

        // Replace the executing message with next approval card (merge steps)
        setMessages(prev => {
          const idx = prev.findLastIndex(m => m.steps === accumulatedSteps)
          if (idx === -1) {
            return [
              ...prev,
              {
                role: 'assistant' as const,
                content: '',
                status: 'pending_tool_approval' as const,
                pending_tool: res.pending_tool,
                thread_id: res.thread_id,
                steps: nextSteps,
              },
            ]
          }
          const updated = [...prev]
          updated[idx] = {
            ...updated[idx],
            status: 'pending_tool_approval' as const,
            pending_tool: res.pending_tool,
            thread_id: res.thread_id,
            steps: nextSteps,
          }
          return updated
        })
        setPendingApproval(true)
      } else {
        const doneStep: AgentStep = {
          status: 'tool_done',
          tool_name: accumulatedSteps.find(s => s.status === 'tool_executing')?.tool_name ?? '',
        }
        const finalSteps = [...accumulatedSteps, doneStep]
        // Replace executing placeholder with final answer (keep steps)
        setMessages(prev => {
          const idx = prev.findLastIndex(m => m.steps === accumulatedSteps)
          if (idx === -1) {
            return [...prev, { role: 'assistant' as const, content: res.answer, sources: res.sources, status: 'done' as const, steps: finalSteps }]
          }
          const updated = [...prev]
          updated[idx] = { ...updated[idx], content: res.answer, sources: res.sources, status: 'done' as const, steps: finalSteps }
          return updated
        })
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

    let accumulatedSteps: AgentStep[] = []
    setMessages(prev =>
      prev.map(m => {
        if (m.thread_id !== threadId) return m
        const cancelledStep: AgentStep = { status: 'tool_cancelled', tool_name: m.pending_tool?.tool_name ?? '' }
        accumulatedSteps = [...(m.steps ?? []), cancelledStep]
        return { ...m, content: '', status: 'done' as const, pending_tool: undefined, steps: accumulatedSteps }
      })
    )

    try {
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: false })
      setSessionId(res.session_id)
      setMessages(prev => {
        const idx = prev.findLastIndex(m => m.steps === accumulatedSteps)
        if (idx === -1) {
          return [...prev, { role: 'assistant' as const, content: res.answer, sources: res.sources, status: 'done' as const, steps: accumulatedSteps }]
        }
        const updated = [...prev]
        updated[idx] = { ...updated[idx], content: res.answer, sources: res.sources, status: 'done' as const }
        return updated
      })
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong after cancellation. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleResetChat() {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setMessages([])
    setSessionId(undefined)
    setPendingApproval(false)
    setLoading(false)
  }

  const inputDisabled = loading || pendingApproval

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col overflow-hidden" style={{ height: 'calc(100vh - 10vh)' }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Chat</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400">Ask questions based on your knowledge base.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`flex items-center gap-2 text-sm border rounded-lg px-3 py-1.5 cursor-pointer transition-colors ${
              strictMode
                ? 'bg-indigo-50 dark:bg-indigo-900/40 border-indigo-300 dark:border-indigo-600 text-indigo-700 dark:text-indigo-300'
                : 'bg-gray-50 dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-500 dark:text-slate-400'
            }`}
            onClick={toggleStrictMode}
            title={strictMode
              ? 'Strict mode ON: hanya menjawab dari knowledge base. Klik untuk menonaktifkan.'
              : 'Strict mode OFF: LLM boleh menggunakan general knowledge. Klik untuk mengaktifkan dan membatasi jawaban hanya dari knowledge base.'}
          >
            {strictMode ? '🔒 Strict' : '🔓 Flexible'}
          </button>
          <div className="relative" ref={toolMenuRef}>
            <button
              className={`flex items-center gap-2 text-sm border rounded-lg px-3 py-1.5 cursor-pointer transition-colors ${
                enabledTools.length === 0
                  ? 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-700 text-red-500 dark:text-red-400'
                  : enabledTools.length < ALL_TOOLS.length
                  ? 'bg-amber-50 dark:bg-amber-900/30 border-amber-300 dark:border-amber-600 text-amber-700 dark:text-amber-400'
                  : 'bg-gray-50 dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400'
              }`}
              onClick={() => setShowToolMenu(prev => !prev)}
              title="Toggle active tools"
            >
              Tools {enabledTools.length}/{ALL_TOOLS.length}
            </button>
            {showToolMenu && (
              <div className="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg z-10 min-w-44">
                <div className="px-3 py-2 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Active Tools</span>
                  <button
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                    onClick={() => setEnabledTools(enabledTools.length === ALL_TOOLS.length ? [] : [...ALL_TOOLS])}
                    disabled={strictMode}
                  >
                    {enabledTools.length === ALL_TOOLS.length ? 'Disable all' : 'Enable all'}
                  </button>
                </div>
                {ALL_TOOLS.map(name => {
                  const locked = strictMode && name === 'search_knowledge'
                  const disabledByStrict = strictMode && name !== 'search_knowledge'
                  return (
                    <label
                      key={name}
                      className={`flex items-center gap-2 px-3 py-2 ${disabledByStrict || locked ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50 dark:hover:bg-slate-700 cursor-pointer'}`}
                      title={disabledByStrict ? 'Nonaktifkan strict mode untuk mengaktifkan tool ini.' : locked ? 'Terkunci saat strict mode aktif.' : TOOL_DESCRIPTIONS[name]}
                    >
                      <input
                        type="checkbox"
                        checked={enabledTools.includes(name)}
                        onChange={() => toggleTool(name)}
                        disabled={strictMode}
                        className="accent-indigo-600"
                      />
                      <span className="text-sm text-gray-700 dark:text-slate-300">{TOOL_LABELS[name]}</span>
                    </label>
                  )
                })}
              </div>
            )}
          </div>
          {messages.length > 0 && (
            <button
              className="text-sm text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 border border-gray-200 dark:border-slate-600 rounded-lg px-3 py-1.5 cursor-pointer"
              onClick={handleResetChat}
            >
              Reset Chat
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col flex-1 rounded-2xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50 overflow-hidden shadow-sm">
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
