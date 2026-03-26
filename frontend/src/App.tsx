import { Routes, Route, NavLink } from 'react-router-dom'
import KnowledgePage from './pages/KnowledgePage'
import ChatPage from './pages/ChatPage'
import AuditPage from './pages/AuditPage'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import { UserProvider } from './context/UserContext'
import { UserSwitcher } from './components/UserSwitcher'

function AppInner() {
  const { theme, toggle } = useTheme()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      {/* Top nav */}
      <nav className="bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 flex items-center gap-1 h-14">
          <span className="font-bold text-indigo-600 dark:text-indigo-400 mr-4 text-lg">⚡ RAG</span>
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `px-4 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-800 dark:hover:text-slate-200'
              }`
            }
          >
            Chat
          </NavLink>
          <NavLink
            to="/knowledge"
            className={({ isActive }) =>
              `px-4 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-800 dark:hover:text-slate-200'
              }`
            }
          >
            Knowledge
          </NavLink>
          <NavLink
            to="/audit"
            className={({ isActive }) =>
              `px-4 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-800 dark:hover:text-slate-200'
              }`
            }
          >
            Audit
          </NavLink>
          <div className="ml-auto flex items-center gap-2">
            <UserSwitcher />
            <button
              onClick={toggle}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-gray-500 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors cursor-pointer"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="4"/>
                  <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
                </svg>
              )}
            </button>
          </div>
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/audit" element={<AuditPage />} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <AppInner />
      </UserProvider>
    </ThemeProvider>
  )
}
