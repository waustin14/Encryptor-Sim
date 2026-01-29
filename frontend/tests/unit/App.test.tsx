import { describe, expect, it, beforeEach } from 'vitest'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { render, screen } from '@testing-library/react'
import { App } from '../../src/App'
import { useAuthStore } from '../../src/state/authStore'

describe('App', () => {
  beforeEach(() => {
    // Set up authenticated state so ProtectedRoute allows access to dashboard
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: false },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
      isAuthenticated: true,
    })
  })

  it('renders the system dashboard heading', () => {
    render(
      <ChakraProvider value={defaultSystem}>
        <App />
      </ChakraProvider>,
    )
    expect(screen.getByText('System Dashboard')).toBeTruthy()
  })
})
