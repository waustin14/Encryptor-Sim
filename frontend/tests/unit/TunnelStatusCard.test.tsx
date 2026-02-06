import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { TunnelStatusCard } from '../../src/components/TunnelStatusCard'
import type { TunnelStatus } from '../../src/state/tunnelsStore'

describe('TunnelStatusCard', () => {
  const baseProps: TunnelStatus = {
    peerId: 1,
    peerName: 'site-a',
    status: 'up',
    lastUpdated: '2026-02-04T12:00:00Z',
    establishedSec: 0,
    bytesIn: 0,
    bytesOut: 0,
    packetsIn: 0,
    packetsOut: 0,
    isPassingTraffic: false,
    lastTrafficAt: null,
  }

  const renderCard = (tunnel: TunnelStatus) => {
    return render(
      <ChakraProvider value={defaultSystem}>
        <TunnelStatusCard tunnel={tunnel} />
      </ChakraProvider>,
    )
  }

  it('renders peer name', () => {
    renderCard(baseProps)
    expect(screen.getByText('site-a')).not.toBeNull()
  })

  it('displays status badge with correct label', () => {
    renderCard(baseProps)
    const badge = screen.getByTestId('tunnel-status-site-a')
    expect(badge.textContent).toContain('Up')
  })

  it('shows different status colors for each state', () => {
    const statuses: Array<{ status: TunnelStatus['status']; label: string }> = [
      { status: 'up', label: 'Up' },
      { status: 'down', label: 'Down' },
      { status: 'negotiating', label: 'Negotiating' },
      { status: 'unknown', label: 'Unknown' },
    ]

    statuses.forEach(({ status, label }) => {
      const props = { ...baseProps, status, peerName: `peer-${status}` }
      const { unmount } = renderCard(props)
      expect(screen.getByTestId(`tunnel-status-peer-${status}`).textContent).toContain(label)
      unmount()
    })
  })

  describe('telemetry display (Story 5.4)', () => {
    it('shows establishment time for up tunnel (AC: #2)', () => {
      const props = { ...baseProps, status: 'up' as const, establishedSec: 3600 }
      renderCard(props)
      expect(screen.getByTestId('tunnel-established').textContent).toContain('Established: 1h')
    })

    it('formats duration as hours and minutes', () => {
      const props = { ...baseProps, status: 'up' as const, establishedSec: 5430 } // 1h 30m 30s
      renderCard(props)
      expect(screen.getByTestId('tunnel-established').textContent).toContain('Established: 1h 30m')
    })

    it('formats duration as minutes and seconds', () => {
      const props = { ...baseProps, status: 'up' as const, establishedSec: 125 } // 2m 5s
      renderCard(props)
      expect(screen.getByTestId('tunnel-established').textContent).toContain('Established: 2m 5s')
    })

    it('formats duration as seconds only', () => {
      const props = { ...baseProps, status: 'up' as const, establishedSec: 45 }
      renderCard(props)
      expect(screen.getByTestId('tunnel-established').textContent).toContain('Established: 45s')
    })

    it('shows "Passing Traffic" indicator when traffic detected (AC: #1, #4)', () => {
      const props = { ...baseProps, status: 'up' as const, isPassingTraffic: true }
      renderCard(props)
      expect(screen.getByTestId('tunnel-traffic-indicator').textContent).toContain('Passing Traffic')
    })

    it('shows "Idle" indicator when no traffic (AC: #1, #4)', () => {
      const props = { ...baseProps, status: 'up' as const, isPassingTraffic: false }
      renderCard(props)
      expect(screen.getByTestId('tunnel-traffic-indicator').textContent).toContain('Idle')
    })

    it('hides telemetry for down tunnels (AC: #8, Task 3.4)', () => {
      const props = {
        ...baseProps,
        status: 'down' as const,
        establishedSec: 3600,
        isPassingTraffic: true,
      }
      renderCard(props)
      expect(screen.queryByTestId('tunnel-established')).toBeNull()
      expect(screen.queryByTestId('tunnel-traffic-indicator')).toBeNull()
    })

    it('hides telemetry for negotiating tunnels (AC: #8, Task 3.4)', () => {
      const props = {
        ...baseProps,
        status: 'negotiating' as const,
        establishedSec: 100,
        isPassingTraffic: false,
      }
      renderCard(props)
      expect(screen.queryByTestId('tunnel-established')).toBeNull()
      expect(screen.queryByTestId('tunnel-traffic-indicator')).toBeNull()
    })

    it('hides telemetry for unknown tunnels (AC: #8, Task 3.4)', () => {
      const props = {
        ...baseProps,
        status: 'unknown' as const,
        establishedSec: 100,
      }
      renderCard(props)
      expect(screen.queryByTestId('tunnel-established')).toBeNull()
      expect(screen.queryByTestId('tunnel-traffic-indicator')).toBeNull()
    })

    it('hides establishment time when establishedSec is 0', () => {
      const props = { ...baseProps, status: 'up' as const, establishedSec: 0 }
      renderCard(props)
      expect(screen.queryByTestId('tunnel-established')).toBeNull()
    })

    it('still shows traffic indicator even when established time is 0', () => {
      const props = { ...baseProps, status: 'up' as const, establishedSec: 0, isPassingTraffic: false }
      renderCard(props)
      expect(screen.getByTestId('tunnel-traffic-indicator')).not.toBeNull()
    })
  })

  it('shows last updated timestamp', () => {
    renderCard(baseProps)
    expect(screen.getByText(/Last updated:/)).not.toBeNull()
  })
})
