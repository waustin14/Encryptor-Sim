import { Badge, Box, Container, Heading, HStack, SimpleGrid, Stack, Text } from '@chakra-ui/react'
import { useEffect } from 'react'

import { InterfaceStatsCard } from '../components/InterfaceStatsCard'
import { IsolationStatusBanner } from '../components/IsolationStatusBanner'
import { NavBar } from '../components/NavBar'
import { TunnelStatusCard } from '../components/TunnelStatusCard'
import { useInterfacesStore } from '../state/interfacesStore'
import { useSystemStatusStore } from '../state/systemStatus'
import { useTunnelsStore } from '../state/tunnelsStore'

export function DashboardPage() {
  const { isolationStatus, isLoading, error, loadIsolationStatus, connectIsolationStatusSocket } =
    useSystemStatusStore()
  const { tunnelStatus, isConnected, connectWebSocket, disconnectWebSocket } = useTunnelsStore()
  const { interfaceStats } = useInterfacesStore()

  useEffect(() => {
    loadIsolationStatus()
    const disconnect = connectIsolationStatusSocket()
    return () => {
      disconnect()
    }
  }, [loadIsolationStatus, connectIsolationStatusSocket])

  useEffect(() => {
    connectWebSocket()
    return () => {
      disconnectWebSocket()
    }
  }, [connectWebSocket, disconnectWebSocket])

  const tunnelEntries = Object.values(tunnelStatus)
  const statsEntries = Object.entries(interfaceStats)

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
            <HStack gap={3}>
              <Badge
                colorPalette={isConnected ? 'green' : 'red'}
                fontSize="0.75rem"
                paddingX={2}
                paddingY={1}
                borderRadius="999px"
                data-testid="ws-connection-status"
              >
                {isConnected ? 'Live' : 'Disconnected'}
              </Badge>
              <NavBar />
            </HStack>
          </HStack>

          <IsolationStatusBanner status={isolationStatus} isLoading={isLoading} error={error} />

          {/* Tunnel Status Section */}
          <Box>
            <HStack justify="space-between" align="center" mb={4}>
              <Heading fontSize="xl" fontWeight="600">
                Tunnel Status
              </Heading>
              <Text fontSize="sm" color="gray.500">
                {tunnelEntries.length} peer{tunnelEntries.length !== 1 ? 's' : ''}
              </Text>
            </HStack>
            {tunnelEntries.length === 0 ? (
              <Box
                border="1px dashed"
                borderColor="gray.300"
                borderRadius="12px"
                padding={6}
                textAlign="center"
              >
                <Text color="gray.500">No tunnel status available</Text>
                <Text fontSize="sm" color="gray.400" mt={1}>
                  Configure peers to see tunnel status
                </Text>
              </Box>
            ) : (
              <Stack gap={3}>
                {tunnelEntries.map((tunnel) => (
                  <TunnelStatusCard key={tunnel.peerName} tunnel={tunnel} />
                ))}
              </Stack>
            )}
          </Box>

          {/* Interface Statistics Section */}
          <Box>
            <Heading fontSize="xl" fontWeight="600" mb={4}>
              Interface Statistics
            </Heading>
            {statsEntries.length === 0 ? (
              <Box
                border="1px dashed"
                borderColor="gray.300"
                borderRadius="12px"
                padding={6}
                textAlign="center"
              >
                <Text color="gray.500">No interface statistics available</Text>
                <Text fontSize="sm" color="gray.400" mt={1}>
                  Statistics will appear once WebSocket connects
                </Text>
              </Box>
            ) : (
              <SimpleGrid columns={{ base: 1, md: 3 }} gap={4}>
                {statsEntries.map(([name, stats]) => (
                  <InterfaceStatsCard key={name} interfaceName={name} stats={stats} />
                ))}
              </SimpleGrid>
            )}
          </Box>
        </Stack>
      </Container>
    </Box>
  )
}
