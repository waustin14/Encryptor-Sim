/**
 * Unit tests for authStore.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

import { useAuthStore } from '../../src/state/authStore'

function mockJsonResponse(payload: unknown, ok = true) {
  const raw = JSON.stringify(payload)
  return {
    ok,
    json: () => Promise.resolve(payload),
    text: () => Promise.resolve(raw),
  }
}

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
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: { accessToken: 'access', refreshToken: 'refresh' },
        })
      )
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: { userId: 1, username: 'admin', requirePasswordChange: false },
        })
      )

    const { login } = useAuthStore.getState()
    await login('admin', 'admin')

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access')
    expect(state.refreshToken).toBe('refresh')
    expect(state.isAuthenticated).toBe(true)
    expect(state.user).toEqual({ userId: 1, username: 'admin', requirePasswordChange: false })
  })

  it('login throws on failure', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce(
      mockJsonResponse({ detail: { detail: 'Invalid credentials' } }, false)
    )

    const { login } = useAuthStore.getState()

    await expect(login('admin', 'wrong')).rejects.toThrow('Invalid credentials')
  })

  it('changePassword updates user state on success', async () => {
    // Set up authenticated state with requirePasswordChange=true
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    global.fetch = vi.fn().mockResolvedValueOnce({
      ...mockJsonResponse({
        data: { message: 'Password changed successfully', requirePasswordChange: false },
      }),
    })

    const { changePassword } = useAuthStore.getState()
    await changePassword('admin', 'newpass123')

    const state = useAuthStore.getState()
    expect(state.user?.requirePasswordChange).toBe(false)
    expect(state.isAuthenticated).toBe(true)
  })

  it('changePassword throws on failure', async () => {
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    global.fetch = vi.fn().mockResolvedValueOnce(
      mockJsonResponse(
        {
          detail: { detail: 'Current password is incorrect' },
        },
        false
      )
    )

    const { changePassword } = useAuthStore.getState()
    await expect(changePassword('wrong', 'newpass123')).rejects.toThrow(
      'Current password is incorrect'
    )
  })

  it('login uses relative URL for HTTPS compatibility', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: { accessToken: 'access', refreshToken: 'refresh' },
        })
      )
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: { userId: 1, username: 'admin', requirePasswordChange: false },
        })
      )

    const { login } = useAuthStore.getState()
    await login('admin', 'admin')

    // Verify fetch was called with relative URL (works over HTTPS via proxy/same-origin)
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/auth/login',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('changePassword uses relative URL for HTTPS compatibility', async () => {
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(mockJsonResponse({ data: { message: 'Password changed successfully' } }))

    const { changePassword } = useAuthStore.getState()
    await changePassword('admin', 'newpass123')

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/auth/change-password',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('logout uses relative URL for HTTPS compatibility', async () => {
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    global.fetch = vi.fn().mockResolvedValueOnce(mockJsonResponse({ data: { message: 'Logged out' } }))

    const { logout } = useAuthStore.getState()
    await logout()

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/auth/logout',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('logout clears state', async () => {
    // Set up authenticated state
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    global.fetch = vi.fn().mockResolvedValueOnce(mockJsonResponse({ data: { message: 'Logged out' } }))

    const { logout } = useAuthStore.getState()
    await logout()

    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.refreshToken).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })
})
