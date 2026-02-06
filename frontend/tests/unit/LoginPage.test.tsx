/**
 * Unit tests for LoginPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'

import { LoginPage } from '../../src/pages/LoginPage'
import { useAuthStore } from '../../src/state/authStore'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ChakraProvider value={defaultSystem}>
      <BrowserRouter>{ui}</BrowserRouter>
    </ChakraProvider>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  })

  it('renders login form with heading', () => {
    renderWithProviders(<LoginPage />)

    // Use getAllByText for potential duplicates
    const titles = screen.getAllByText('Encryptor Simulator')
    const subtitles = screen.getAllByText('Sign in to continue')
    expect(titles.length).toBeGreaterThan(0)
    expect(subtitles.length).toBeGreaterThan(0)
  })

  it('renders username and password labels', () => {
    renderWithProviders(<LoginPage />)

    // Chakra UI v3 Field renders labels - use getAllByText for duplicates
    const usernameLabels = screen.getAllByText('Username')
    const passwordLabels = screen.getAllByText('Password')
    expect(usernameLabels.length).toBeGreaterThan(0)
    expect(passwordLabels.length).toBeGreaterThan(0)
  })

  it('renders submit button', () => {
    renderWithProviders(<LoginPage />)

    // Use getAllByText in case Chakra renders multiple
    const buttons = screen.getAllByText('Sign In')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('shows default credentials hint', () => {
    renderWithProviders(<LoginPage />)

    // Use getAllByText in case there are multiple matches
    const hints = screen.getAllByText(/default credentials:\s*admin\s*\/\s*changeme/i)
    expect(hints.length).toBeGreaterThan(0)
  })

  it('renders input fields', () => {
    renderWithProviders(<LoginPage />)

    // Check inputs exist by type
    const inputs = document.querySelectorAll('input')
    expect(inputs.length).toBeGreaterThanOrEqual(2)

    // First input should be text (username)
    expect(inputs[0].type).toBe('text')
    // Second input should be password
    expect(inputs[1].type).toBe('password')
  })
})
