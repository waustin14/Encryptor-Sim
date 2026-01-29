/**
 * Authentication state management using Zustand.
 *
 * CRITICAL: Tokens stored in memory only (Zustand, not localStorage)
 * Per NFR21: "Web UI shall store JWT in memory only (not localStorage)"
 */

import { create } from 'zustand'

interface User {
  userId: number
  username: string
  requirePasswordChange: boolean
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  setTokens: (accessToken: string, refreshToken: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,

  login: async (username: string, password: string) => {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail?.detail || error.detail || 'Login failed')
    }

    const { data } = await response.json()
    set({
      accessToken: data.accessToken,
      refreshToken: data.refreshToken,
      isAuthenticated: true,
    })

    // Fetch user profile after login
    const profileResponse = await fetch('/api/v1/auth/me', {
      headers: {
        Authorization: `Bearer ${data.accessToken}`,
      },
    })

    if (profileResponse.ok) {
      const { data: userData } = await profileResponse.json()
      set({ user: userData })
    }
  },

  logout: async () => {
    const token = get().accessToken

    if (token) {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
      } catch (err) {
        console.error('Logout failed:', err)
      }
    }

    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  },

  setTokens: (accessToken: string, refreshToken: string) => {
    set({ accessToken, refreshToken, isAuthenticated: true })
  },

  clearAuth: () => {
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  },
}))
