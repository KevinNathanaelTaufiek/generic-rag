import type { DocumentInfo } from '../api/knowledge'
import { deleteDocument } from '../api/knowledge'

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

export default function KnowledgeList({ documents, loading, onDeleted }: Props) {
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
    return <p className="text-sm text-gray-400 py-4 text-center">Loading…</p>
  }

  if (!documents.length) {
    return (
      <p className="text-sm text-gray-400 py-8 text-center">
        No documents yet. Add some knowledge above.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Title</th>
            <th className="px-4 py-3">Chunks</th>
            <th className="px-4 py-3">Added</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {documents.map(doc => (
            <tr key={doc.doc_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-base">{sourceIcon[doc.source_type] ?? '📎'}</td>
              <td className="px-4 py-3 font-medium text-gray-800">{doc.title}</td>
              <td className="px-4 py-3 text-gray-500">{doc.chunk_count}</td>
              <td className="px-4 py-3 text-gray-400">{formatDate(doc.created_at)}</td>
              <td className="px-4 py-3 text-right">
                <button
                  className="text-xs text-red-500 hover:text-red-700 font-medium cursor-pointer"
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
  )
}
