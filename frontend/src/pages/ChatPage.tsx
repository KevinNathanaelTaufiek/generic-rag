import { useState, useEffect, useRef } from 'react'
import { sendMessage, approveToolCall, fetchTools } from '../api/chat'
import ChatWindow from '../components/ChatWindow'
import type { DisplayMessage, AgentStep } from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'
import { useChatStore, setAllTools } from '../store/chatStore'

// Fallback display names for static tools not coming from microservices.json
const STATIC_LABELS: Record<string, string> = {
  search_knowledge: 'Knowledge Base',
  search_web: 'Search Web',
}

function toLabel(name: string): string {
  return STATIC_LABELS[name] ?? name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function ChatPage() {
  const {
    messages, setMessages,
    sessionId, setSessionId,
    loading, setLoading,
    pendingApproval, setPendingApproval,
    strictMode, toggleStrictMode,
    enabledTools, toggleTool, toggleAllTools,
    resetChat,
    currentUsername, setMessagesForUser,
  } = useChatStore()

  const [toolInfos, setToolInfos] = useState<{ name: string; description: string }[]>([])
  const [showToolMenu, setShowToolMenu] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState<string>('')

  // Fetch tool list from backend on mount
  useEffect(() => {
    fetchTools().then((tools) => {
      setToolInfos(tools)
      setAllTools(tools.map(t => t.name))
    }).catch(() => {
      // backend unreachable — leave toolInfos empty, store keeps its defaults
    })
  }, [])
  const toolMenuRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  // mutable ref for in-flight progress steps — avoids stale closure issues
  const progressStepsRef = useRef<AgentStep[]>([])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (toolMenuRef.current && !toolMenuRef.current.contains(e.target as Node)) {
        setShowToolMenu(false)
      }
    }
    if (showToolMenu) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showToolMenu])

  async function handleSend(text: string) {
    const owner = currentUsername
    const userMsg: DisplayMessage = { role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessagesForUser(owner, prev => [...prev, userMsg])
    setLoading(true)
    setLoadingStatus('Thinking…')

    // Use a unique ID to reliably find/update the placeholder message across multiple setState calls
    const placeholderId = `ph-${Date.now()}`
    setMessagesForUser(owner, prev => [...prev, { role: 'assistant', content: '', status: 'done', steps: [], _id: placeholderId } as DisplayMessage & { _id: string }])
    progressStepsRef.current = []

    const controller = new AbortController()
    abortControllerRef.current = controller

    function updatePlaceholderSteps(steps: AgentStep[]) {
      setMessagesForUser(owner, prev => {
        const idx = prev.findLastIndex(m => (m as DisplayMessage & { _id?: string })._id === placeholderId)
        if (idx === -1) return prev
        const updated = [...prev]
        updated[idx] = { ...updated[idx], steps: [...steps] }
        return updated
      })
    }

    function replacePlaceholder(msg: DisplayMessage) {
      setMessagesForUser(owner, prev => {
        const idx = prev.findLastIndex(m => (m as DisplayMessage & { _id?: string })._id === placeholderId)
        if (idx === -1) return [...prev, msg]
        const updated = [...prev]
        updated[idx] = msg
        return updated
      })
    }

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
      }, controller.signal, (p) => {
        setLoadingStatus(p.label)
        const now = Date.now()
        const steps = progressStepsRef.current
        // Close previous active step with duration
        const lastIdx = steps.findLastIndex(s => s.status === 'progress' && s.durationMs === undefined)
        if (lastIdx !== -1) {
          steps[lastIdx] = {
            ...steps[lastIdx],
            durationMs: now - (steps[lastIdx].startedAt ?? now),
          }
        }
        // Push new active step
        const newStep: AgentStep = { status: 'progress', tool_name: '', label: p.label, startedAt: now }
        progressStepsRef.current = [...steps, newStep]
        updatePlaceholderSteps(progressStepsRef.current)
      })

      // Close last active step on completion
      const now = Date.now()
      const finalSteps = progressStepsRef.current.map(s =>
        s.status === 'progress' && s.durationMs === undefined
          ? { ...s, durationMs: now - (s.startedAt ?? now) }
          : s
      )

      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        const toolSteps: AgentStep[] = res.pending_tool
          ? [{ status: 'tool_requested', tool_name: res.pending_tool.tool_name, description: res.pending_tool.description }]
          : []
        replacePlaceholder({
          role: 'assistant',
          content: '',
          status: 'pending_tool_approval',
          pending_tool: res.pending_tool,
          thread_id: res.thread_id,
          steps: [...finalSteps, ...toolSteps],
        })
        setPendingApproval(true)
      } else {
        replacePlaceholder({
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          status: 'done',
          from_general_knowledge: res.from_general_knowledge,
          timestamp: new Date().toISOString(),
          steps: finalSteps,
        })
      }
    } catch (err) {
      if (err instanceof Error && (err.name === 'CanceledError' || err.name === 'AbortError')) {
        setMessagesForUser(owner, prev => prev.filter(m => (m as DisplayMessage & { _id?: string })._id !== placeholderId))
        return
      }
      replacePlaceholder({ role: 'assistant', content: 'Sorry, something went wrong. Please try again.' })
    } finally {
      setLoading(false)
      setLoadingStatus('')
      progressStepsRef.current = []
    }
  }

  async function handleApprove(threadId: string, modifiedArgs: Record<string, unknown>) {
    if (!sessionId) return
    const owner = currentUsername
    setPendingApproval(false)
    setLoading(true)

    let accumulatedSteps: AgentStep[] = []
    setMessagesForUser(owner, prev =>
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
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: true, modified_args: modifiedArgs })
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

        setMessagesForUser(owner, prev => {
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
        setMessagesForUser(owner, prev => {
          const idx = prev.findLastIndex(m => m.steps === accumulatedSteps)
          if (idx === -1) {
            return [...prev, { role: 'assistant' as const, content: res.answer, sources: res.sources, status: 'done' as const, steps: finalSteps, from_general_knowledge: res.from_general_knowledge, timestamp: new Date().toISOString() }]
          }
          const updated = [...prev]
          updated[idx] = { ...updated[idx], content: res.answer, sources: res.sources, status: 'done' as const, steps: finalSteps, from_general_knowledge: res.from_general_knowledge, timestamp: new Date().toISOString() }
          return updated
        })
      }
    } catch {
      setMessagesForUser(owner, prev => [
        ...prev,
        { role: 'assistant', content: 'Tool execution failed. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleCancel(threadId: string) {
    if (!sessionId) return
    const owner = currentUsername
    setPendingApproval(false)
    setLoading(true)

    let accumulatedSteps: AgentStep[] = []
    setMessagesForUser(owner, prev =>
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
      setMessagesForUser(owner, prev => {
        const idx = prev.findLastIndex(m => m.steps === accumulatedSteps)
        if (idx === -1) {
          return [...prev, { role: 'assistant' as const, content: res.answer, sources: res.sources, status: 'done' as const, steps: accumulatedSteps, from_general_knowledge: res.from_general_knowledge, timestamp: new Date().toISOString() }]
        }
        const updated = [...prev]
        updated[idx] = { ...updated[idx], content: res.answer, sources: res.sources, status: 'done' as const, from_general_knowledge: res.from_general_knowledge, timestamp: new Date().toISOString() }
        return updated
      })
    } catch {
      setMessagesForUser(owner, prev => [
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
    resetChat()
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
                  : enabledTools.length < toolInfos.length
                  ? 'bg-amber-50 dark:bg-amber-900/30 border-amber-300 dark:border-amber-600 text-amber-700 dark:text-amber-400'
                  : 'bg-gray-50 dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400'
              }`}
              onClick={() => setShowToolMenu(prev => !prev)}
              title="Toggle active tools"
            >
              Tools {enabledTools.length}/{toolInfos.length}
            </button>
            {showToolMenu && (
              <div className="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg z-10 min-w-44">
                <div className="px-3 py-2 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide">Active Tools</span>
                  <button
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                    onClick={toggleAllTools}
                    disabled={strictMode}
                  >
                    {enabledTools.length === toolInfos.length ? 'Disable all' : 'Enable all'}
                  </button>
                </div>
                {toolInfos.map(({ name, description }) => {
                  const locked = strictMode && name === 'search_knowledge'
                  const disabledByStrict = strictMode && name !== 'search_knowledge'
                  return (
                    <label
                      key={name}
                      className={`flex items-center gap-2 px-3 py-2 ${disabledByStrict || locked ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50 dark:hover:bg-slate-700 cursor-pointer'}`}
                      title={disabledByStrict ? 'Nonaktifkan strict mode untuk mengaktifkan tool ini.' : locked ? 'Terkunci saat strict mode aktif.' : description}
                    >
                      <input
                        type="checkbox"
                        checked={enabledTools.includes(name)}
                        onChange={() => toggleTool(name)}
                        disabled={strictMode}
                        className="accent-indigo-600"
                      />
                      <span className="text-sm text-gray-700 dark:text-slate-300">{toLabel(name)}</span>
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
          loadingStatus={loadingStatus}
          onApprove={handleApprove}
          onCancel={handleCancel}
        />
        <ChatInput onSend={handleSend} disabled={inputDisabled} />
      </div>
    </div>
  )
}
