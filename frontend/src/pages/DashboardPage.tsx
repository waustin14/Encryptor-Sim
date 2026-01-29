import { Box, Button, Container, Heading, HStack, Stack, Text } from '@chakra-ui/react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { IsolationStatusBanner } from '../components/IsolationStatusBanner'
import { useAuthStore } from '../state/authStore'
import { useSystemStatusStore } from '../state/systemStatus'

export function DashboardPage() {
  const { isolationStatus, isLoading, error, loadIsolationStatus, connectIsolationStatusSocket } =
    useSystemStatusStore()
  const { logout, user } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    loadIsolationStatus()
    const disconnect = connectIsolationStatusSocket()
    return () => {
      disconnect()
    }
  }, [loadIsolationStatus, connectIsolationStatusSocket])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <Box
      minHeight="100vh"
      paddingY={{ base: 12, md: 20 }}
      background="radial-gradient(circle at top, rgba(255, 214, 165, 0.35), transparent 55%), linear-gradient(120deg, #f6f0e8 0%, #fff 45%, #f1f5f9 100%)"
    >
      <Container maxW="6xl">
        <Stack gap={10}>
          <HStack justify="space-between" align="flex-start">
            <Box>
              <Text fontSize="sm" letterSpacing="0.12em" textTransform="uppercase" color="orange.600">
                Encryptor-Sim Control
              </Text>
              <Heading fontSize={{ base: '2xl', md: '4xl' }} fontWeight="600">
                System Dashboard
              </Heading>
              <Text maxW="lg" color="gray.600">
                Verify isolation at boot and keep the status in view before any operations begin.
              </Text>
            </Box>
            <Button
              onClick={handleLogout}
              variant="outline"
              size="sm"
            >
              Logout{user ? ` (${user.username})` : ''}
            </Button>
          </HStack>

          <IsolationStatusBanner status={isolationStatus} isLoading={isLoading} error={error} />
        </Stack>
      </Container>
    </Box>
  )
}
