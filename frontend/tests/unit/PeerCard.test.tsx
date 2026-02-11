/**
 * Unit tests for PeerCard delete functionality (Story 4.3, Task 5).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'

import { PeerCard } from '../../src/components/PeerCard'
import type { Peer } from '../../src/state/peersStore'

const MOCK_PEER: Peer = {
  peerId: 1,
  name: 'test-peer',
  remoteIp: '10.1.1.100',
  ikeVersion: 'ikev2',
  enabled: true,
  dpdAction: 'restart',
  dpdDelay: 30,
  dpdTimeout: 150,
  rekeyTime: 3600,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
  operationalStatus: 'ready',
}

function renderCard(props?: {
  onDelete?: (id: number) => Promise<void>
  onEdit?: (id: number) => void
  onInitiate?: (id: number) => Promise<void>
  onToggleEnabled?: (id: number, enabled: boolean) => Promise<void>
  peer?: Peer
}) {
  const onEdit = props?.onEdit ?? vi.fn()
  const onDelete = props?.onDelete ?? vi.fn().mockResolvedValue(undefined)
  const onInitiate = props?.onInitiate ?? vi.fn().mockResolvedValue(undefined)
  const onToggleEnabled = props?.onToggleEnabled ?? vi.fn().mockResolvedValue(undefined)
  const peer = props?.peer ?? MOCK_PEER

  return render(
    <ChakraProvider value={defaultSystem}>
      <PeerCard
        peer={peer}
        onEdit={onEdit}
        onDelete={onDelete}
        onInitiate={onInitiate}
        onToggleEnabled={onToggleEnabled}
      />
    </ChakraProvider>,
  )
}

async function openActionsMenu() {
  fireEvent.click(screen.getByTestId('peer-actions-menu'))
  await waitFor(() => {
    expect(screen.getByTestId('delete-button')).toBeTruthy()
  })
}

describe('PeerCard', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders peer name and details', () => {
    renderCard()

    expect(screen.getByText('test-peer')).toBeTruthy()
    expect(screen.getByText('IKEV2')).toBeTruthy()
  })

  it('renders actions menu trigger', () => {
    renderCard()

    expect(screen.getByTestId('peer-actions-menu')).toBeTruthy()
  })

  it('shows delete option in actions menu', async () => {
    renderCard()

    await openActionsMenu()

    expect(screen.getByTestId('delete-button')).toBeTruthy()
  })

  it('shows confirmation dialog on delete click', async () => {
    renderCard()

    await openActionsMenu()
    fireEvent.click(screen.getByTestId('delete-button'))

    expect(screen.getByText(/Delete peer "test-peer"\? This cannot be undone\./)).toBeTruthy()
    expect(screen.getByLabelText('Confirm delete')).toBeTruthy()
    expect(screen.getByLabelText('Cancel delete')).toBeTruthy()
  })

  it('calls onDelete when confirmed', async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined)
    renderCard({ onDelete })

    await openActionsMenu()
    fireEvent.click(screen.getByTestId('delete-button'))
    fireEvent.click(screen.getByLabelText('Confirm delete'))

    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith(1)
    })
  })

  it('hides confirmation when cancel is clicked', async () => {
    renderCard()

    await openActionsMenu()
    fireEvent.click(screen.getByTestId('delete-button'))
    expect(screen.getByLabelText('Confirm delete')).toBeTruthy()

    fireEvent.click(screen.getByLabelText('Cancel delete'))
    expect(screen.queryByLabelText('Confirm delete')).toBeNull()
  })

  it('does not call onEdit when delete button is clicked', async () => {
    const onEdit = vi.fn()
    renderCard({ onEdit })

    await openActionsMenu()
    fireEvent.click(screen.getByTestId('delete-button'))

    expect(onEdit).not.toHaveBeenCalled()
  })

  it('shows error message when delete fails', async () => {
    const onDelete = vi.fn().mockRejectedValue(new Error('Network error'))
    renderCard({ onDelete })

    await openActionsMenu()
    fireEvent.click(screen.getByTestId('delete-button'))
    fireEvent.click(screen.getByLabelText('Confirm delete'))

    await waitFor(() => {
      expect(screen.getByText(/Error: Network error/)).toBeTruthy()
    })

    // Confirmation dialog should still be visible after error
    expect(screen.getByLabelText('Confirm delete')).toBeTruthy()
  })

  it('displays Ready badge when operationalStatus is ready', () => {
    renderCard()

    const badge = screen.getByTestId('operational-status-badge')
    expect(badge).toBeTruthy()
    expect(badge.textContent).toBe('Ready')
  })

  it('displays Incomplete badge when operationalStatus is incomplete', () => {
    const incompletePeer: Peer = { ...MOCK_PEER, operationalStatus: 'incomplete' }
    renderCard({ peer: incompletePeer })

    const badge = screen.getByTestId('operational-status-badge')
    expect(badge).toBeTruthy()
    expect(badge.textContent).toBe('Incomplete')
  })

  it('shows warning message for incomplete peers', () => {
    const incompletePeer: Peer = { ...MOCK_PEER, operationalStatus: 'incomplete' }
    renderCard({ peer: incompletePeer })

    const warning = screen.getByTestId('incomplete-warning')
    expect(warning).toBeTruthy()
    expect(warning.textContent).toContain('incomplete')
  })

  it('does not show warning message for ready peers', () => {
    renderCard()

    expect(screen.queryByTestId('incomplete-warning')).toBeNull()
  })

  describe('Initiate Tunnel Button', () => {
    it('renders initiate button in menu', async () => {
      renderCard()

      await openActionsMenu()

      expect(screen.getByTestId('initiate-button')).toBeTruthy()
    })

    it('calls onInitiate when clicked', async () => {
      const onInitiate = vi.fn().mockResolvedValue(undefined)
      renderCard({ onInitiate })

      await openActionsMenu()
      fireEvent.click(screen.getByTestId('initiate-button'))

      await waitFor(() => {
        expect(onInitiate).toHaveBeenCalledWith(1)
      })
    })

    it('does not call onEdit when initiate button is clicked', async () => {
      const onEdit = vi.fn()
      renderCard({ onEdit })

      await openActionsMenu()
      fireEvent.click(screen.getByTestId('initiate-button'))

      expect(onEdit).not.toHaveBeenCalled()
    })
  })

  describe('Enable / Disable', () => {
    it('shows disabled badge when peer is disabled', () => {
      const disabledPeer: Peer = { ...MOCK_PEER, enabled: false }
      renderCard({ peer: disabledPeer })

      expect(screen.getByTestId('disabled-badge')).toBeTruthy()
    })

    it('shows disable confirmation before disabling', async () => {
      renderCard()

      await openActionsMenu()
      fireEvent.click(screen.getByTestId('toggle-enabled-button'))

      expect(screen.getByTestId('disable-confirmation')).toBeTruthy()
      expect(screen.getByTestId('confirm-disable-button')).toBeTruthy()
    })

    it('calls onToggleEnabled(false) after disable confirmation', async () => {
      const onToggleEnabled = vi.fn().mockResolvedValue(undefined)
      renderCard({ onToggleEnabled })

      await openActionsMenu()
      fireEvent.click(screen.getByTestId('toggle-enabled-button'))
      fireEvent.click(screen.getByTestId('confirm-disable-button'))

      await waitFor(() => {
        expect(onToggleEnabled).toHaveBeenCalledWith(1, false)
      })
    })

    it('calls onToggleEnabled(true) immediately for disabled peers', async () => {
      const onToggleEnabled = vi.fn().mockResolvedValue(undefined)
      const disabledPeer: Peer = { ...MOCK_PEER, enabled: false }
      renderCard({ peer: disabledPeer, onToggleEnabled })

      await openActionsMenu()
      fireEvent.click(screen.getByTestId('toggle-enabled-button'))

      await waitFor(() => {
        expect(onToggleEnabled).toHaveBeenCalledWith(1, true)
      })
      expect(screen.queryByTestId('disable-confirmation')).toBeNull()
    })
  })
})
