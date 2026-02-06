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
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
  setTokens: (accessToken: string, refreshToken: string) => void
  clearAuth: () => void
}

async function parseResponseBody(response: Response): Promise<{
  data: unknown | null
  rawText: string
}> {
  const rawText = await response.text()
  if (!rawText) {
    return { data: null, rawText: '' }
  }

  try {
    return { data: JSON.parse(rawText), rawText }
  } catch {
    return { data: null, rawText }
  }
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
    const { data: responseBody, rawText } = await parseResponseBody(response)

    if (!response.ok) {
      if (responseBody && typeof responseBody === 'object' && 'detail' in responseBody) {
        const detail = (responseBody as { detail?: unknown }).detail
        if (typeof detail === 'object' && detail !== null && 'detail' in detail) {
          const nestedDetail = (detail as { detail?: unknown }).detail
          if (typeof nestedDetail === 'string') {
            throw new Error(nestedDetail)
          }
        }
        if (typeof detail === 'string') {
          throw new Error(detail)
        }
      }

      if (rawText.trim()) {
        throw new Error(`Login failed: unexpected response from API`)
      }

      throw new Error('Login failed')
    }

    if (!responseBody || typeof responseBody !== 'object' || !('data' in responseBody)) {
      throw new Error('Login failed: API returned invalid response')
    }

    const { data } = responseBody as {
      data?: { accessToken?: string; refreshToken?: string }
    }
    if (!data?.accessToken || !data?.refreshToken) {
      throw new Error('Login failed: API returned incomplete token data')
    }

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
      const { data: profileBody } = await parseResponseBody(profileResponse)
      if (profileBody && typeof profileBody === 'object' && 'data' in profileBody) {
        const userData = (profileBody as { data?: User }).data
        if (userData) {
          set({ user: userData })
        }
      }
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

  changePassword: async (currentPassword: string, newPassword: string) => {
    const token = get().accessToken

    const response = await fetch('/api/v1/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ currentPassword, newPassword }),
    })
    const { data: responseBody } = await parseResponseBody(response)

    if (!response.ok) {
      // Handle RFC 7807 error format and fallbacks
      let errorMessage = 'Password change failed'
      if (responseBody && typeof responseBody === 'object' && 'detail' in responseBody) {
        const detail = (responseBody as { detail?: unknown }).detail
        if (typeof detail === 'object' && detail !== null && 'detail' in detail) {
          const nestedDetail = (detail as { detail?: unknown }).detail
          if (typeof nestedDetail === 'string') {
            errorMessage = nestedDetail
          }
        } else if (typeof detail === 'string') {
          errorMessage = detail
        }
      }

      throw new Error(errorMessage)
    }

    // Update user state to reflect password no longer requires change
    const currentUser = get().user
    if (currentUser) {
      set({ user: { ...currentUser, requirePasswordChange: false } })
    }
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
