/**
 * Unit tests for ProtectedRoute component.
 *
 * Tests authentication guard and password change enforcement.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'

import { ProtectedRoute } from '../../src/components/ProtectedRoute'
import { useAuthStore } from '../../src/state/authStore'

function renderWithRouter(initialRoute: string, routes: React.ReactElement) {
  return render(
    <ChakraProvider value={defaultSystem}>
      <MemoryRouter initialEntries={[initialRoute]}>
        {routes}
      </MemoryRouter>
    </ChakraProvider>
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  })

  it('redirects to /login when not authenticated', () => {
    renderWithRouter(
      '/dashboard',
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Dashboard</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    )

    expect(screen.getByText('Login Page')).toBeTruthy()
  })

  it('allows access to dashboard when authenticated without password change required', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
    })

    renderWithRouter(
      '/dashboard',
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Dashboard</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    )

    expect(screen.getByText('Dashboard')).toBeTruthy()
  })

  it('redirects to /change-password when requirePasswordChange is true', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
    })

    renderWithRouter(
      '/dashboard',
      <Routes>
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Dashboard</div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/change-password"
          element={
            <ProtectedRoute>
              <div>Change Password</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    )

    expect(screen.getByText('Change Password')).toBeTruthy()
  })

  it('allows access to /change-password when requirePasswordChange is true', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
    })

    renderWithRouter(
      '/change-password',
      <Routes>
        <Route
          path="/change-password"
          element={
            <ProtectedRoute>
              <div>Change Password Form</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    )

    expect(screen.getByText('Change Password Form')).toBeTruthy()
  })

  it('allows access to /logout when requirePasswordChange is true', () => {
    useAuthStore.setState({
      isAuthenticated: true,
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
    })

    renderWithRouter(
      '/logout',
      <Routes>
        <Route
          path="/logout"
          element={
            <ProtectedRoute>
              <div>Logout Page</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    )

    expect(screen.getByText('Logout Page')).toBeTruthy()
  })
})
