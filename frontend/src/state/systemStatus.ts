import { create } from 'zustand'

export type IsolationStatusCheck = {
  name: string
  status: string
  details?: string | null
}

export type IsolationStatus = {
  status: string
  timestamp: string
  checks: IsolationStatusCheck[]
  failures: string[]
  duration: number
}

type SystemStatusState = {
  isolationStatus: IsolationStatus | null
  isLoading: boolean
  error: string | null
  setIsolationStatus: (status: IsolationStatus | null) => void
  loadIsolationStatus: () => Promise<void>
  connectIsolationStatusSocket: () => () => void
}

const buildSystemSocketUrl = () => {
  if (typeof window === 'undefined') {
    return ''
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/system`
}

export const useSystemStatusStore = create<SystemStatusState>((set) => ({
  isolationStatus: null,
  isLoading: false,
  error: null,
  setIsolationStatus: (status) => set({ isolationStatus: status }),
  loadIsolationStatus: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await fetch('/api/v1/system/isolation-status')
      if (response.status === 404) {
        set({ isolationStatus: null, isLoading: false })
        return
      }
      if (!response.ok) {
        throw new Error(`Failed to load status (${response.status})`)
      }
      const payload = (await response.json()) as { data: IsolationStatus }
      set({ isolationStatus: payload.data, isLoading: false })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      set({ error: message, isLoading: false })
    }
  },
  connectIsolationStatusSocket: () => {
    const url = buildSystemSocketUrl()
    if (!url) {
      return () => undefined
    }
    const socket = new WebSocket(url)
    socket.addEventListener('message', (event) => {
      try {
        const payload = JSON.parse(event.data as string) as {
          type?: string
          data?: IsolationStatus
        }
        if (payload.type === 'system.isolation_status_updated' && payload.data) {
          set({ isolationStatus: payload.data })
        }
      } catch {
        // Ignore malformed WebSocket payloads.
      }
    })
    return () => {
      socket.close()
    }
  },
}))
