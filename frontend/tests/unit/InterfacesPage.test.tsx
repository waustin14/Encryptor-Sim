/**
 * Unit tests for InterfacesPage form validation and rendering.
 *
 * Validates that invalid IP, netmask, and gateway inputs are rejected
 * with appropriate error messages.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { InterfacesPage } from '../../src/pages/InterfacesPage'
import { useAuthStore } from '../../src/state/authStore'
import { useInterfacesStore } from '../../src/state/interfacesStore'

const MOCK_INTERFACES = [
  {
    interfaceId: 1,
    name: 'CT',
    ipAddress: null,
    netmask: null,
    gateway: null,
    namespace: 'ns_ct',
    device: 'eth1',
  },
  {
    interfaceId: 2,
    name: 'PT',
    ipAddress: '10.0.0.1',
    netmask: '255.255.255.0',
    gateway: '10.0.0.254',
    namespace: 'ns_pt',
    device: 'eth2',
  },
  {
    interfaceId: 3,
    name: 'MGMT',
    ipAddress: null,
    netmask: null,
    gateway: null,
    namespace: 'ns_mgmt',
    device: 'eth0',
  },
]

function renderPage() {
  return render(
    <ChakraProvider value={defaultSystem}>
      <MemoryRouter>
        <InterfacesPage />
      </MemoryRouter>
    </ChakraProvider>,
  )
}

describe('InterfacesPage', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'test-token',
      refreshToken: 'test-refresh',
      isAuthenticated: true,
    })
    useInterfacesStore.setState({
      interfaces: MOCK_INTERFACES,
      loading: false,
      error: null,
      fetchInterfaces: vi.fn(),
      updateInterface: vi.fn(),
    })
  })

  it('renders interface cards for all three interfaces', () => {
    renderPage()

    expect(screen.getByText('Ciphertext (CT)')).toBeTruthy()
    expect(screen.getByText('Plaintext (PT)')).toBeTruthy()
    expect(screen.getByText('Management (MGMT)')).toBeTruthy()
  })

  it('renders the page heading', () => {
    renderPage()

    expect(screen.getByText('Interface Configuration')).toBeTruthy()
  })

  it('shows configured status for interfaces with IP', () => {
    renderPage()

    const badges = screen.getAllByText('Configured')
    expect(badges.length).toBe(1) // Only PT is configured

    const unconfigured = screen.getAllByText('Unconfigured')
    expect(unconfigured.length).toBe(2) // CT and MGMT
  })

  it('shows loading state', () => {
    useInterfacesStore.setState({ loading: true, interfaces: [] })
    renderPage()

    expect(screen.getByText('Loading interfaces...')).toBeTruthy()
  })

  it('shows error state', () => {
    useInterfacesStore.setState({ error: 'Network error' })
    renderPage()

    expect(screen.getByText('Network error')).toBeTruthy()
  })

  it('opens configuration form when card is clicked', () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))

    expect(screen.getByText('Configure CT Interface')).toBeTruthy()
    expect(screen.getByText('Apply Configuration')).toBeTruthy()
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('rejects invalid IP address format', async () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))

    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: 'not-an-ip' } })
    fireEvent.change(inputs[1], { target: { value: '255.255.255.0' } })
    fireEvent.change(inputs[2], { target: { value: '192.168.1.254' } })

    fireEvent.click(screen.getByText('Apply Configuration'))

    await waitFor(() => {
      expect(screen.getByText('Invalid IP address format')).toBeTruthy()
    })
  })

  it('rejects IP with octets out of range', async () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))

    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: '256.1.1.1' } })
    fireEvent.change(inputs[1], { target: { value: '255.255.255.0' } })
    fireEvent.change(inputs[2], { target: { value: '192.168.1.254' } })

    fireEvent.click(screen.getByText('Apply Configuration'))

    await waitFor(() => {
      expect(screen.getByText('IP octets must be 0-255')).toBeTruthy()
    })
  })

  it('rejects reserved 0.0.0.0 address', async () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))

    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: '0.0.0.0' } })
    fireEvent.change(inputs[1], { target: { value: '255.255.255.0' } })
    fireEvent.change(inputs[2], { target: { value: '192.168.1.254' } })

    fireEvent.click(screen.getByText('Apply Configuration'))

    await waitFor(() => {
      expect(screen.getByText('Reserved address not allowed')).toBeTruthy()
    })
  })

  it('rejects non-contiguous netmask', async () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))

    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: '192.168.1.1' } })
    fireEvent.change(inputs[1], { target: { value: '255.0.255.0' } })
    fireEvent.change(inputs[2], { target: { value: '192.168.1.254' } })

    fireEvent.click(screen.getByText('Apply Configuration'))

    await waitFor(() => {
      expect(screen.getByText('Invalid netmask: must be contiguous')).toBeTruthy()
    })
  })

  it('rejects invalid gateway format', async () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))

    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: '192.168.1.1' } })
    fireEvent.change(inputs[1], { target: { value: '255.255.255.0' } })
    fireEvent.change(inputs[2], { target: { value: 'bad-gateway' } })

    fireEvent.click(screen.getByText('Apply Configuration'))

    await waitFor(() => {
      expect(screen.getByText('Invalid gateway format')).toBeTruthy()
    })
  })

  it('closes the form when Cancel is clicked', () => {
    renderPage()

    fireEvent.click(screen.getByText('Ciphertext (CT)'))
    expect(screen.getByText('Configure CT Interface')).toBeTruthy()

    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByText('Configure CT Interface')).toBeNull()
  })

  it('pre-fills form with existing config when editing configured interface', () => {
    renderPage()

    fireEvent.click(screen.getByText('Plaintext (PT)'))

    const inputs = screen.getAllByRole('textbox')
    expect(inputs[0]).toHaveProperty('value', '10.0.0.1')
    expect(inputs[1]).toHaveProperty('value', '255.255.255.0')
    expect(inputs[2]).toHaveProperty('value', '10.0.0.254')
  })
})
