/**
 * Unit tests for interfacesStore.
 *
 * Covers fetch, update, and error handling for interface configuration state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

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

describe('interfacesStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useInterfacesStore.setState({
      interfaces: [],
      interfaceStats: {},
      loading: false,
      error: null,
    })
    useAuthStore.setState({
      accessToken: 'test-token',
      isAuthenticated: true,
    })
  })

  it('has correct initial state', () => {
    const state = useInterfacesStore.getState()

    expect(state.interfaces).toEqual([])
    expect(state.loading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('fetchInterfaces loads interface data on success', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: MOCK_INTERFACES }),
    })

    const { fetchInterfaces } = useInterfacesStore.getState()
    await fetchInterfaces()

    const state = useInterfacesStore.getState()
    expect(state.interfaces).toEqual(MOCK_INTERFACES)
    expect(state.loading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('fetchInterfaces sends authorization header', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: [] }),
    })

    const { fetchInterfaces } = useInterfacesStore.getState()
    await fetchInterfaces()

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/interfaces',
      expect.objectContaining({
        headers: { Authorization: 'Bearer test-token' },
      }),
    )
  })

  it('fetchInterfaces sets loading=true during request', async () => {
    let resolvePromise: (value: unknown) => void
    const promise = new Promise((resolve) => { resolvePromise = resolve })

    global.fetch = vi.fn().mockReturnValueOnce(promise)

    const { fetchInterfaces } = useInterfacesStore.getState()
    const fetchPromise = fetchInterfaces()

    expect(useInterfacesStore.getState().loading).toBe(true)

    resolvePromise!({
      ok: true,
      json: () => Promise.resolve({ data: [] }),
    })

    await fetchPromise
    expect(useInterfacesStore.getState().loading).toBe(false)
  })

  it('fetchInterfaces sets error on failure', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { fetchInterfaces } = useInterfacesStore.getState()
    await fetchInterfaces()

    const state = useInterfacesStore.getState()
    expect(state.error).toBe('Failed to load interfaces (500)')
    expect(state.loading).toBe(false)
  })

  it('updateInterface updates the matching interface in state', async () => {
    useInterfacesStore.setState({ interfaces: MOCK_INTERFACES })

    const updatedCT = {
      ...MOCK_INTERFACES[0],
      ipAddress: '192.168.1.1',
      netmask: '255.255.255.0',
      gateway: '192.168.1.254',
    }

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: updatedCT }),
    })

    const { updateInterface } = useInterfacesStore.getState()
    await updateInterface('CT', {
      ipAddress: '192.168.1.1',
      netmask: '255.255.255.0',
      gateway: '192.168.1.254',
    })

    const state = useInterfacesStore.getState()
    const ct = state.interfaces.find((i) => i.name === 'CT')
    expect(ct?.ipAddress).toBe('192.168.1.1')
    expect(ct?.netmask).toBe('255.255.255.0')
    expect(ct?.gateway).toBe('192.168.1.254')

    // Other interfaces unchanged
    expect(state.interfaces.find((i) => i.name === 'PT')?.ipAddress).toBe('10.0.0.1')
  })

  it('updateInterface sends correct POST request', async () => {
    useInterfacesStore.setState({ interfaces: MOCK_INTERFACES })

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: MOCK_INTERFACES[0] }),
    })

    const { updateInterface } = useInterfacesStore.getState()
    await updateInterface('CT', {
      ipAddress: '192.168.1.1',
      netmask: '255.255.255.0',
      gateway: '192.168.1.254',
    })

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/interfaces/CT/configure',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
        body: JSON.stringify({
          ipAddress: '192.168.1.1',
          netmask: '255.255.255.0',
          gateway: '192.168.1.254',
        }),
      }),
    )
  })

  it('updateInterface sets error and throws on failure', async () => {
    useInterfacesStore.setState({ interfaces: MOCK_INTERFACES })

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: 'Invalid IP address format' }),
    })

    const { updateInterface } = useInterfacesStore.getState()
    await expect(
      updateInterface('CT', {
        ipAddress: 'bad',
        netmask: '255.255.255.0',
        gateway: '192.168.1.254',
      }),
    ).rejects.toThrow('Invalid IP address format')

    expect(useInterfacesStore.getState().error).toBe('Invalid IP address format')
  })

  it('updateInterface handles nested error detail', async () => {
    useInterfacesStore.setState({ interfaces: MOCK_INTERFACES })

    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: { detail: 'Netmask must be contiguous' } }),
    })

    const { updateInterface } = useInterfacesStore.getState()
    await expect(
      updateInterface('CT', {
        ipAddress: '192.168.1.1',
        netmask: 'bad',
        gateway: '192.168.1.254',
      }),
    ).rejects.toThrow('Netmask must be contiguous')
  })

  describe('updateInterfaceStats', () => {
    it('stores stats for a new interface', () => {
      const stats = {
        bytesRx: 1000,
        bytesTx: 2000,
        packetsRx: 10,
        packetsTx: 20,
        errorsRx: 0,
        errorsTx: 0,
        timestamp: '2026-02-04T12:00:00Z',
      }

      useInterfacesStore.getState().updateInterfaceStats('CT', stats)

      const stored = useInterfacesStore.getState().interfaceStats['CT']
      expect(stored).toEqual(stats)
    })

    it('updates stats for an existing interface', () => {
      const initial = {
        bytesRx: 100,
        bytesTx: 200,
        packetsRx: 1,
        packetsTx: 2,
        errorsRx: 0,
        errorsTx: 0,
        timestamp: '2026-02-04T12:00:00Z',
      }
      const updated = {
        bytesRx: 500,
        bytesTx: 600,
        packetsRx: 5,
        packetsTx: 6,
        errorsRx: 1,
        errorsTx: 0,
        timestamp: '2026-02-04T12:00:02Z',
      }

      useInterfacesStore.getState().updateInterfaceStats('CT', initial)
      useInterfacesStore.getState().updateInterfaceStats('CT', updated)

      const stored = useInterfacesStore.getState().interfaceStats['CT']
      expect(stored).toEqual(updated)
    })

    it('tracks multiple interfaces independently', () => {
      const ctStats = {
        bytesRx: 100, bytesTx: 200, packetsRx: 10, packetsTx: 20,
        errorsRx: 0, errorsTx: 0, timestamp: '2026-02-04T12:00:00Z',
      }
      const ptStats = {
        bytesRx: 300, bytesTx: 400, packetsRx: 30, packetsTx: 40,
        errorsRx: 0, errorsTx: 0, timestamp: '2026-02-04T12:00:00Z',
      }
      const mgmtStats = {
        bytesRx: 50, bytesTx: 60, packetsRx: 5, packetsTx: 6,
        errorsRx: 0, errorsTx: 0, timestamp: '2026-02-04T12:00:00Z',
      }

      useInterfacesStore.getState().updateInterfaceStats('CT', ctStats)
      useInterfacesStore.getState().updateInterfaceStats('PT', ptStats)
      useInterfacesStore.getState().updateInterfaceStats('MGMT', mgmtStats)

      const state = useInterfacesStore.getState().interfaceStats
      expect(state['CT'].bytesRx).toBe(100)
      expect(state['PT'].bytesRx).toBe(300)
      expect(state['MGMT'].bytesRx).toBe(50)
    })

    it('does not affect interface config state', () => {
      useInterfacesStore.setState({ interfaces: MOCK_INTERFACES })

      useInterfacesStore.getState().updateInterfaceStats('CT', {
        bytesRx: 100, bytesTx: 200, packetsRx: 10, packetsTx: 20,
        errorsRx: 0, errorsTx: 0, timestamp: '2026-02-04T12:00:00Z',
      })

      expect(useInterfacesStore.getState().interfaces).toEqual(MOCK_INTERFACES)
    })

    it('has empty interfaceStats in initial state', () => {
      useInterfacesStore.setState({ interfaceStats: {} })
      expect(useInterfacesStore.getState().interfaceStats).toEqual({})
    })
  })
})
