import { useEffect, useState } from 'react'
import { fetchAuditLog, type AuditFilters, type AuditRecord } from '../api/audit'
import { getDocumentContent, type DocumentContent } from '../api/knowledge'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const KNOWLEDGE_ACTIONS = new Set(['knowledge.add', 'knowledge.delete'])

function isKnowledgeAction(action: string) {
  return KNOWLEDGE_ACTIONS.has(action)
}

function ActionBadge({ action }: { action: string }) {
  if (action === 'knowledge.add') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
        + knowledge.add
      </span>
    )
  }
  if (action === 'knowledge.delete') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300">
        − knowledge.delete
      </span>
    )
  }
  return <span className="font-mono text-gray-700 dark:text-slate-200 text-sm">{action}</span>
}

function StatusBadge({ status, changes }: { status: string; changes: Record<string, unknown> | null }) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
          status === 'approved'
            ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300'
            : status === 'completed'
            ? 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300'
            : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'
        }`}
      >
        {status === 'approved' ? '✓ approved' : status === 'completed' ? '✓ completed' : '✗ rejected'}
      </span>
      {changes && (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
          edited
        </span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Details cell for tool-call records
// ---------------------------------------------------------------------------

function ArgsDiff({
  aiArgs,
  userArgs,
}: {
  aiArgs: Record<string, unknown>
  userArgs: Record<string, unknown> | null
}) {
  const [expanded, setExpanded] = useState(false)

  if (!expanded) {
    return (
      <button onClick={() => setExpanded(true)} className="text-xs text-indigo-500 hover:underline">
        Show args
      </button>
    )
  }

  return (
    <div className="space-y-2 text-xs">
      <div>
        <span className="font-medium text-gray-500 dark:text-gray-400">AI suggested:</span>
        <pre className="mt-0.5 bg-gray-100 dark:bg-gray-700 rounded p-2 overflow-x-auto text-gray-700 dark:text-gray-200 font-mono">
          {JSON.stringify(aiArgs, null, 2)}
        </pre>
      </div>
      {userArgs && (
        <div>
          <span className="font-medium text-amber-600 dark:text-amber-400">User edited:</span>
          <pre className="mt-0.5 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded p-2 overflow-x-auto text-amber-800 dark:text-amber-200 font-mono">
            {JSON.stringify(userArgs, null, 2)}
          </pre>
        </div>
      )}
      <button onClick={() => setExpanded(false)} className="text-xs text-gray-400 hover:underline">
        Collapse
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Details cell for knowledge records
// ---------------------------------------------------------------------------

function KnowledgeDetails({ record }: { record: AuditRecord }) {
  const details = record.details as { doc_id?: string; title?: string; source_type?: string; chunk_count?: number }
  const [content, setContent] = useState<DocumentContent | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [expanded, setExpanded] = useState(false)

  function loadContent() {
    if (!details.doc_id || loading || content) return
    setLoading(true)
    getDocumentContent(details.doc_id)
      .then(setContent)
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  if (!expanded) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 dark:text-slate-400">
          {details.title} · {details.chunk_count} chunks
        </span>
        <button
          onClick={() => { setExpanded(true); loadContent() }}
          className="text-xs text-indigo-500 hover:underline"
        >
          Show content
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-2 text-xs">
      <div className="flex gap-3 text-gray-500 dark:text-slate-400">
        <span>doc_id: <span className="font-mono text-gray-700 dark:text-slate-200">{details.doc_id}</span></span>
        <span>type: <span className="font-medium text-gray-700 dark:text-slate-200">{details.source_type}</span></span>
        <span>chunks: <span className="font-medium text-gray-700 dark:text-slate-200">{details.chunk_count}</span></span>
      </div>
      {loading && <p className="text-gray-400 dark:text-slate-500">Loading content…</p>}
      {error && <p className="text-red-500">Content not available.</p>}
      {content && (
        <pre className="bg-gray-100 dark:bg-gray-700 rounded p-2 overflow-x-auto max-h-48 text-gray-700 dark:text-gray-200 font-mono whitespace-pre-wrap">
          {content.content}
        </pre>
      )}
      <button onClick={() => setExpanded(false)} className="text-xs text-gray-400 hover:underline">
        Collapse
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AuditPage() {
  const [records, setRecords] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState<AuditFilters>({ limit: 100 })
  const [usernameInput, setUsernameInput] = useState('')
  const [actionInput, setActionInput] = useState('')

  useEffect(() => {
    setLoading(true)
    fetchAuditLog(filters)
      .then((res) => setRecords(res.records))
      .catch(() => setRecords([]))
      .finally(() => setLoading(false))
  }, [filters])

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((prev) => ({ ...prev, username: usernameInput || undefined }))
    }, 400)
    return () => clearTimeout(timer)
  }, [usernameInput])

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((prev) => ({ ...prev, action: actionInput || undefined }))
    }, 400)
    return () => clearTimeout(timer)
  }, [actionInput])

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Audit Trail</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Riwayat semua aksi: tool call dan perubahan knowledge base.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700">
        <input
          type="text"
          placeholder="Filter username..."
          value={usernameInput}
          onChange={(e) => setUsernameInput(e.target.value)}
          className="text-sm px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
        />
        <input
          type="text"
          placeholder="Filter action (e.g. knowledge.add)..."
          value={actionInput}
          onChange={(e) => setActionInput(e.target.value)}
          className="text-sm px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400 min-w-56"
        />
        <input
          type="datetime-local"
          onChange={(e) => setFilters((prev) => ({ ...prev, date_from: e.target.value ? new Date(e.target.value).toISOString() : undefined }))}
          className="text-sm px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          title="From date"
        />
        <input
          type="datetime-local"
          onChange={(e) => setFilters((prev) => ({ ...prev, date_to: e.target.value ? new Date(e.target.value).toISOString() : undefined }))}
          className="text-sm px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          title="To date"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center text-gray-400 dark:text-slate-500 py-12 text-sm">Loading...</div>
      ) : records.length === 0 ? (
        <div className="text-center text-gray-400 dark:text-slate-500 py-12 text-sm">No audit records found.</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-slate-800 text-xs text-gray-500 dark:text-slate-400 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Timestamp</th>
                <th className="px-4 py-3 text-left">User</th>
                <th className="px-4 py-3 text-left">Action</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {records.map((r) => (
                <tr key={r.id} className="bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-700 dark:text-slate-200">{r.username}</td>
                  <td className="px-4 py-3">
                    <ActionBadge action={r.action} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={r.status} changes={r.changes} />
                  </td>
                  <td className="px-4 py-3">
                    {isKnowledgeAction(r.action) ? (
                      <KnowledgeDetails record={r} />
                    ) : (
                      <ArgsDiff aiArgs={r.details} userArgs={r.changes} />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
