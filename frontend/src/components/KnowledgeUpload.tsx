import { useRef, useState } from 'react'
import type { DocumentInfo } from '../api/knowledge'
import { addText, uploadFile } from '../api/knowledge'

interface Props {
  onAdded: (doc: DocumentInfo) => void
}

export default function KnowledgeUpload({ onAdded }: Props) {
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleAddText() {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    try {
      const doc = await addText(text, title || undefined)
      onAdded(doc)
      setText('')
      setTitle('')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to add text.')
    } finally {
      setLoading(false)
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const doc = await uploadFile(file)
      onAdded(doc)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to upload file.')
    } finally {
      setLoading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="space-y-4">
      {/* Text input */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-700">Add text</h2>
        <input
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="Title (optional)"
          value={title}
          onChange={e => setTitle(e.target.value)}
        />
        <textarea
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
          rows={5}
          placeholder="Paste your text here..."
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <button
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 cursor-pointer"
          onClick={handleAddText}
          disabled={loading || !text.trim()}
        >
          {loading ? 'Adding…' : 'Add text'}
        </button>
      </div>

      {/* File upload */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-700">Upload file</h2>
        <p className="text-xs text-gray-400">Supported: PDF, TXT, MD</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md"
          className="block text-sm text-gray-500 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
          onChange={handleFileChange}
          disabled={loading}
        />
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  )
}
