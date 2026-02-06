/**
 * Route state management using Zustand.
 *
 * Manages route configurations (destination CIDRs) associated with IPsec peers.
 */

import { create } from 'zustand'
import { useAuthStore } from './authStore'

export type Route = {
  routeId: number
  peerId: number
  peerName: string
  destinationCidr: string
  createdAt: string
  updatedAt: string
}

export type RouteCreateRequest = {
  peerId: number
  destinationCidr: string
}

export type RouteUpdateRequest = {
  destinationCidr?: string
}

type RoutesState = {
  routes: Route[]
  loading: boolean
  error: string | null
  fetchRoutes: (peerId?: number) => Promise<void>
  createRoute: (data: RouteCreateRequest) => Promise<void>
  updateRoute: (routeId: number, updates: RouteUpdateRequest) => Promise<void>
  deleteRoute: (routeId: number) => Promise<void>
}

export const useRoutesStore = create<RoutesState>((set) => ({
  routes: [],
  loading: false,
  error: null,

  fetchRoutes: async (peerId?: number) => {
    const token = useAuthStore.getState().accessToken
    set({ loading: true, error: null })
    try {
      const url = peerId != null ? `/api/v1/routes?peerId=${peerId}` : '/api/v1/routes'
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!response.ok) {
        throw new Error(`Failed to load routes (${response.status})`)
      }
      const { data } = (await response.json()) as { data: Route[] }
      set({ routes: data, loading: false })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message, loading: false })
    }
  },

  createRoute: async (data: RouteCreateRequest) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch('/api/v1/routes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to create route'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to create route'
        throw new Error(detail)
      }

      const { data: route } = (await response.json()) as { data: Route }
      set((state) => ({
        routes: [...state.routes, route],
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  updateRoute: async (routeId: number, updates: RouteUpdateRequest) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/routes/${routeId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to update route'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to update route'
        throw new Error(detail)
      }

      const { data: route } = (await response.json()) as { data: Route }
      set((state) => ({
        routes: state.routes.map((r) => (r.routeId === route.routeId ? route : r)),
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  deleteRoute: async (routeId: number) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/routes/${routeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to delete route'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to delete route'
        throw new Error(detail)
      }

      set((state) => ({
        routes: state.routes.filter((r) => r.routeId !== routeId),
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },
}))
