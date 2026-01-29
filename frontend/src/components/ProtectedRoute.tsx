/**
 * Protected route wrapper component.
 *
 * Redirects unauthenticated users to /login.
 * Uses authStore to check authentication state.
 */

import { Navigate } from 'react-router-dom'

import { useAuthStore } from '../state/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
