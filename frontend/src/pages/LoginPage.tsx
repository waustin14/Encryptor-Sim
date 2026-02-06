/**
 * Login page component.
 *
 * Provides username/password form for authentication.
 * Uses Chakra UI components and Zustand authStore.
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

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const login = useAuthStore((state) => state.login)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
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
            <Heading size="lg">Encryptor Simulator</Heading>
            <Text color="gray.600">Sign in to continue</Text>
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
                <Field.Label>Username</Field.Label>
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                />
              </Field.Root>

              <Field.Root required>
                <Field.Label>Password</Field.Label>
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </Field.Root>

              <Button
                type="submit"
                colorPalette="blue"
                width="full"
                loading={loading}
              >
                Sign In
              </Button>
            </Stack>
          </form>

          <Text fontSize="sm" color="gray.500">
            Default credentials: admin / changeme
          </Text>
        </Stack>
      </Box>
    </Box>
  )
}
