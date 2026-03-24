import { useEffect, useState } from 'react'
import { fetchAuditLog, type AuditFilters, type AuditRecord } from '../api/audit'

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
      <button
        onClick={() => setExpanded(true)}
        className="text-xs text-indigo-500 hover:underline"
      >
        Show args
      </button>
    )
  }

  const hasEdits = userArgs !== null

  return (
    <div className="space-y-2 text-xs">
      <div>
        <span className="font-medium text-gray-500 dark:text-gray-400">AI suggested:</span>
        <pre className="mt-0.5 bg-gray-100 dark:bg-gray-700 rounded p-2 overflow-x-auto text-gray-700 dark:text-gray-200 font-mono">
          {JSON.stringify(aiArgs, null, 2)}
        </pre>
      </div>
      {hasEdits && (
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

export default function AuditPage() {
  const [records, setRecords] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState<AuditFilters>({ limit: 100 })
  const [usernameInput, setUsernameInput] = useState('')
  const [toolNameInput, setToolNameInput] = useState('')

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
      setFilters((prev) => ({ ...prev, tool_name: toolNameInput || undefined }))
    }, 400)
    return () => clearTimeout(timer)
  }, [toolNameInput])

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Audit Trail</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Riwayat tool call yang diapprove atau direject per user.
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
          placeholder="Filter tool name..."
          value={toolNameInput}
          onChange={(e) => setToolNameInput(e.target.value)}
          className="text-sm px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
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
                <th className="px-4 py-3 text-left">Tool</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Args</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
              {records.map((r) => (
                <tr key={r.id} className="bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                  <td className="px-4 py-3 text-xs text-gray-500 dark:text-slate-400 whitespace-nowrap">
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-700 dark:text-slate-200">{r.username}</td>
                  <td className="px-4 py-3 font-mono text-gray-700 dark:text-slate-200">{r.tool_name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        r.result_status === 'approved'
                          ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300'
                          : 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'
                      }`}
                    >
                      {r.result_status === 'approved' ? '✓ approved' : '✗ rejected'}
                    </span>
                    {r.user_edited_args && (
                      <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                        edited
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <ArgsDiff aiArgs={r.ai_suggested_args} userArgs={r.user_edited_args} />
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
