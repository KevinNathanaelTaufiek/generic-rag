import { useEffect, useState } from 'react'
import type { DocumentInfo } from '../api/knowledge'
import { listDocuments } from '../api/knowledge'
import KnowledgeUpload from '../components/KnowledgeUpload'
import KnowledgeList from '../components/KnowledgeList'

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listDocuments()
      .then(res => setDocuments(res.documents))
      .finally(() => setLoading(false))
  }, [])

  function handleAdded(doc: DocumentInfo) {
    setDocuments(prev => [doc, ...prev])
  }

  function handleDeleted(docId: string) {
    setDocuments(prev => prev.filter(d => d.doc_id !== docId))
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
        <p className="text-sm text-gray-500 mt-1">
          Add documents and text that the AI will use to answer your questions.
        </p>
      </div>

      <KnowledgeUpload onAdded={handleAdded} />

      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">
          Documents ({documents.length})
        </h2>
        <KnowledgeList
          documents={documents}
          loading={loading}
          onDeleted={handleDeleted}
        />
      </div>
    </div>
  )
}
