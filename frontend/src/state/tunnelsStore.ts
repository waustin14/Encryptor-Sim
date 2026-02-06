/**
 * Tunnel status state management using Zustand with WebSocket.
 *
 * Manages real-time tunnel status for all peers via WebSocket connection.
 * Auto-reconnects with exponential backoff on disconnect.
 */

import { create } from 'zustand'
import { useAuthStore } from './authStore'
import { useInterfacesStore } from './interfacesStore'
import { usePeersStore } from './peersStore'
import { useRoutesStore } from './routesStore'

export type TunnelStatus = {
  peerId: number
  peerName: string
  status: 'up' | 'down' | 'negotiating' | 'unknown'
  lastUpdated: string
  establishedSec: number
  bytesIn: number
  bytesOut: number
  packetsIn: number
  packetsOut: number
  isPassingTraffic: boolean
  lastTrafficAt: string | null
}

type TunnelsState = {
  tunnelStatus: Record<number, TunnelStatus>
  wsConnection: WebSocket | null
  isConnected: boolean
  reconnectAttempts: number
  _reconnectTimer: ReturnType<typeof setTimeout> | null
  _shouldReconnect: boolean

  connectWebSocket: () => void
  disconnectWebSocket: () => void
  updateTunnelStatus: (
    peerId: number,
    peerName: string,
    status: string,
    timestamp: string,
    telemetry?: {
      establishedSec?: number
      bytesIn?: number
      bytesOut?: number
      packetsIn?: number
      packetsOut?: number
      isPassingTraffic?: boolean
      lastTrafficAt?: string | null
    }
  ) => void
}

const MAX_RECONNECT_DELAY = 30000
const BASE_DELAY = 1000

const buildMonitoringSocketUrl = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const token = useAuthStore.getState().accessToken
  if (!token) {
    return ''
  }
  return `${protocol}://${window.location.host}/api/v1/ws?token=${token}`
}

export const useTunnelsStore = create<TunnelsState>((set, get) => ({
  tunnelStatus: {},
  wsConnection: null,
  isConnected: false,
  reconnectAttempts: 0,
  _reconnectTimer: null,
  _shouldReconnect: true,

  connectWebSocket: () => {
    const url = buildMonitoringSocketUrl()
    if (!url) {
      return
    }

    set({ _shouldReconnect: true })

    const existingTimer = get()._reconnectTimer
    if (existingTimer) {
      clearTimeout(existingTimer)
    }

    // Close existing connection if any
    const existing = get().wsConnection
    if (existing) {
      existing.close()
    }

    const ws = new WebSocket(url)

    ws.onopen = () => {
      set({ isConnected: true, reconnectAttempts: 0, wsConnection: ws })
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string) as {
          type?: string
          data?: Record<string, unknown>
        }

        if (message.type === 'tunnel.status_changed' && message.data) {
          const {
            peerId, peerName, status, timestamp,
            establishedSec, bytesIn, bytesOut,
            packetsIn, packetsOut, isPassingTraffic, lastTrafficAt,
          } = message.data as {
            peerId?: number
            peerName?: string
            status?: string
            timestamp?: string
            establishedSec?: number
            bytesIn?: number
            bytesOut?: number
            packetsIn?: number
            packetsOut?: number
            isPassingTraffic?: boolean
            lastTrafficAt?: string | null
          }
          if (peerId !== undefined && peerName && status && timestamp) {
            get().updateTunnelStatus(peerId, peerName, status, timestamp, {
              establishedSec,
              bytesIn,
              bytesOut,
              packetsIn,
              packetsOut,
              isPassingTraffic,
              lastTrafficAt,
            })
          }
        }

        if (message.type === 'interface.stats_updated' && message.data) {
          const data = message.data as {
            interface?: string
            bytesRx?: number; bytesTx?: number
            packetsRx?: number; packetsTx?: number
            errorsRx?: number; errorsTx?: number
            timestamp?: string
          }
          if (data.interface && data.timestamp) {
            useInterfacesStore.getState().updateInterfaceStats(data.interface, {
              bytesRx: data.bytesRx ?? 0,
              bytesTx: data.bytesTx ?? 0,
              packetsRx: data.packetsRx ?? 0,
              packetsTx: data.packetsTx ?? 0,
              errorsRx: data.errorsRx ?? 0,
              errorsTx: data.errorsTx ?? 0,
              timestamp: data.timestamp,
            })
          }
        }

        // Config-change events: re-fetch store data when REST mutations occur
        if (message.type === 'peer.config_changed') {
          usePeersStore.getState().fetchPeers()
        }
        if (message.type === 'route.config_changed') {
          useRoutesStore.getState().fetchRoutes()
        }
        if (message.type === 'interface.config_changed') {
          useInterfacesStore.getState().fetchInterfaces()
        }
      } catch {
        // Ignore malformed payloads
      }
    }

    ws.onerror = () => {
      // Error handling is done in onclose
    }

    ws.onclose = () => {
      set({ isConnected: false, wsConnection: null })
      if (!get()._shouldReconnect) {
        return
      }

      // Auto-reconnect with exponential backoff
      const attempts = get().reconnectAttempts
      const delay = Math.min(BASE_DELAY * Math.pow(2, attempts), MAX_RECONNECT_DELAY)

      const timer = setTimeout(() => {
        set({ reconnectAttempts: attempts + 1 })
        get().connectWebSocket()
      }, delay)

      set({ _reconnectTimer: timer })
    }
  },

  disconnectWebSocket: () => {
    set({ _shouldReconnect: false })
    const timer = get()._reconnectTimer
    if (timer) {
      clearTimeout(timer)
    }

    const ws = get().wsConnection
    if (ws) {
      ws.close()
    }
    set({
      wsConnection: null,
      isConnected: false,
      _reconnectTimer: null,
      reconnectAttempts: 0,
    })
  },

  updateTunnelStatus: (
    peerId: number,
    peerName: string,
    status: string,
    timestamp: string,
    telemetry?: {
      establishedSec?: number
      bytesIn?: number
      bytesOut?: number
      packetsIn?: number
      packetsOut?: number
      isPassingTraffic?: boolean
      lastTrafficAt?: string | null
    }
  ) => {
    set((state) => ({
      tunnelStatus: {
        ...state.tunnelStatus,
        [peerId]: {
          peerId,
          peerName,
          status: status as TunnelStatus['status'],
          lastUpdated: timestamp,
          establishedSec: telemetry?.establishedSec ?? 0,
          bytesIn: telemetry?.bytesIn ?? 0,
          bytesOut: telemetry?.bytesOut ?? 0,
          packetsIn: telemetry?.packetsIn ?? 0,
          packetsOut: telemetry?.packetsOut ?? 0,
          isPassingTraffic: telemetry?.isPassingTraffic ?? false,
          lastTrafficAt: telemetry?.lastTrafficAt ?? null,
        },
      },
    }))
  },
}))
