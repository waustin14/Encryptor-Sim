/**
 * Unit tests for RouteCard component (Story 4.4 + Story 4.5).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'

import { RouteCard } from '../../src/components/RouteCard'
import type { Route } from '../../src/state/routesStore'

const MOCK_ROUTE: Route = {
  routeId: 1,
  peerId: 1,
  peerName: 'site-a',
  destinationCidr: '192.168.1.0/24',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
}

function renderCard(props?: { onEdit?: (id: number) => void; onDelete?: (id: number) => Promise<void> }) {
  const onEdit = props?.onEdit ?? vi.fn()
  const onDelete = props?.onDelete ?? vi.fn(() => Promise.resolve())

  return render(
    <ChakraProvider value={defaultSystem}>
      <RouteCard route={MOCK_ROUTE} onEdit={onEdit} onDelete={onDelete} />
    </ChakraProvider>,
  )
}

describe('RouteCard', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders destination CIDR', () => {
    renderCard()
    expect(screen.getByText('192.168.1.0/24')).toBeTruthy()
  })

  it('renders peer name', () => {
    renderCard()
    expect(screen.getAllByText('site-a').length).toBeGreaterThanOrEqual(1)
  })

  it('calls onEdit when clicked', () => {
    const onEdit = vi.fn()
    renderCard({ onEdit })

    fireEvent.click(screen.getByText('192.168.1.0/24'))
    expect(onEdit).toHaveBeenCalledWith(1)
  })

  // Story 4.5: Delete button and confirmation dialog tests

  it('renders delete button', () => {
    renderCard()
    expect(screen.getByLabelText('Delete route 192.168.1.0/24')).toBeTruthy()
  })

  it('shows confirmation dialog when delete is clicked', () => {
    renderCard()
    fireEvent.click(screen.getByLabelText('Delete route 192.168.1.0/24'))

    expect(screen.getByText(/Delete route "192.168.1.0\/24"\? This cannot be undone\./)).toBeTruthy()
    expect(screen.getByLabelText('Confirm delete')).toBeTruthy()
    expect(screen.getByLabelText('Cancel delete')).toBeTruthy()
  })

  it('hides confirmation dialog when cancel is clicked', () => {
    renderCard()
    fireEvent.click(screen.getByLabelText('Delete route 192.168.1.0/24'))
    fireEvent.click(screen.getByLabelText('Cancel delete'))

    expect(screen.queryByText(/This cannot be undone/)).toBeNull()
  })

  it('calls onDelete when confirm is clicked', async () => {
    const onDelete = vi.fn(() => Promise.resolve())
    renderCard({ onDelete })

    fireEvent.click(screen.getByLabelText('Delete route 192.168.1.0/24'))
    fireEvent.click(screen.getByLabelText('Confirm delete'))

    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith(1)
    })
  })

  it('shows error message when delete fails', async () => {
    const onDelete = vi.fn(() => Promise.reject(new Error('Delete failed')))
    renderCard({ onDelete })

    fireEvent.click(screen.getByLabelText('Delete route 192.168.1.0/24'))
    fireEvent.click(screen.getByLabelText('Confirm delete'))

    await waitFor(() => {
      expect(screen.getByText('Error: Delete failed')).toBeTruthy()
    })
  })

  it('does not call onEdit when delete button is clicked', () => {
    const onEdit = vi.fn()
    renderCard({ onEdit })

    fireEvent.click(screen.getByLabelText('Delete route 192.168.1.0/24'))
    expect(onEdit).not.toHaveBeenCalled()
  })
})
