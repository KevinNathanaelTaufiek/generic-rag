import { useRef, useState } from 'react'
import type { DocumentInfo, PreviewResponse } from '../api/knowledge'
import { addText, previewFile, previewText, uploadFile } from '../api/knowledge'

interface Props {
  onAdded: (doc: DocumentInfo) => void
}

function PreviewPanel({
  preview,
  onConfirm,
  onCancel,
  uploading,
}: {
  preview: PreviewResponse
  onConfirm: () => void
  onCancel: () => void
  uploading: boolean
}) {
  const [showFull, setShowFull] = useState(false)
  const PREVIEW_LIMIT = 800

  const isLong = preview.content.length > PREVIEW_LIMIT
  const displayedContent = showFull ? preview.content : preview.content.slice(0, PREVIEW_LIMIT)

  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/20 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">Preview</h3>
        <button
          onClick={onCancel}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
        >
          ✕ Cancel
        </button>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="px-2 py-1 rounded-full bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300">
          Title: <span className="font-medium">{preview.title}</span>
        </span>
        <span className="px-2 py-1 rounded-full bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300">
          Type: <span className="font-medium">{preview.source_type}</span>
        </span>
        <span className="px-2 py-1 rounded-full bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300">
          {preview.char_count.toLocaleString()} chars
        </span>
        <span className="px-2 py-1 rounded-full bg-indigo-100 dark:bg-indigo-800/50 border border-indigo-200 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300 font-medium">
          ~{preview.estimated_chunks} chunks
        </span>
      </div>

      {/* Content preview */}
      <div className="rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3">
        <p className="text-xs text-gray-400 dark:text-slate-500 mb-2">Content</p>
        <pre className="text-xs text-gray-700 dark:text-slate-200 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto">
          {displayedContent}
          {isLong && !showFull && <span className="text-gray-400 dark:text-slate-500">…</span>}
        </pre>
        {isLong && (
          <button
            onClick={() => setShowFull(v => !v)}
            className="mt-2 text-xs text-indigo-500 hover:underline"
          >
            {showFull ? 'Show less' : `Show full content (${preview.content.length.toLocaleString()} chars)`}
          </button>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          disabled={uploading}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 dark:bg-indigo-500 text-white hover:bg-indigo-700 dark:hover:bg-indigo-600 disabled:opacity-50 cursor-pointer"
        >
          {uploading ? 'Uploading…' : 'Confirm Upload'}
        </button>
        <button
          onClick={onCancel}
          disabled={uploading}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-slate-600 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 cursor-pointer"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function KnowledgeUpload({ onAdded }: Props) {
  // --- text state ---
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [textPreview, setTextPreview] = useState<PreviewResponse | null>(null)
  const [textPreviewing, setTextPreviewing] = useState(false)
  const [textUploading, setTextUploading] = useState(false)

  // --- file state ---
  const fileRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<PreviewResponse | null>(null)
  const [filePreviewing, setFilePreviewing] = useState(false)
  const [fileUploading, setFileUploading] = useState(false)

  const [error, setError] = useState('')

  // ---------------------------------------------------------------------------
  // Text flow
  // ---------------------------------------------------------------------------

  async function handleTextPreview() {
    if (!text.trim()) return
    setTextPreviewing(true)
    setError('')
    try {
      const preview = await previewText(text, title || undefined)
      setTextPreview(preview)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to generate preview.')
    } finally {
      setTextPreviewing(false)
    }
  }

  async function handleTextConfirm() {
    if (!textPreview) return
    setTextUploading(true)
    setError('')
    try {
      const doc = await addText(text, title || undefined)
      onAdded(doc)
      setText('')
      setTitle('')
      setTextPreview(null)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to add text.')
    } finally {
      setTextUploading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // File flow
  // ---------------------------------------------------------------------------

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setSelectedFile(file)
    setFilePreview(null)
    setError('')
    setFilePreviewing(true)
    try {
      const preview = await previewFile(file)
      setFilePreview(preview)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to read file.')
      setSelectedFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } finally {
      setFilePreviewing(false)
    }
  }

  async function handleFileConfirm() {
    if (!selectedFile) return
    setFileUploading(true)
    setError('')
    try {
      const doc = await uploadFile(selectedFile)
      onAdded(doc)
      setSelectedFile(null)
      setFilePreview(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to upload file.')
    } finally {
      setFileUploading(false)
    }
  }

  function handleFileCancel() {
    setSelectedFile(null)
    setFilePreview(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className="space-y-4">
      {/* Text input */}
      <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-700 dark:text-slate-300">Add text</h2>
        <input
          className="w-full rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500"
          placeholder="Title (optional)"
          value={title}
          onChange={e => setTitle(e.target.value)}
          disabled={!!textPreview}
        />
        <textarea
          className="w-full rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:focus:ring-indigo-500 resize-none"
          rows={5}
          placeholder="Paste your text here..."
          value={text}
          onChange={e => { setText(e.target.value); setTextPreview(null) }}
          disabled={!!textPreview}
        />

        {!textPreview ? (
          <button
            className="rounded-lg bg-indigo-600 dark:bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:hover:bg-indigo-600 disabled:opacity-50 cursor-pointer"
            onClick={handleTextPreview}
            disabled={textPreviewing || !text.trim()}
          >
            {textPreviewing ? 'Generating preview…' : 'Preview'}
          </button>
        ) : (
          <PreviewPanel
            preview={textPreview}
            onConfirm={handleTextConfirm}
            onCancel={() => setTextPreview(null)}
            uploading={textUploading}
          />
        )}
      </div>

      {/* File upload */}
      <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 shadow-sm space-y-3">
        <h2 className="font-semibold text-gray-700 dark:text-slate-300">Upload file</h2>
        <p className="text-xs text-gray-400 dark:text-slate-500">Supported: PDF, TXT, MD</p>

        {!filePreview && (
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.md"
              className="block text-sm text-gray-500 dark:text-slate-400 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 dark:file:bg-indigo-900/40 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700 dark:file:text-indigo-300 hover:file:bg-indigo-100 dark:hover:file:bg-indigo-900/60 cursor-pointer"
              onChange={handleFileChange}
              disabled={filePreviewing}
            />
            {filePreviewing && (
              <p className="text-xs text-gray-400 dark:text-slate-500">Reading file…</p>
            )}
          </>
        )}

        {filePreview && (
          <PreviewPanel
            preview={filePreview}
            onConfirm={handleFileConfirm}
            onCancel={handleFileCancel}
            uploading={fileUploading}
          />
        )}
      </div>

      {error && <p className="text-sm text-red-500 dark:text-red-400">{error}</p>}
    </div>
  )
}
