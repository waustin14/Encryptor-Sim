import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useRoutesStore } from '../../src/state/routesStore'
import { useAuthStore } from '../../src/state/authStore'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('routesStore', () => {
  beforeEach(() => {
    // Reset store state
    useRoutesStore.setState({ routes: [], loading: false, error: null })
    // Set a mock access token
    useAuthStore.setState({ accessToken: 'mock-token' })
    mockFetch.mockReset()
  })

  describe('fetchRoutes', () => {
    it('sets loading to true during fetch', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      })

      const promise = useRoutesStore.getState().fetchRoutes()
      expect(useRoutesStore.getState().loading).toBe(true)
      await promise
      expect(useRoutesStore.getState().loading).toBe(false)
    })

    it('stores fetched routes', async () => {
      const mockRoutes = [
        { routeId: 1, peerId: 1, peerName: 'peer-1', destinationCidr: '192.168.1.0/24', createdAt: '', updatedAt: '' },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockRoutes }),
      })

      await useRoutesStore.getState().fetchRoutes()
      expect(useRoutesStore.getState().routes).toEqual(mockRoutes)
    })

    it('sets error on fetch failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      })

      await useRoutesStore.getState().fetchRoutes()
      expect(useRoutesStore.getState().error).toContain('Failed to load routes')
    })

    it('sends authorization header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      })

      await useRoutesStore.getState().fetchRoutes()
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/routes', {
        headers: { Authorization: 'Bearer mock-token' },
      })
    })

    it('fetches with peerId filter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      })

      await useRoutesStore.getState().fetchRoutes(5)
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/routes?peerId=5', {
        headers: { Authorization: 'Bearer mock-token' },
      })
    })
  })

  describe('createRoute', () => {
    it('adds created route to store', async () => {
      const newRoute = {
        routeId: 1,
        peerId: 1,
        peerName: 'peer-1',
        destinationCidr: '192.168.1.0/24',
        createdAt: '',
        updatedAt: '',
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: newRoute }),
      })

      await useRoutesStore.getState().createRoute({
        peerId: 1,
        destinationCidr: '192.168.1.0/24',
      })

      expect(useRoutesStore.getState().routes).toHaveLength(1)
      expect(useRoutesStore.getState().routes[0].destinationCidr).toBe('192.168.1.0/24')
    })

    it('sets error on create failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: { detail: 'Peer not found' },
        }),
      })

      await expect(
        useRoutesStore.getState().createRoute({
          peerId: 99999,
          destinationCidr: '192.168.1.0/24',
        })
      ).rejects.toThrow()

      expect(useRoutesStore.getState().error).toBe('Peer not found')
    })

    it('sends POST with correct body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { routeId: 1 } }),
      })

      await useRoutesStore.getState().createRoute({
        peerId: 1,
        destinationCidr: '10.0.0.0/8',
      })

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/routes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({
          peerId: 1,
          destinationCidr: '10.0.0.0/8',
        }),
      })
    })
  })

  describe('deleteRoute', () => {
    it('removes route from store on successful delete', async () => {
      useRoutesStore.setState({
        routes: [
          { routeId: 1, peerId: 1, peerName: 'peer-1', destinationCidr: '192.168.1.0/24', createdAt: '', updatedAt: '' },
          { routeId: 2, peerId: 1, peerName: 'peer-1', destinationCidr: '10.0.0.0/8', createdAt: '', updatedAt: '' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { routeId: 1 }, meta: {} }),
      })

      await useRoutesStore.getState().deleteRoute(1)

      expect(useRoutesStore.getState().routes).toHaveLength(1)
      expect(useRoutesStore.getState().routes[0].routeId).toBe(2)
    })

    it('sends DELETE with correct URL and auth header', async () => {
      useRoutesStore.setState({
        routes: [
          { routeId: 5, peerId: 1, peerName: 'peer-1', destinationCidr: '192.168.1.0/24', createdAt: '', updatedAt: '' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { routeId: 5 }, meta: {} }),
      })

      await useRoutesStore.getState().deleteRoute(5)

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/routes/5', {
        method: 'DELETE',
        headers: { Authorization: 'Bearer mock-token' },
      })
    })

    it('throws error on 404 response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({
          detail: { detail: 'Route with ID 99999 not found' },
        }),
      })

      await expect(useRoutesStore.getState().deleteRoute(99999)).rejects.toThrow('Route with ID 99999 not found')
      expect(useRoutesStore.getState().error).toBe('Route with ID 99999 not found')
    })

    it('throws error on unexpected status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({
          detail: { detail: 'Internal server error' },
        }),
      })

      await expect(useRoutesStore.getState().deleteRoute(1)).rejects.toThrow('Internal server error')
    })

    it('clears error before delete attempt', async () => {
      useRoutesStore.setState({ error: 'previous error' })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { routeId: 1 }, meta: {} }),
      })

      await useRoutesStore.getState().deleteRoute(1)
      expect(useRoutesStore.getState().error).toBeNull()
    })
  })

  describe('updateRoute', () => {
    it('updates route in store', async () => {
      useRoutesStore.setState({
        routes: [
          { routeId: 1, peerId: 1, peerName: 'peer-1', destinationCidr: '192.168.1.0/24', createdAt: '', updatedAt: '' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { routeId: 1, peerId: 1, peerName: 'peer-1', destinationCidr: '10.0.0.0/8', createdAt: '', updatedAt: '' },
        }),
      })

      await useRoutesStore.getState().updateRoute(1, { destinationCidr: '10.0.0.0/8' })

      expect(useRoutesStore.getState().routes[0].destinationCidr).toBe('10.0.0.0/8')
    })

    it('sends PUT with correct URL', async () => {
      useRoutesStore.setState({
        routes: [
          { routeId: 5, peerId: 1, peerName: 'peer-1', destinationCidr: '192.168.1.0/24', createdAt: '', updatedAt: '' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { routeId: 5 } }),
      })

      await useRoutesStore.getState().updateRoute(5, { destinationCidr: '10.0.0.0/8' })

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/routes/5', expect.objectContaining({
        method: 'PUT',
      }))
    })

    it('sets error on update failure', async () => {
      useRoutesStore.setState({
        routes: [
          { routeId: 1, peerId: 1, peerName: 'peer-1', destinationCidr: '192.168.1.0/24', createdAt: '', updatedAt: '' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: { detail: 'Route not found' },
        }),
      })

      await expect(useRoutesStore.getState().updateRoute(1, { destinationCidr: '10.0.0.0/8' })).rejects.toThrow()
      expect(useRoutesStore.getState().error).toBe('Route not found')
    })
  })
})
