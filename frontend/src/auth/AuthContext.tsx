import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getMe, login as apiLogin, register as apiRegister, type User } from '../api'

const TOKEN_KEY = 'reviewerlens_token'

interface AuthContextValue {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function storeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // ignore — auth just won't persist across reloads in this browser context
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }
    getMe(token)
      .then(setUser)
      .catch(() => {
        storeToken(null)
        setToken(null)
      })
      .finally(() => setIsLoading(false))
  }, [token])

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiLogin(email, password)
    storeToken(data.access_token)
    setToken(data.access_token)
    setUser(data.user)
  }, [])

  const register = useCallback(async (name: string, email: string, password: string) => {
    const data = await apiRegister(name, email, password)
    storeToken(data.access_token)
    setToken(data.access_token)
    setUser(data.user)
  }, [])

  const logout = useCallback(() => {
    storeToken(null)
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, token, isLoading, login, register, logout }),
    [user, token, isLoading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
