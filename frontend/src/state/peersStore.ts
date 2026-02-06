/**
 * IPsec peer state management using Zustand.
 *
 * Manages peer configurations for IPsec tunnels.
 */

import { create } from 'zustand'
import { useAuthStore } from './authStore'

export type Peer = {
  peerId: number
  name: string
  remoteIp: string
  ikeVersion: string
  enabled: boolean
  dpdAction: string | null
  dpdDelay: number | null
  dpdTimeout: number | null
  rekeyTime: number | null
  createdAt: string
  updatedAt: string
  operationalStatus: string
}

export type PeerCreateRequest = {
  name: string
  remoteIp: string
  psk: string
  ikeVersion: string
  enabled?: boolean
  dpdAction?: string
  dpdDelay?: number
  dpdTimeout?: number
  rekeyTime?: number
}

export type PeerUpdateRequest = {
  name?: string
  remoteIp?: string
  psk?: string
  ikeVersion?: string
  enabled?: boolean
  dpdAction?: string
  dpdDelay?: number
  dpdTimeout?: number
  rekeyTime?: number
}

type PeersState = {
  peers: Peer[]
  loading: boolean
  error: string | null
  fetchPeers: () => Promise<void>
  createPeer: (peerData: PeerCreateRequest) => Promise<void>
  updatePeer: (peerId: number, updates: PeerUpdateRequest) => Promise<void>
  deletePeer: (peerId: number) => Promise<void>
  toggleEnabled: (peerId: number, enabled: boolean) => Promise<{
    enabled: boolean
    daemonAvailable?: boolean | null
    warning?: string
  }>
  initiatePeer: (peerId: number) => Promise<{
    initiationStatus: string
    initiationMessage: string
    daemonAvailable?: boolean
    warning?: string
  }>
}

export const usePeersStore = create<PeersState>((set) => ({
  peers: [],
  loading: false,
  error: null,

  fetchPeers: async () => {
    const token = useAuthStore.getState().accessToken
    set({ loading: true, error: null })
    try {
      const response = await fetch('/api/v1/peers', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!response.ok) {
        throw new Error(`Failed to load peers (${response.status})`)
      }
      const { data } = (await response.json()) as { data: Peer[] }
      set({ peers: data, loading: false })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message, loading: false })
    }
  },

  createPeer: async (peerData: PeerCreateRequest) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch('/api/v1/peers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(peerData),
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to create peer'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to create peer'
        throw new Error(detail)
      }

      const { data } = (await response.json()) as { data: Peer }
      set((state) => ({
        peers: [...state.peers, data],
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  deletePeer: async (peerId: number) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/peers/${peerId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to delete peer'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to delete peer'
        throw new Error(detail)
      }

      set((state) => ({
        peers: state.peers.filter((p) => p.peerId !== peerId),
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  updatePeer: async (peerId: number, updates: PeerUpdateRequest) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/peers/${peerId}`, {
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
            ? error.detail.detail || 'Failed to update peer'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to update peer'
        throw new Error(detail)
      }

      const { data } = (await response.json()) as { data: Peer }
      set((state) => ({
        peers: state.peers.map((p) => (p.peerId === data.peerId ? data : p)),
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  toggleEnabled: async (peerId: number, enabled: boolean) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/peers/${peerId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled }),
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to update peer'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to update peer'
        throw new Error(detail)
      }

      const { data, meta } = (await response.json()) as {
        data: Peer
        meta?: {
          daemonAvailable?: boolean | null
          warning?: string
        }
      }
      set((state) => ({
        peers: state.peers.map((p) => (p.peerId === data.peerId ? data : p)),
      }))
      return {
        enabled: data.enabled,
        daemonAvailable: meta?.daemonAvailable,
        warning: meta?.warning,
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  initiatePeer: async (peerId: number) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/peers/${peerId}/initiate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Failed to initiate tunnel'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Failed to initiate tunnel'
        throw new Error(detail)
      }

      const body = (await response.json()) as {
        meta?: {
          initiationStatus?: string
          initiationMessage?: string
          daemonAvailable?: boolean
          warning?: string
        }
      }
      const meta = body.meta ?? {}
      const initiationStatus = meta.initiationStatus ?? 'unknown'
      const initiationMessage =
        meta.initiationMessage ?? meta.warning ?? 'Tunnel initiation failed'

      if (initiationStatus !== 'success') {
        throw new Error(initiationMessage)
      }

      // Successful initiation - no state update needed
      // Tunnel status will be updated via WebSocket
      return {
        initiationStatus,
        initiationMessage,
        daemonAvailable: meta.daemonAvailable,
        warning: meta.warning,
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },
}))
