import { create } from 'zustand'
import type { DisplayMessage } from '../components/ChatWindow'

const ALL_TOOLS = ['search_knowledge', 'search_web', 'send_notification', 'get_random_number', 'crud_data']

interface ChatStore {
  messages: DisplayMessage[]
  sessionId: string | undefined
  loading: boolean
  pendingApproval: boolean
  strictMode: boolean
  enabledTools: string[]
  toolsBeforeStrict: string[]
  currentUsername: string
  userMessages: Record<string, DisplayMessage[]>

  setMessages: (updater: DisplayMessage[] | ((prev: DisplayMessage[]) => DisplayMessage[])) => void
  setMessagesForUser: (username: string, updater: DisplayMessage[] | ((prev: DisplayMessage[]) => DisplayMessage[])) => void
  setSessionId: (id: string | undefined) => void
  setLoading: (v: boolean) => void
  setPendingApproval: (v: boolean) => void
  toggleStrictMode: () => void
  toggleTool: (name: string) => void
  toggleAllTools: () => void
  resetChat: () => void
  switchUser: (name: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  sessionId: undefined,
  loading: false,
  pendingApproval: false,
  strictMode: false,
  enabledTools: ['search_knowledge'],
  toolsBeforeStrict: ['search_knowledge'],
  currentUsername: localStorage.getItem('rag_username') ?? '',
  userMessages: {},

  setMessages: (updater) =>
    set((state) => ({
      messages: typeof updater === 'function' ? updater(state.messages) : updater,
    })),

  setMessagesForUser: (username, updater) =>
    set((state) => {
      const current = state.userMessages[username] ?? (username === state.currentUsername ? state.messages : [])
      const next = typeof updater === 'function' ? updater(current) : updater
      const isActive = username === state.currentUsername
      return {
        userMessages: { ...state.userMessages, [username]: next },
        ...(isActive ? { messages: next } : {}),
      }
    }),

  setSessionId: (id) => set({ sessionId: id }),
  setLoading: (v) => set({ loading: v }),
  setPendingApproval: (v) => set({ pendingApproval: v }),

  toggleStrictMode: () => {
    const { strictMode, enabledTools } = get()
    if (!strictMode) {
      set({ toolsBeforeStrict: enabledTools, enabledTools: ['search_knowledge'], strictMode: true })
    } else {
      set((state) => ({ enabledTools: state.toolsBeforeStrict, strictMode: false }))
    }
  },

  toggleTool: (name) =>
    set((state) => ({
      enabledTools: state.enabledTools.includes(name)
        ? state.enabledTools.filter((t) => t !== name)
        : [...state.enabledTools, name],
    })),

  toggleAllTools: () =>
    set((state) => ({
      enabledTools: state.enabledTools.length === ALL_TOOLS.length ? [] : [...ALL_TOOLS],
    })),

  resetChat: () => set({ messages: [], sessionId: undefined, pendingApproval: false, loading: false }),

  switchUser: (name: string) => {
    const { currentUsername, messages, userMessages } = get()
    // Save current user's messages
    const updatedUserMessages = { ...userMessages, [currentUsername]: messages }
    // Load new user's messages (empty if first time)
    const newMessages = updatedUserMessages[name] ?? []
    set({
      userMessages: updatedUserMessages,
      currentUsername: name,
      messages: newMessages,
      sessionId: undefined,
      pendingApproval: false,
      loading: false,
    })
  },
}))

export { ALL_TOOLS }
