import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Container,
  Heading,
  HStack,
  SimpleGrid,
  Stack,
  Text,
} from '@chakra-ui/react'

import { RouteCard } from '../components/RouteCard'
import { RouteForm } from '../components/RouteForm'
import { useAuthStore } from '../state/authStore'
import { useRoutesStore } from '../state/routesStore'
import type { RouteCreateRequest, RouteUpdateRequest } from '../state/routesStore'

export function RoutesPage() {
  const { routes, loading, error, fetchRoutes, createRoute, updateRoute, deleteRoute } = useRoutesStore()
  const { logout, user } = useAuthStore()
  const navigate = useNavigate()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingRouteId, setEditingRouteId] = useState<number | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    fetchRoutes()
  }, [fetchRoutes])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleCreate = async (data: { peerId: string; destinationCidr: string }) => {
    const request: RouteCreateRequest = {
      peerId: parseInt(data.peerId, 10),
      destinationCidr: data.destinationCidr,
    }
    await createRoute(request)
    setShowCreateForm(false)
    setSuccessMessage('Route created successfully')
    setTimeout(() => setSuccessMessage(null), 3000)
  }

  const handleDelete = async (routeId: number) => {
    await deleteRoute(routeId)
    setSuccessMessage('Route deleted successfully')
    setTimeout(() => setSuccessMessage(null), 3000)
  }

  const handleUpdate = async (data: { peerId: string; destinationCidr: string }) => {
    if (editingRouteId === null) return
    const updates: RouteUpdateRequest = {}
    if (data.destinationCidr) updates.destinationCidr = data.destinationCidr
    await updateRoute(editingRouteId, updates)
    setEditingRouteId(null)
    setSuccessMessage('Route updated successfully')
    setTimeout(() => setSuccessMessage(null), 3000)
  }

  const editingRoute = editingRouteId !== null
    ? routes.find((r) => r.routeId === editingRouteId)
    : null

  // Group routes by peer
  const routesByPeer = routes.reduce(
    (groups, route) => {
      const key = route.peerName
      if (!groups[key]) groups[key] = []
      groups[key].push(route)
      return groups
    },
    {} as Record<string, typeof routes>,
  )

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
                Route Configuration
              </Heading>
              <Text maxW="lg" color="gray.600">
                Manage traffic routes associated with IPsec peers.
              </Text>
            </Box>
            <HStack gap={2}>
              <Button onClick={() => navigate('/dashboard')} variant="outline" size="sm">
                Dashboard
              </Button>
              <Button onClick={() => navigate('/peers')} variant="outline" size="sm">
                Peers
              </Button>
              <Button onClick={() => navigate('/interfaces')} variant="outline" size="sm">
                Interfaces
              </Button>
              <Button onClick={handleLogout} variant="outline" size="sm">
                Logout{user ? ` (${user.username})` : ''}
              </Button>
            </HStack>
          </HStack>

          {successMessage && (
            <Box bg="green.50" border="1px solid" borderColor="green.200" color="green.700" px={4} py={3} rounded="md">
              {successMessage}
            </Box>
          )}

          {error && (
            <Box bg="red.50" border="1px solid" borderColor="red.200" color="red.700" px={4} py={3} rounded="md">
              {error}
            </Box>
          )}

          {loading && (
            <Text color="gray.500">Loading routes...</Text>
          )}

          <HStack>
            <Button
              colorPalette="orange"
              onClick={() => { setShowCreateForm(true); setEditingRouteId(null) }}
              disabled={showCreateForm}
            >
              Add Route
            </Button>
          </HStack>

          {routes.length === 0 && !loading && !showCreateForm && (
            <Box
              border="1px dashed"
              borderColor="gray.300"
              borderRadius="16px"
              padding={8}
              textAlign="center"
              color="gray.500"
            >
              <Text>No routes configured yet. Click "Add Route" to create one.</Text>
            </Box>
          )}

          {Object.entries(routesByPeer).map(([peerName, peerRoutes]) => (
            <Box key={peerName}>
              <Text fontSize="sm" fontWeight="600" color="gray.600" mb={3} textTransform="uppercase" letterSpacing="0.08em">
                Peer: {peerName}
              </Text>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={6}>
                {peerRoutes.map((route) => (
                  <RouteCard
                    key={route.routeId}
                    route={route}
                    onEdit={(id) => { setEditingRouteId(id); setShowCreateForm(false) }}
                    onDelete={handleDelete}
                  />
                ))}
              </SimpleGrid>
            </Box>
          ))}

          {showCreateForm && (
            <RouteForm
              mode="create"
              onSubmit={handleCreate}
              onCancel={() => setShowCreateForm(false)}
            />
          )}

          {editingRoute && (
            <RouteForm
              mode="edit"
              initialData={{
                peerId: String(editingRoute.peerId),
                destinationCidr: editingRoute.destinationCidr,
              }}
              onSubmit={handleUpdate}
              onCancel={() => setEditingRouteId(null)}
            />
          )}
        </Stack>
      </Container>
    </Box>
  )
}
