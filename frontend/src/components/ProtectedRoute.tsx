/**
 * Protected route wrapper component.
 *
 * Redirects unauthenticated users to /login.
 * Redirects users requiring password change to /change-password.
 * Uses authStore to check authentication state.
 */

import { Navigate, useLocation } from 'react-router-dom'

import { useAuthStore } from '../state/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Redirect to password change if required (block all other routes except /logout)
  if (
    user?.requirePasswordChange &&
    location.pathname !== '/change-password' &&
    location.pathname !== '/logout'
  ) {
    return <Navigate to="/change-password" replace />
  }

  return <>{children}</>
}
