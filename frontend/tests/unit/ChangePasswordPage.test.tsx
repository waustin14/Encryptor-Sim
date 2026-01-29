/**
 * Unit tests for ChangePasswordPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'

import { ChangePasswordPage } from '../../src/pages/ChangePasswordPage'
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

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
      isAuthenticated: true,
    })
  })

  it('renders change password heading', () => {
    renderWithProviders(<ChangePasswordPage />)

    const headings = screen.getAllByText('Change Password')
    expect(headings.length).toBeGreaterThan(0)
  })

  it('renders warning about default credentials', () => {
    renderWithProviders(<ChangePasswordPage />)

    const warnings = screen.getAllByText(/default credentials/i)
    expect(warnings.length).toBeGreaterThan(0)
  })

  it('renders password requirement text', () => {
    renderWithProviders(<ChangePasswordPage />)

    const reqs = screen.getAllByText(/8-72 characters/i)
    expect(reqs.length).toBeGreaterThan(0)
  })

  it('renders password input fields', () => {
    renderWithProviders(<ChangePasswordPage />)

    // Chakra UI v3 may render additional inputs; verify at least 3 password inputs exist
    const inputs = document.querySelectorAll('input[type="password"]')
    expect(inputs.length).toBeGreaterThanOrEqual(3)
  })

  it('renders submit button', () => {
    renderWithProviders(<ChangePasswordPage />)

    const buttons = screen.getAllByText('Change Password')
    // Filter to find the button element
    const submitButton = buttons.find(
      (el) => el.tagName === 'BUTTON' || el.closest('button')
    )
    expect(submitButton).toBeTruthy()
  })

  it('shows must change password message', () => {
    renderWithProviders(<ChangePasswordPage />)

    const messages = screen.getAllByText(/must change your password/i)
    expect(messages.length).toBeGreaterThan(0)
  })

  it('disables submit button when form is invalid', () => {
    renderWithProviders(<ChangePasswordPage />)

    const inputs = document.querySelectorAll('input[type="password"]')
    const currentPasswordInput = inputs[0] as HTMLInputElement
    const newPasswordInput = inputs[1] as HTMLInputElement
    const confirmPasswordInput = inputs[2] as HTMLInputElement

    // Fill with mismatched passwords
    fireEvent.change(currentPasswordInput, { target: { value: 'admin' } })
    fireEvent.change(newPasswordInput, { target: { value: 'newpass123' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'different123' } })

    const submitButton = screen.getAllByText('Change Password').find(
      (el) => el.tagName === 'BUTTON' || el.closest('button')
    )
    const button = submitButton?.closest('button') || (submitButton as HTMLButtonElement)
    expect(button?.disabled).toBe(true)
  })

  it('enables submit button when form is valid', () => {
    renderWithProviders(<ChangePasswordPage />)

    const inputs = document.querySelectorAll('input[type="password"]')
    const currentPasswordInput = inputs[0] as HTMLInputElement
    const newPasswordInput = inputs[1] as HTMLInputElement
    const confirmPasswordInput = inputs[2] as HTMLInputElement

    // Fill with valid matching passwords
    fireEvent.change(currentPasswordInput, { target: { value: 'admin' } })
    fireEvent.change(newPasswordInput, { target: { value: 'newpass123' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'newpass123' } })

    const submitButton = screen.getAllByText('Change Password').find(
      (el) => el.tagName === 'BUTTON' || el.closest('button')
    )
    const button = submitButton?.closest('button') || (submitButton as HTMLButtonElement)
    expect(button?.disabled).toBe(false)
  })

  it('calls changePassword and navigates on successful submit', async () => {
    const mockChangePassword = vi.fn().mockResolvedValue(undefined)
    useAuthStore.setState({
      changePassword: mockChangePassword,
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
      isAuthenticated: true,
    })

    renderWithProviders(<ChangePasswordPage />)

    const inputs = document.querySelectorAll('input[type="password"]')
    const currentPasswordInput = inputs[0] as HTMLInputElement
    const newPasswordInput = inputs[1] as HTMLInputElement
    const confirmPasswordInput = inputs[2] as HTMLInputElement

    fireEvent.change(currentPasswordInput, { target: { value: 'admin' } })
    fireEvent.change(newPasswordInput, { target: { value: 'newpass123' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'newpass123' } })

    const submitButton = screen.getAllByText('Change Password').find(
      (el) => el.tagName === 'BUTTON' || el.closest('button')
    )
    const button = submitButton?.closest('button') || (submitButton as HTMLButtonElement)

    fireEvent.click(button!)

    // Wait for async operations
    await vi.waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith('admin', 'newpass123')
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('displays error message on failed password change', async () => {
    const mockChangePassword = vi.fn().mockRejectedValue(new Error('Current password is incorrect'))
    useAuthStore.setState({
      changePassword: mockChangePassword,
      user: { userId: 1, username: 'admin', requirePasswordChange: true },
      accessToken: 'fake-token',
      refreshToken: 'fake-refresh',
      isAuthenticated: true,
    })

    renderWithProviders(<ChangePasswordPage />)

    const inputs = document.querySelectorAll('input[type="password"]')
    const currentPasswordInput = inputs[0] as HTMLInputElement
    const newPasswordInput = inputs[1] as HTMLInputElement
    const confirmPasswordInput = inputs[2] as HTMLInputElement

    fireEvent.change(currentPasswordInput, { target: { value: 'wrong' } })
    fireEvent.change(newPasswordInput, { target: { value: 'newpass123' } })
    fireEvent.change(confirmPasswordInput, { target: { value: 'newpass123' } })

    const submitButton = screen.getAllByText('Change Password').find(
      (el) => el.tagName === 'BUTTON' || el.closest('button')
    )
    const button = submitButton?.closest('button') || (submitButton as HTMLButtonElement)

    fireEvent.click(button!)

    // Wait for error to appear
    await vi.waitFor(() => {
      const errorMessages = screen.getAllByText(/current password is incorrect/i)
      expect(errorMessages.length).toBeGreaterThan(0)
    })
  })
})
