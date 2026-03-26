import { createContext, useContext, useEffect, useState } from 'react'

interface UserContextValue {
  username: string
  setUsername: (name: string) => void
  isPickerOpen: boolean
  openPicker: () => void
  closePicker: () => void
}

const UserContext = createContext<UserContextValue>({
  username: '',
  setUsername: () => {},
  isPickerOpen: false,
  openPicker: () => {},
  closePicker: () => {},
})

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsernameState] = useState<string>(() => {
    return localStorage.getItem('rag_username') ?? ''
  })
  const [isPickerOpen, setIsPickerOpen] = useState(() => {
    return !localStorage.getItem('rag_username')
  })

  function setUsername(name: string) {
    const trimmed = name.trim()
    localStorage.setItem('rag_username', trimmed)
    setUsernameState(trimmed)
    setIsPickerOpen(false)
  }

  useEffect(() => {
    if (!username) setIsPickerOpen(true)
  }, [username])

  return (
    <UserContext.Provider
      value={{
        username,
        setUsername,
        isPickerOpen,
        openPicker: () => setIsPickerOpen(true),
        closePicker: () => setIsPickerOpen(false),
      }}
    >
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  return useContext(UserContext)
}
