/**
 * Unit tests for DashboardPage component.
 *
 * Tests tunnel status display, interface statistics, and WebSocket connection indicator.
 */

import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DashboardPage } from '../../src/pages/DashboardPage'
import { useAuthStore } from '../../src/state/authStore'
import { useInterfacesStore } from '../../src/state/interfacesStore'
import { useSystemStatusStore } from '../../src/state/systemStatus'
import { useTunnelsStore } from '../../src/state/tunnelsStore'

// Mock stores
vi.mock('../../src/state/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../../src/state/systemStatus', () => ({
  useSystemStatusStore: vi.fn(),
}))

vi.mock('../../src/state/tunnelsStore', () => ({
  useTunnelsStore: vi.fn(),
}))

vi.mock('../../src/state/interfacesStore', () => ({
  useInterfacesStore: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('DashboardPage', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.clearAllMocks()

    vi.mocked(useAuthStore).mockReturnValue({
      logout: vi.fn(),
      user: { username: 'admin', userId: 1, requirePasswordChange: false },
    } as ReturnType<typeof useAuthStore>)

    vi.mocked(useSystemStatusStore).mockReturnValue({
      isolationStatus: null,
      isLoading: false,
      error: null,
      loadIsolationStatus: vi.fn(),
      connectIsolationStatusSocket: vi.fn(() => vi.fn()),
    } as unknown as ReturnType<typeof useSystemStatusStore>)

    vi.mocked(useTunnelsStore).mockReturnValue({
      tunnelStatus: {},
      isConnected: false,
      connectWebSocket: vi.fn(),
      disconnectWebSocket: vi.fn(),
    } as unknown as ReturnType<typeof useTunnelsStore>)

    vi.mocked(useInterfacesStore).mockReturnValue({
      interfaceStats: {},
    } as unknown as ReturnType<typeof useInterfacesStore>)
  })

  const renderDashboard = () => {
    return render(
      <ChakraProvider value={defaultSystem}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </ChakraProvider>,
    )
  }

  describe('WebSocket connection indicator', () => {
    it('shows Disconnected badge when WebSocket is not connected', () => {
      renderDashboard()

      const badge = screen.getByTestId('ws-connection-status')
      expect(badge.textContent).toBe('Disconnected')
    })

    it('shows Live badge when WebSocket is connected', () => {
      vi.mocked(useTunnelsStore).mockReturnValue({
        tunnelStatus: {},
        isConnected: true,
        connectWebSocket: vi.fn(),
        disconnectWebSocket: vi.fn(),
      } as unknown as ReturnType<typeof useTunnelsStore>)

      renderDashboard()

      const badge = screen.getByTestId('ws-connection-status')
      expect(badge.textContent).toBe('Live')
    })
  })

  describe('Tunnel status section', () => {
    it('shows empty state when no tunnels', () => {
      renderDashboard()

      expect(screen.getByText('No tunnel status available')).toBeTruthy()
      expect(screen.getByText('Configure peers to see tunnel status')).toBeTruthy()
    })

    it('shows tunnel count', () => {
      vi.mocked(useTunnelsStore).mockReturnValue({
        tunnelStatus: {
          1: { peerId: 1, peerName: 'site-a', status: 'up', lastUpdated: '2026-02-04T12:00:00Z' },
          2: { peerId: 2, peerName: 'site-b', status: 'down', lastUpdated: '2026-02-04T12:00:00Z' },
        },
        isConnected: true,
        connectWebSocket: vi.fn(),
        disconnectWebSocket: vi.fn(),
      } as unknown as ReturnType<typeof useTunnelsStore>)

      renderDashboard()

      expect(screen.getByText('2 peers')).toBeTruthy()
    })

    it('displays tunnel status cards for each peer', () => {
      vi.mocked(useTunnelsStore).mockReturnValue({
        tunnelStatus: {
          1: { peerId: 1, peerName: 'site-a', status: 'up', lastUpdated: '2026-02-04T12:00:00Z' },
          2: { peerId: 2, peerName: 'site-b', status: 'negotiating', lastUpdated: '2026-02-04T12:00:01Z' },
        },
        isConnected: true,
        connectWebSocket: vi.fn(),
        disconnectWebSocket: vi.fn(),
      } as unknown as ReturnType<typeof useTunnelsStore>)

      renderDashboard()

      expect(screen.getByText('site-a')).toBeTruthy()
      expect(screen.getByText('site-b')).toBeTruthy()
      expect(screen.getByTestId('tunnel-status-site-a').textContent).toBe('Up')
      expect(screen.getByTestId('tunnel-status-site-b').textContent).toBe('Negotiating')
    })
  })

  describe('Interface statistics section', () => {
    it('shows empty state when no stats', () => {
      renderDashboard()

      expect(screen.getByText('No interface statistics available')).toBeTruthy()
      expect(screen.getByText('Statistics will appear once WebSocket connects')).toBeTruthy()
    })

    it('displays interface stats cards', () => {
      vi.mocked(useInterfacesStore).mockReturnValue({
        interfaceStats: {
          CT: {
            bytesRx: 1024,
            bytesTx: 2048,
            packetsRx: 10,
            packetsTx: 20,
            errorsRx: 0,
            errorsTx: 0,
            timestamp: '2026-02-04T12:00:00Z',
          },
          PT: {
            bytesRx: 1048576,
            bytesTx: 2097152,
            packetsRx: 1000,
            packetsTx: 2000,
            errorsRx: 1,
            errorsTx: 0,
            timestamp: '2026-02-04T12:00:00Z',
          },
        },
      } as unknown as ReturnType<typeof useInterfacesStore>)

      renderDashboard()

      expect(screen.getByText('Ciphertext (CT)')).toBeTruthy()
      expect(screen.getByText('Plaintext (PT)')).toBeTruthy()
    })

    it('formats bytes in human-readable format', () => {
      vi.mocked(useInterfacesStore).mockReturnValue({
        interfaceStats: {
          CT: {
            bytesRx: 1536,
            bytesTx: 1048576,
            packetsRx: 10,
            packetsTx: 20,
            errorsRx: 0,
            errorsTx: 0,
            timestamp: '2026-02-04T12:00:00Z',
          },
        },
      } as unknown as ReturnType<typeof useInterfacesStore>)

      renderDashboard()

      // Find the stats element - there should be exactly one CT stats card
      const bytesDisplay = screen.getByTestId('stats-CT-bytes')
      expect(bytesDisplay.textContent).toContain('1.5 KB')
      expect(bytesDisplay.textContent).toContain('1.0 MB')
    })
  })

  describe('WebSocket lifecycle', () => {
    it('connects WebSocket on mount', () => {
      const connectWebSocket = vi.fn()
      vi.mocked(useTunnelsStore).mockReturnValue({
        tunnelStatus: {},
        isConnected: false,
        connectWebSocket,
        disconnectWebSocket: vi.fn(),
      } as unknown as ReturnType<typeof useTunnelsStore>)

      renderDashboard()

      expect(connectWebSocket).toHaveBeenCalled()
    })

    it('disconnects WebSocket on unmount', () => {
      const disconnectWebSocket = vi.fn()
      vi.mocked(useTunnelsStore).mockReturnValue({
        tunnelStatus: {},
        isConnected: false,
        connectWebSocket: vi.fn(),
        disconnectWebSocket,
      } as unknown as ReturnType<typeof useTunnelsStore>)

      const { unmount } = renderDashboard()
      unmount()

      expect(disconnectWebSocket).toHaveBeenCalled()
    })
  })
})
