/**
 * Main application component with routing.
 *
 * Sets up React Router for navigation between pages.
 * Protects dashboard and other authenticated routes.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { ProtectedRoute } from './components/ProtectedRoute'
import { ChangePasswordPage } from './pages/ChangePasswordPage'
import { DashboardPage } from './pages/DashboardPage'
import { InterfacesPage } from './pages/InterfacesPage'
import { LoginPage } from './pages/LoginPage'
import { PeersPage } from './pages/PeersPage'
import { RoutesPage } from './pages/RoutesPage'

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/change-password"
          element={
            <ProtectedRoute>
              <ChangePasswordPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/interfaces"
          element={
            <ProtectedRoute>
              <InterfacesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/peers"
          element={
            <ProtectedRoute>
              <PeersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/routes"
          element={
            <ProtectedRoute>
              <RoutesPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
