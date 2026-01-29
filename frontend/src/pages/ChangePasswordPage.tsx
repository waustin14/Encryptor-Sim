/**
 * Change password page component.
 *
 * Forces password change on first login when default credentials are detected.
 * Provides real-time validation feedback for password requirements.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Field,
  Heading,
  Input,
  Stack,
  Text,
} from '@chakra-ui/react'

import { useAuthStore } from '../state/authStore'

export function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const changePassword = useAuthStore((state) => state.changePassword)
  const navigate = useNavigate()

  const isMinLength = newPassword.length >= 8
  const isMaxLength = newPassword.length <= 72
  const isValidLength = isMinLength && isMaxLength
  const passwordsMatch = newPassword === confirmPassword && confirmPassword !== ''
  const isFormValid = currentPassword !== '' && isValidLength && passwordsMatch

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await changePassword(currentPassword, newPassword)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password change failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bg="gray.50"
    >
      <Box
        maxW="md"
        w="full"
        bg="white"
        rounded="lg"
        shadow="md"
        p={8}
      >
        <Stack gap={6}>
          <Box>
            <Heading size="lg">Change Password</Heading>
            <Text color="gray.600" mt={2}>
              You must change your password before continuing.
            </Text>
          </Box>

          <Box
            bg="orange.50"
            border="1px solid"
            borderColor="orange.200"
            color="orange.700"
            px={4}
            py={3}
            rounded="md"
          >
            Default credentials detected. Please choose a secure password.
          </Box>

          {error && (
            <Box
              bg="red.50"
              border="1px solid"
              borderColor="red.200"
              color="red.700"
              px={4}
              py={3}
              rounded="md"
            >
              {error}
            </Box>
          )}

          <form onSubmit={handleSubmit}>
            <Stack gap={4}>
              <Field.Root required>
                <Field.Label>Current Password</Field.Label>
                <Input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </Field.Root>

              <Field.Root required invalid={newPassword !== '' && !isValidLength}>
                <Field.Label>New Password</Field.Label>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                />
                {newPassword === '' ? (
                  <Field.HelperText>Must be 8-72 characters</Field.HelperText>
                ) : !isMinLength ? (
                  <Field.ErrorText>Password must be at least 8 characters</Field.ErrorText>
                ) : !isMaxLength ? (
                  <Field.ErrorText>Password must be at most 72 characters</Field.ErrorText>
                ) : (
                  <Field.HelperText color="green.600">Meets length requirements</Field.HelperText>
                )}
              </Field.Root>

              <Field.Root required invalid={confirmPassword !== '' && !passwordsMatch}>
                <Field.Label>Confirm New Password</Field.Label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                />
                {confirmPassword !== '' && !passwordsMatch && (
                  <Field.ErrorText>Passwords do not match</Field.ErrorText>
                )}
                {passwordsMatch && (
                  <Field.HelperText color="green.600">Passwords match</Field.HelperText>
                )}
              </Field.Root>

              <Box p={3} bg="blue.50" rounded="md">
                <Text fontWeight="semibold" fontSize="sm" mb={1}>
                  Password Requirements:
                </Text>
                <Text fontSize="sm" color={isValidLength ? 'green.600' : 'gray.600'}>
                  {isValidLength ? '\u2713' : '\u2022'} 8-72 characters
                </Text>
              </Box>

              <Button
                type="submit"
                colorPalette="blue"
                width="full"
                loading={loading}
                disabled={!isFormValid}
              >
                Change Password
              </Button>
            </Stack>
          </form>
        </Stack>
      </Box>
    </Box>
  )
}
