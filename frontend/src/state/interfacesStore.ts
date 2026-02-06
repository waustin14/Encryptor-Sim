/**
 * Interface configuration state management using Zustand.
 *
 * Manages CT, PT, and MGMT interface configurations.
 */

import { create } from 'zustand'
import { useAuthStore } from './authStore'

export type InterfaceConfig = {
  interfaceId: number
  name: string
  ipAddress: string | null
  netmask: string | null
  gateway: string | null
  namespace: string
  device: string
}

export type InterfaceStats = {
  bytesRx: number
  bytesTx: number
  packetsRx: number
  packetsTx: number
  errorsRx: number
  errorsTx: number
  timestamp: string
}

type InterfacesState = {
  interfaces: InterfaceConfig[]
  interfaceStats: Record<string, InterfaceStats>
  loading: boolean
  error: string | null
  fetchInterfaces: () => Promise<void>
  updateInterface: (name: string, config: { ipAddress: string; netmask: string; gateway: string }) => Promise<void>
  updateInterfaceStats: (interfaceName: string, stats: InterfaceStats) => void
}

export const useInterfacesStore = create<InterfacesState>((set) => ({
  interfaces: [],
  interfaceStats: {},
  loading: false,
  error: null,

  fetchInterfaces: async () => {
    const token = useAuthStore.getState().accessToken
    set({ loading: true, error: null })
    try {
      const response = await fetch('/api/v1/interfaces', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (!response.ok) {
        throw new Error(`Failed to load interfaces (${response.status})`)
      }
      const { data } = (await response.json()) as { data: InterfaceConfig[] }
      set({ interfaces: data, loading: false })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message, loading: false })
    }
  },

  updateInterface: async (name: string, config: { ipAddress: string; netmask: string; gateway: string }) => {
    const token = useAuthStore.getState().accessToken
    set({ error: null })
    try {
      const response = await fetch(`/api/v1/interfaces/${name}/configure`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(config),
      })

      if (!response.ok) {
        const error = await response.json()
        const detail =
          typeof error.detail === 'object' && error.detail !== null
            ? error.detail.detail || 'Configuration failed'
            : typeof error.detail === 'string'
              ? error.detail
              : 'Configuration failed'
        throw new Error(detail)
      }

      const { data } = (await response.json()) as { data: InterfaceConfig }
      set((state) => ({
        interfaces: state.interfaces.map((iface) =>
          iface.name === data.name ? data : iface
        ),
      }))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message })
      throw error
    }
  },

  updateInterfaceStats: (interfaceName: string, stats: InterfaceStats) => {
    set((state) => ({
      interfaceStats: {
        ...state.interfaceStats,
        [interfaceName]: stats,
      },
    }))
  },
}))
