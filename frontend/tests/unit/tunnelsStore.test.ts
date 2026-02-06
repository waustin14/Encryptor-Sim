import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useTunnelsStore } from '../../src/state/tunnelsStore'
import { useAuthStore } from '../../src/state/authStore'
import { useInterfacesStore } from '../../src/state/interfacesStore'
import { usePeersStore } from '../../src/state/peersStore'
import { useRoutesStore } from '../../src/state/routesStore'

// Capture WebSocket instances created by the store
let createdWs: {
  onopen: (() => void) | null
  onmessage: ((event: { data: string }) => void) | null
  onerror: (() => void) | null
  onclose: (() => void) | null
  close: ReturnType<typeof vi.fn>
  url: string
} | null = null

// Mock window.location for WebSocket URL construction
Object.defineProperty(globalThis, 'window', {
  value: {
    location: {
      protocol: 'http:',
      host: 'localhost:8000',
    },
  },
  writable: true,
})

vi.stubGlobal(
  'WebSocket',
  vi.fn().mockImplementation(function (this: unknown, url: string) {
    createdWs = {
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      close: vi.fn(),
      url,
    }
    return createdWs
  }),
)

describe('tunnelsStore', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    useTunnelsStore.setState({
      tunnelStatus: {},
      wsConnection: null,
      isConnected: false,
      reconnectAttempts: 0,
      _reconnectTimer: null,
      _shouldReconnect: true,
    })
    useAuthStore.setState({ accessToken: 'mock-jwt-token' })
    useInterfacesStore.setState({ interfaceStats: {} })
    createdWs = null
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('updateTunnelStatus', () => {
    it('adds new tunnel status entry', () => {
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'up', '2026-02-04T12:00:00Z')

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status).toBeDefined()
      expect(status.peerId).toBe(1)
      expect(status.peerName).toBe('site-a')
      expect(status.status).toBe('up')
      expect(status.lastUpdated).toBe('2026-02-04T12:00:00Z')
    })

    it('updates existing tunnel status', () => {
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'up', '2026-02-04T12:00:00Z')
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'down', '2026-02-04T12:00:02Z')

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.status).toBe('down')
      expect(status.lastUpdated).toBe('2026-02-04T12:00:02Z')
    })

    it('tracks multiple peers independently', () => {
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'up', '2026-02-04T12:00:00Z')
      useTunnelsStore.getState().updateTunnelStatus(2, 'site-b', 'negotiating', '2026-02-04T12:00:01Z')

      const state = useTunnelsStore.getState().tunnelStatus
      expect(state[1].status).toBe('up')
      expect(state[2].status).toBe('negotiating')
    })

    it('accepts all valid status values', () => {
      const statuses = ['up', 'down', 'negotiating', 'unknown'] as const
      statuses.forEach((status, index) => {
        useTunnelsStore.getState().updateTunnelStatus(index + 1, `peer-${status}`, status, '2026-02-04T12:00:00Z')
      })

      const state = useTunnelsStore.getState().tunnelStatus
      expect(state[1].status).toBe('up')
      expect(state[2].status).toBe('down')
      expect(state[3].status).toBe('negotiating')
      expect(state[4].status).toBe('unknown')
    })

    it('stores telemetry fields when provided (Story 5.4, AC: #1-3)', () => {
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'up', '2026-02-04T12:00:00Z', {
        establishedSec: 3600,
        bytesIn: 10240,
        bytesOut: 20480,
        packetsIn: 100,
        packetsOut: 200,
        isPassingTraffic: true,
        lastTrafficAt: '2026-02-04T11:55:00Z',
      })

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.establishedSec).toBe(3600)
      expect(status.bytesIn).toBe(10240)
      expect(status.bytesOut).toBe(20480)
      expect(status.packetsIn).toBe(100)
      expect(status.packetsOut).toBe(200)
      expect(status.isPassingTraffic).toBe(true)
      expect(status.lastTrafficAt).toBe('2026-02-04T11:55:00Z')
    })

    it('defaults telemetry fields safely when not provided (Story 5.4, AC: #8)', () => {
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'up', '2026-02-04T12:00:00Z')

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.establishedSec).toBe(0)
      expect(status.bytesIn).toBe(0)
      expect(status.bytesOut).toBe(0)
      expect(status.packetsIn).toBe(0)
      expect(status.packetsOut).toBe(0)
      expect(status.isPassingTraffic).toBe(false)
      expect(status.lastTrafficAt).toBeNull()
    })

    it('defaults individual missing telemetry fields (Story 5.4, AC: #8)', () => {
      useTunnelsStore.getState().updateTunnelStatus(1, 'site-a', 'up', '2026-02-04T12:00:00Z', {
        establishedSec: 100,
        // Other fields omitted
      })

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.establishedSec).toBe(100)
      expect(status.bytesIn).toBe(0)
      expect(status.isPassingTraffic).toBe(false)
    })
  })

  describe('connectWebSocket', () => {
    it('does nothing without an access token', () => {
      useAuthStore.setState({ accessToken: null })
      useTunnelsStore.getState().connectWebSocket()
      expect(createdWs).toBeNull()
      expect(useTunnelsStore.getState().isConnected).toBe(false)
    })

    it('creates WebSocket connection with token', () => {
      useTunnelsStore.getState().connectWebSocket()
      expect(createdWs).not.toBeNull()
      expect(createdWs!.url).toContain('token=mock-jwt-token')
    })

    it('sets isConnected on open', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()
      expect(useTunnelsStore.getState().isConnected).toBe(true)
    })

    it('resets reconnect attempts on successful connect', () => {
      useTunnelsStore.setState({ reconnectAttempts: 5 })
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(0)
    })
  })

  describe('disconnectWebSocket', () => {
    it('sets isConnected to false', () => {
      useTunnelsStore.setState({ isConnected: true })
      useTunnelsStore.getState().disconnectWebSocket()
      expect(useTunnelsStore.getState().isConnected).toBe(false)
    })

    it('resets reconnect attempts', () => {
      useTunnelsStore.setState({ reconnectAttempts: 3 })
      useTunnelsStore.getState().disconnectWebSocket()
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(0)
    })

    it('calls close on existing connection', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.() // Must open so wsConnection is stored
      const ws = createdWs
      useTunnelsStore.getState().disconnectWebSocket()
      expect(ws?.close).toHaveBeenCalled()
    })
  })

  describe('WebSocket event handling', () => {
    it('updates tunnel status on tunnel.status_changed event', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'tunnel.status_changed',
          data: {
            peerId: 1,
            peerName: 'site-a',
            status: 'up',
            timestamp: '2026-02-04T12:00:00Z',
          },
        }),
      })

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.status).toBe('up')
    })

    it('parses telemetry fields from WebSocket event (Story 5.4, AC: #5, #6)', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'tunnel.status_changed',
          data: {
            peerId: 1,
            peerName: 'site-a',
            status: 'up',
            timestamp: '2026-02-04T12:00:00Z',
            establishedSec: 7200,
            bytesIn: 51200,
            bytesOut: 102400,
            packetsIn: 500,
            packetsOut: 1000,
            isPassingTraffic: true,
            lastTrafficAt: '2026-02-04T11:58:00Z',
          },
        }),
      })

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.establishedSec).toBe(7200)
      expect(status.bytesIn).toBe(51200)
      expect(status.bytesOut).toBe(102400)
      expect(status.packetsIn).toBe(500)
      expect(status.packetsOut).toBe(1000)
      expect(status.isPassingTraffic).toBe(true)
      expect(status.lastTrafficAt).toBe('2026-02-04T11:58:00Z')
    })

    it('maintains backward compatibility with events missing telemetry (Story 5.4, AC: #7)', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      // Event without telemetry fields (legacy format)
      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'tunnel.status_changed',
          data: {
            peerId: 1,
            peerName: 'site-a',
            status: 'up',
            timestamp: '2026-02-04T12:00:00Z',
          },
        }),
      })

      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.status).toBe('up')
      expect(status.peerName).toBe('site-a')
      // Telemetry should default safely
      expect(status.establishedSec).toBe(0)
      expect(status.isPassingTraffic).toBe(false)
    })

    it('routes interface.stats_updated to interfacesStore', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'interface.stats_updated',
          data: {
            interface: 'CT',
            bytesRx: 100,
            bytesTx: 200,
            packetsRx: 10,
            packetsTx: 20,
            errorsRx: 0,
            errorsTx: 0,
            timestamp: '2026-02-04T12:00:00Z',
          },
        }),
      })

      // Should not add to tunnel status
      expect(Object.keys(useTunnelsStore.getState().tunnelStatus)).toHaveLength(0)

      // Should update interfaces store
      const stats = useInterfacesStore.getState().interfaceStats['CT']
      expect(stats).toBeDefined()
      expect(stats.bytesRx).toBe(100)
      expect(stats.bytesTx).toBe(200)
      expect(stats.timestamp).toBe('2026-02-04T12:00:00Z')
    })

    it('ignores unknown event types', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'unknown.event',
          data: { foo: 'bar' },
        }),
      })

      expect(Object.keys(useTunnelsStore.getState().tunnelStatus)).toHaveLength(0)
      expect(Object.keys(useInterfacesStore.getState().interfaceStats)).toHaveLength(0)
    })

    it('ignores malformed messages', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({ data: 'not-json' })

      expect(Object.keys(useTunnelsStore.getState().tunnelStatus)).toHaveLength(0)
    })

    it('triggers peers re-fetch on peer.config_changed event (Story 5.5, AC: #6)', () => {
      const fetchPeersSpy = vi.fn()
      usePeersStore.setState({ fetchPeers: fetchPeersSpy } as unknown as Parameters<typeof usePeersStore.setState>[0])

      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'peer.config_changed',
          data: { action: 'created', peerId: 1 },
        }),
      })

      expect(fetchPeersSpy).toHaveBeenCalledTimes(1)
    })

    it('triggers routes re-fetch on route.config_changed event (Story 5.5, AC: #6)', () => {
      const fetchRoutesSpy = vi.fn()
      useRoutesStore.setState({ fetchRoutes: fetchRoutesSpy } as unknown as Parameters<typeof useRoutesStore.setState>[0])

      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'route.config_changed',
          data: { action: 'deleted', routeId: 5, peerId: 1 },
        }),
      })

      expect(fetchRoutesSpy).toHaveBeenCalledTimes(1)
    })

    it('triggers interfaces re-fetch on interface.config_changed event (Story 5.5, AC: #6)', () => {
      const fetchInterfacesSpy = vi.fn()
      useInterfacesStore.setState({ fetchInterfaces: fetchInterfacesSpy } as unknown as Parameters<typeof useInterfacesStore.setState>[0])

      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'interface.config_changed',
          data: { action: 'updated', interface: 'ct' },
        }),
      })

      expect(fetchInterfacesSpy).toHaveBeenCalledTimes(1)
    })

    it('preserves tunnel.status_changed handling alongside config events (Story 5.5, AC: #8)', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()

      // Receive a config event followed by a status event
      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'peer.config_changed',
          data: { action: 'created', peerId: 1 },
        }),
      })

      createdWs?.onmessage?.({
        data: JSON.stringify({
          type: 'tunnel.status_changed',
          data: {
            peerId: 1,
            peerName: 'site-a',
            status: 'up',
            timestamp: '2026-02-04T12:00:00Z',
          },
        }),
      })

      // Status event should still be processed
      const status = useTunnelsStore.getState().tunnelStatus[1]
      expect(status.status).toBe('up')
    })
  })

  describe('auto-reconnect', () => {
    it('sets isConnected to false on close', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()
      createdWs?.onclose?.()

      expect(useTunnelsStore.getState().isConnected).toBe(false)
    })

    it('increments reconnect attempts after delay', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()
      createdWs?.onclose?.()

      // Advance timer to trigger reconnect (base delay = 1000ms for attempt 0)
      vi.advanceTimersByTime(1000)
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(1)
    })

    it('uses exponential backoff delay', () => {
      // Don't call onopen - set reconnectAttempts directly to simulate
      // a scenario where attempts have accumulated
      useTunnelsStore.getState().connectWebSocket()
      useTunnelsStore.setState({ reconnectAttempts: 3 })
      createdWs?.onclose?.()

      // With 3 attempts, delay = min(1000 * 2^3, 30000) = 8000ms
      vi.advanceTimersByTime(7999)
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(3) // Not yet

      vi.advanceTimersByTime(1)
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(4) // Now
    })

    it('caps backoff at 30 seconds', () => {
      useTunnelsStore.getState().connectWebSocket()
      useTunnelsStore.setState({ reconnectAttempts: 10 })
      createdWs?.onclose?.()

      // With 10 attempts, delay = min(1000 * 2^10, 30000) = 30000ms
      vi.advanceTimersByTime(30000)
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(11)
    })

    it('clears reconnect timer on disconnect', () => {
      useTunnelsStore.getState().connectWebSocket()
      createdWs?.onopen?.()
      createdWs?.onclose?.()

      // Disconnect before timer fires
      useTunnelsStore.getState().disconnectWebSocket()

      // Advancing timer should not change attempts
      vi.advanceTimersByTime(60000)
      expect(useTunnelsStore.getState().reconnectAttempts).toBe(0)
    })
  })
})
