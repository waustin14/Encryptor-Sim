/**
 * Unit tests for RouteForm CIDR validation and submission (Story 4.4, Task 7.14).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { RouteForm } from '../../src/components/RouteForm'
import { usePeersStore } from '../../src/state/peersStore'

vi.mock('../../src/state/peersStore')

describe('RouteForm', () => {
  const mockOnSubmit = vi.fn()
  const mockOnCancel = vi.fn()
  const mockFetchPeers = vi.fn()

  const mockPeers = [
    { peerId: 1, name: 'peer-1', remoteIp: '10.0.0.1', ikeVersion: 'ikev2', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    { peerId: 2, name: 'peer-2', remoteIp: '10.0.0.2', ikeVersion: 'ikev2', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockOnSubmit.mockResolvedValue(undefined)
    vi.mocked(usePeersStore).mockReturnValue({
      peers: mockPeers,
      loading: false,
      error: null,
      fetchPeers: mockFetchPeers,
      createPeer: vi.fn(),
      deletePeer: vi.fn(),
    })
  })

  afterEach(() => {
    cleanup()
  })

  function renderForm(props: { mode: 'create' | 'edit'; initialData?: any }) {
    return render(
      <ChakraProvider value={defaultSystem}>
        <RouteForm
          mode={props.mode}
          initialData={props.initialData}
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        />
      </ChakraProvider>
    )
  }

  describe('CIDR Validation', () => {
    it('accepts valid CIDR 192.168.1.0/24', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '1' } })
      fireEvent.change(cidrInput, { target: { value: '192.168.1.0/24' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          peerId: '1',
          destinationCidr: '192.168.1.0/24',
        })
      })
    })

    it('accepts valid CIDR 10.0.0.0/8', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '1' } })
      fireEvent.change(cidrInput, { target: { value: '10.0.0.0/8' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          peerId: '1',
          destinationCidr: '10.0.0.0/8',
        })
      })
    })

    it('rejects invalid CIDR /33 (prefix too large)', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '1' } })
      fireEvent.change(cidrInput, { target: { value: '192.168.1.0/33' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/prefix length must be 0-32/i)).toBeTruthy()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('rejects invalid CIDR with no prefix', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '1' } })
      fireEvent.change(cidrInput, { target: { value: '192.168.1.0' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid cidr format/i)).toBeTruthy()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('rejects invalid CIDR with octet > 255', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '1' } })
      fireEvent.change(cidrInput, { target: { value: '192.168.256.0/24' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/ip octets must be 0-255/i)).toBeTruthy()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('rejects empty CIDR', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '1' } })
      fireEvent.change(cidrInput, { target: { value: '' } })
      fireEvent.click(submitButton)

      // Validation should prevent submission
      await new Promise(resolve => setTimeout(resolve, 100))
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Peer Selection Validation', () => {
    it('requires peer selection in create mode', async () => {
      renderForm({ mode: 'create' })

      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(cidrInput, { target: { value: '192.168.1.0/24' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/peer selection is required/i)).toBeTruthy()
      })
      expect(mockOnSubmit).not.toHaveBeenCalled()
    })

    it('fetches peers on mount in create mode', () => {
      vi.mocked(usePeersStore).mockReturnValue({
        peers: [],
        loading: false,
        error: null,
        fetchPeers: mockFetchPeers,
        createPeer: vi.fn(),
        deletePeer: vi.fn(),
      })

      renderForm({ mode: 'create' })

      expect(mockFetchPeers).toHaveBeenCalledTimes(1)
    })

    it('does not require peer selection in edit mode', async () => {
      renderForm({ mode: 'edit', initialData: { peerId: '1', destinationCidr: '192.168.1.0/24' } })

      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /save changes/i })

      fireEvent.change(cidrInput, { target: { value: '192.168.2.0/24' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          peerId: '1',
          destinationCidr: '192.168.2.0/24',
        })
      })
    })
  })

  describe('Form Submission', () => {
    it('calls onSubmit with form data', async () => {
      renderForm({ mode: 'create' })

      const peerSelect = screen.getByRole('combobox', { name: /peer/i })
      const cidrInput = screen.getByLabelText(/destination cidr/i)
      const submitButton = screen.getByRole('button', { name: /create route/i })

      fireEvent.change(peerSelect, { target: { value: '2' } })
      fireEvent.change(cidrInput, { target: { value: '10.1.1.0/24' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          peerId: '2',
          destinationCidr: '10.1.1.0/24',
        })
      })
    })

    it('calls onCancel when cancel button clicked', async () => {
      renderForm({ mode: 'create' })

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      fireEvent.click(cancelButton)

      expect(mockOnCancel).toHaveBeenCalledTimes(1)
    })
  })

  describe('Initial Data', () => {
    it('populates form with initial data in edit mode', () => {
      renderForm({ mode: 'edit', initialData: { peerId: '1', destinationCidr: '192.168.1.0/24' } })

      const cidrInput = screen.getByLabelText(/destination cidr/i) as HTMLInputElement
      expect(cidrInput.value).toBe('192.168.1.0/24')
    })
  })
})
