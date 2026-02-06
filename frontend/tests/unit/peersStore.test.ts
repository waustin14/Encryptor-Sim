import { describe, it, expect, beforeEach, vi } from 'vitest'
import { usePeersStore } from '../../src/state/peersStore'
import { useAuthStore } from '../../src/state/authStore'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('peersStore', () => {
  beforeEach(() => {
    // Reset store state
    usePeersStore.setState({ peers: [], loading: false, error: null })
    // Set a mock access token
    useAuthStore.setState({ accessToken: 'mock-token' })
    mockFetch.mockReset()
  })

  describe('fetchPeers', () => {
    it('sets loading to true during fetch', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      })

      const promise = usePeersStore.getState().fetchPeers()
      expect(usePeersStore.getState().loading).toBe(true)
      await promise
      expect(usePeersStore.getState().loading).toBe(false)
    })

    it('stores fetched peers', async () => {
      const mockPeers = [
        { peerId: 1, name: 'peer-1', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true },
        { peerId: 2, name: 'peer-2', remoteIp: '10.0.0.2', ikeVersion: 'ikev1', enabled: false },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockPeers }),
      })

      await usePeersStore.getState().fetchPeers()
      expect(usePeersStore.getState().peers).toEqual(mockPeers)
    })

    it('stores peer enabled field correctly', async () => {
      const mockPeers = [
        {
          peerId: 1,
          name: 'enabled-peer',
          remoteIp: '10.0.0.1',
          ikeVersion: 'ikev2',
          enabled: true,
          createdAt: '2026-02-05T00:00:00Z',
          updatedAt: '2026-02-05T00:00:00Z',
          operationalStatus: 'ready',
          dpdAction: null,
          dpdDelay: null,
          dpdTimeout: null,
          rekeyTime: null
        },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockPeers }),
      })

      await usePeersStore.getState().fetchPeers()
      const peers = usePeersStore.getState().peers
      expect(peers[0].enabled).toBe(true)
    })

    it('sets error on fetch failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      })

      await usePeersStore.getState().fetchPeers()
      expect(usePeersStore.getState().error).toContain('Failed to load peers')
    })

    it('sends authorization header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      })

      await usePeersStore.getState().fetchPeers()
      expect(mockFetch).toHaveBeenCalledWith('/api/v1/peers', {
        headers: { Authorization: 'Bearer mock-token' },
      })
    })
  })

  describe('createPeer', () => {
    it('adds created peer to store', async () => {
      const newPeer = {
        peerId: 1,
        name: 'new-peer',
        remoteIp: '10.1.1.1',
        ikeVersion: 'ikev2',
        enabled: true,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: newPeer }),
      })

      await usePeersStore.getState().createPeer({
        name: 'new-peer',
        remoteIp: '10.1.1.1',
        psk: 'secret',
        ikeVersion: 'ikev2',
      })

      expect(usePeersStore.getState().peers).toHaveLength(1)
      expect(usePeersStore.getState().peers[0].name).toBe('new-peer')
    })

    it('sets error on create failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: { detail: 'Validation error' },
        }),
      })

      await expect(
        usePeersStore.getState().createPeer({
          name: 'bad-peer',
          remoteIp: '999.999.999.999',
          psk: 'secret',
          ikeVersion: 'ikev2',
        })
      ).rejects.toThrow()

      expect(usePeersStore.getState().error).toBe('Validation error')
    })

    it('sends POST with correct body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { peerId: 1 } }),
      })

      await usePeersStore.getState().createPeer({
        name: 'test',
        remoteIp: '10.0.0.1',
        psk: 'secret',
        ikeVersion: 'ikev2',
      })

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/peers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer mock-token',
        },
        body: JSON.stringify({
          name: 'test',
          remoteIp: '10.0.0.1',
          psk: 'secret',
          ikeVersion: 'ikev2',
        }),
      })
    })
  })

  describe('deletePeer', () => {
    it('removes peer from store on success', async () => {
      usePeersStore.setState({
        peers: [
          { peerId: 1, name: 'peer-1', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
          { peerId: 2, name: 'peer-2', remoteIp: '10.0.0.2', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      })

      await usePeersStore.getState().deletePeer(1)

      const peers = usePeersStore.getState().peers
      expect(peers).toHaveLength(1)
      expect(peers[0].peerId).toBe(2)
    })

    it('sends DELETE with correct URL and auth', async () => {
      usePeersStore.setState({
        peers: [
          { peerId: 5, name: 'peer', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      })

      await usePeersStore.getState().deletePeer(5)

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/peers/5', {
        method: 'DELETE',
        headers: { Authorization: 'Bearer mock-token' },
      })
    })

    it('sets error on delete failure', async () => {
      usePeersStore.setState({
        peers: [
          { peerId: 1, name: 'peer', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: { detail: 'Peer not found' },
        }),
      })

      await expect(usePeersStore.getState().deletePeer(1)).rejects.toThrow()
      expect(usePeersStore.getState().error).toBe('Peer not found')
      // Peer should not be removed on failure
      expect(usePeersStore.getState().peers).toHaveLength(1)
    })
  })

  describe('operationalStatus', () => {
    it('stores operationalStatus from API response', async () => {
      const mockPeers = [
        { peerId: 1, name: 'ready-peer', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        { peerId: 2, name: 'incomplete-peer', remoteIp: '', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'incomplete' },
      ]
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockPeers }),
      })

      await usePeersStore.getState().fetchPeers()
      const peers = usePeersStore.getState().peers
      expect(peers[0].operationalStatus).toBe('ready')
      expect(peers[1].operationalStatus).toBe('incomplete')
    })
  })

  describe('updatePeer', () => {
    it('updates peer in store', async () => {
      usePeersStore.setState({
        peers: [
          { peerId: 1, name: 'old-name', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { peerId: 1, name: 'old-name', remoteIp: '10.0.0.2', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        }),
      })

      await usePeersStore.getState().updatePeer(1, { remoteIp: '10.0.0.2' })

      expect(usePeersStore.getState().peers[0].remoteIp).toBe('10.0.0.2')
    })

    it('sends PUT with correct URL', async () => {
      usePeersStore.setState({
        peers: [
          { peerId: 5, name: 'peer', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { peerId: 5 } }),
      })

      await usePeersStore.getState().updatePeer(5, { dpdDelay: 60 })

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/peers/5', expect.objectContaining({
        method: 'PUT',
      }))
    })
  })

  describe('initiatePeer', () => {
    it('sends POST to initiate endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { peerId: 1 },
          meta: { daemonAvailable: true, initiationStatus: 'success' },
        }),
      })

      const result = await usePeersStore.getState().initiatePeer(1)

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/peers/1/initiate', {
        method: 'POST',
        headers: { Authorization: 'Bearer mock-token' },
      })
      expect(result.initiationStatus).toBe('success')
    })

    it('throws error on initiation failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: { detail: 'Peer is not ready for initiation' },
        }),
      })

      await expect(usePeersStore.getState().initiatePeer(1)).rejects.toThrow(
        'Peer is not ready for initiation'
      )

      expect(usePeersStore.getState().error).toBe('Peer is not ready for initiation')
    })

    it('handles daemon unavailable error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          detail: { detail: 'Daemon is not available for tunnel initiation' },
        }),
      })

      await expect(usePeersStore.getState().initiatePeer(1)).rejects.toThrow()
      expect(usePeersStore.getState().error).toContain('Daemon')
    })

    it('throws error when daemon returns error status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { peerId: 1 },
          meta: {
            daemonAvailable: true,
            initiationStatus: 'error',
            initiationMessage: 'Tunnel initiation failed',
          },
        }),
      })

      await expect(usePeersStore.getState().initiatePeer(1)).rejects.toThrow(
        'Tunnel initiation failed'
      )
      expect(usePeersStore.getState().error).toBe('Tunnel initiation failed')
    })
  })

  describe('toggleEnabled', () => {
    it('sends PUT with enabled field and returns warning metadata', async () => {
      usePeersStore.setState({
        peers: [
          { peerId: 1, name: 'peer', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: true, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
        ],
      })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { peerId: 1, name: 'peer', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', enabled: false, dpdAction: null, dpdDelay: null, dpdTimeout: null, rekeyTime: null, createdAt: '', updatedAt: '', operationalStatus: 'ready' },
          meta: { daemonAvailable: false, warning: 'daemon unavailable for part of cleanup' },
        }),
      })

      const result = await usePeersStore.getState().toggleEnabled(1, false)

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/peers/1', expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify({ enabled: false }),
      }))
      expect(result.enabled).toBe(false)
      expect(result.daemonAvailable).toBe(false)
      expect(result.warning).toContain('daemon unavailable')
      expect(usePeersStore.getState().peers[0].enabled).toBe(false)
    })
  })
})
