/**
 * Unit tests for authStore.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

import { useAuthStore } from '../../src/state/authStore'

describe('authStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset store to initial state
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  })

  it('has initial state', () => {
    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('setTokens updates tokens and sets authenticated', () => {
    const { setTokens } = useAuthStore.getState()

    setTokens('access-token', 'refresh-token')

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-token')
    expect(state.refreshToken).toBe('refresh-token')
    expect(state.isAuthenticated).toBe(true)
  })

  it('clearAuth resets all state', () => {
    // First set some state
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    // Then clear it
    const { clearAuth } = useAuthStore.getState()
    clearAuth()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('login sets tokens and isAuthenticated on success', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          data: { accessToken: 'access', refreshToken: 'refresh' }
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          data: { userId: 1, username: 'admin', requirePasswordChange: false }
        }),
      })

    const { login } = useAuthStore.getState()
    await login('admin', 'admin')

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access')
    expect(state.refreshToken).toBe('refresh')
    expect(state.isAuthenticated).toBe(true)
    expect(state.user).toEqual({ userId: 1, username: 'admin', requirePasswordChange: false })
  })

  it('login throws on failure', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: { detail: 'Invalid credentials' } }),
    })

    const { login } = useAuthStore.getState()

    await expect(login('admin', 'wrong')).rejects.toThrow('Invalid credentials')
  })

  it('logout clears state', async () => {
    // Set up authenticated state
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: { message: 'Logged out' } }),
    })

    const { logout } = useAuthStore.getState()
    await logout()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })
})
