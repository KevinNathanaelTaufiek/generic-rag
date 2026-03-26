import { useEffect, useRef, useState } from 'react'
import { fetchUsers } from '../api/users'
import { useUser } from '../context/UserContext'
import { useChatStore } from '../store/chatStore'

export function UserSwitcher() {
  const { username, setUsername, isPickerOpen, openPicker, closePicker } = useUser()
  const switchUser = useChatStore((s) => s.switchUser)
  const [predefinedUsers, setPredefinedUsers] = useState<string[]>([])
  const popoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchUsers().then(setPredefinedUsers).catch(() => {})
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!isPickerOpen) return
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        if (username) closePicker()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [isPickerOpen, username, closePicker])

  function handleSwitch(name: string) {
    if (!name) return
    setUsername(name)
    switchUser(name)
  }

  return (
    <div className="relative" ref={popoverRef}>
      {/* Pill button */}
      <button
        onClick={isPickerOpen ? (username ? closePicker : undefined) : openPicker}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
        <span className="text-gray-700 dark:text-gray-200">{username || 'Guest'}</span>
      </button>

      {/* Popover */}
      {isPickerOpen && (
        <div className="absolute right-0 mt-2 w-44 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-100 dark:border-slate-700">
            <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">Switch User</p>
          </div>
          <div className="py-1">
            {predefinedUsers.map((u) => (
              <button
                key={u}
                onClick={() => handleSwitch(u)}
                className={`w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2 ${
                  u === username
                    ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium'
                    : 'hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-700 dark:text-slate-200'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${u === username ? 'bg-indigo-500' : 'bg-transparent'}`} />
                {u}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
