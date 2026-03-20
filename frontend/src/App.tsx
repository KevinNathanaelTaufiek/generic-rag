import { useState } from 'react'
import KnowledgePage from './pages/KnowledgePage'
import ChatPage from './pages/ChatPage'

type Tab = 'knowledge' | 'chat'

export default function App() {
  const [tab, setTab] = useState<Tab>('chat')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 flex items-center gap-1 h-14">
          <span className="font-bold text-indigo-600 mr-4 text-lg">⚡ RAG</span>
          <button
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              tab === 'chat'
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-gray-500 hover:text-gray-800'
            }`}
            onClick={() => setTab('chat')}
          >
            Chat
          </button>
          <button
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
              tab === 'knowledge'
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-gray-500 hover:text-gray-800'
            }`}
            onClick={() => setTab('knowledge')}
          >
            Knowledge
          </button>
        </div>
      </nav>

      {tab === 'chat' ? <ChatPage /> : <KnowledgePage />}
    </div>
  )
}
