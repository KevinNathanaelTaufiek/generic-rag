import { useState } from 'react'
import type { DocumentContent, DocumentInfo } from '../api/knowledge'
import { deleteDocument, getDocumentContent } from '../api/knowledge'

interface Props {
  documents: DocumentInfo[]
  loading: boolean
  onDeleted: (docId: string) => void
}

const sourceIcon: Record<string, string> = {
  text: '📝',
  pdf: '📄',
  file: '📂',
}

function formatDate(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function DocumentDetailModal({
  doc,
  onClose,
}: {
  doc: DocumentInfo
  onClose: () => void
}) {
  const [content, setContent] = useState<DocumentContent | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [loaded, setLoaded] = useState(false)

  function loadContent() {
    if (loaded) return
    setLoading(true)
    getDocumentContent(doc.doc_id)
      .then((data) => {
        setContent(data)
        setLoaded(true)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">{doc.title}</h2>
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 font-mono">{doc.doc_id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 text-xl leading-none ml-4"
          >
            ✕
          </button>
        </div>

        {/* Metadata */}
        <div className="px-6 py-3 flex gap-4 text-sm border-b border-gray-100 dark:border-slate-700 bg-gray-50 dark:bg-slate-700/40">
          <span className="text-gray-500 dark:text-slate-400">
            Type: <span className="font-medium text-gray-700 dark:text-slate-200">{sourceIcon[doc.source_type] ?? '📎'} {doc.source_type}</span>
          </span>
          <span className="text-gray-500 dark:text-slate-400">
            Chunks: <span className="font-medium text-gray-700 dark:text-slate-200">{doc.chunk_count}</span>
          </span>
          <span className="text-gray-500 dark:text-slate-400">
            Added: <span className="font-medium text-gray-700 dark:text-slate-200">{formatDate(doc.created_at)}</span>
          </span>
        </div>

        {/* Content section */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {!loaded && !loading && !error && (
            <div className="flex flex-col items-center justify-center py-8 gap-3">
              <p className="text-sm text-gray-400 dark:text-slate-500">Content not loaded yet.</p>
              <button
                onClick={loadContent}
                className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
              >
                Load Content
              </button>
            </div>
          )}
          {loading && (
            <p className="text-sm text-gray-400 dark:text-slate-500 text-center py-8">Loading content…</p>
          )}
          {error && (
            <p className="text-sm text-red-500 text-center py-8">Failed to load content.</p>
          )}
          {content && (
            <pre className="text-sm text-gray-700 dark:text-slate-200 whitespace-pre-wrap font-mono leading-relaxed">
              {content.content}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default function KnowledgeList({ documents, loading, onDeleted }: Props) {
  const [detailDoc, setDetailDoc] = useState<DocumentInfo | null>(null)

  async function handleDelete(docId: string) {
    if (!confirm('Delete this document from the knowledge base?')) return
    try {
      await deleteDocument(docId)
      onDeleted(docId)
    } catch {
      alert('Failed to delete document.')
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-400 dark:text-slate-500 py-4 text-center">Loading…</p>
  }

  if (!documents.length) {
    return (
      <p className="text-sm text-gray-400 dark:text-slate-500 py-8 text-center">
        No documents yet. Add some knowledge above.
      </p>
    )
  }

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-slate-700/50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Chunks</th>
              <th className="px-4 py-3">Added</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            {documents.map(doc => (
              <tr key={doc.doc_id} className="hover:bg-gray-50 dark:hover:bg-slate-700/40">
                <td className="px-4 py-3 text-base">{sourceIcon[doc.source_type] ?? '📎'}</td>
                <td className="px-4 py-3 font-medium text-gray-800 dark:text-slate-200">{doc.title}</td>
                <td className="px-4 py-3 text-gray-500 dark:text-slate-400">{doc.chunk_count}</td>
                <td className="px-4 py-3 text-gray-400 dark:text-slate-500">{formatDate(doc.created_at)}</td>
                <td className="px-4 py-3 text-right flex items-center justify-end gap-3">
                  <button
                    className="text-xs text-indigo-500 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer"
                    onClick={() => setDetailDoc(doc)}
                  >
                    Detail
                  </button>
                  <button
                    className="text-xs text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium cursor-pointer"
                    onClick={() => handleDelete(doc.doc_id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailDoc && (
        <DocumentDetailModal doc={detailDoc} onClose={() => setDetailDoc(null)} />
      )}
    </>
  )
}
