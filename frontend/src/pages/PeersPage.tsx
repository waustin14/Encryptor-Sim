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
import { toaster } from '../components/ui/toaster'

import { PeerCard } from '../components/PeerCard'
import { PeerForm } from '../components/PeerForm'
import { useAuthStore } from '../state/authStore'
import { usePeersStore } from '../state/peersStore'
import type { PeerCreateRequest, PeerUpdateRequest } from '../state/peersStore'

const DELETE_SUCCESS_TIMEOUT = 3000

export function PeersPage() {
  const { peers, loading, error, fetchPeers, createPeer, updatePeer, deletePeer, toggleEnabled, initiatePeer } = usePeersStore()
  const { logout, user } = useAuthStore()
  const navigate = useNavigate()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingPeerId, setEditingPeerId] = useState<number | null>(null)
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchPeers()
  }, [fetchPeers])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleCreate = async (data: {
    name: string
    remoteIp: string
    psk: string
    ikeVersion: string
    dpdAction: string
    dpdDelay: string
    dpdTimeout: string
    rekeyTime: string
  }) => {
    const request: PeerCreateRequest = {
      name: data.name,
      remoteIp: data.remoteIp,
      psk: data.psk,
      ikeVersion: data.ikeVersion.toLowerCase(),
      dpdAction: data.dpdAction || 'restart',
      dpdDelay: parseInt(data.dpdDelay, 10) || 30,
      dpdTimeout: parseInt(data.dpdTimeout, 10) || 150,
      rekeyTime: parseInt(data.rekeyTime, 10) || 3600,
    }
    await createPeer(request)
    setShowCreateForm(false)
  }

  const handleUpdate = async (data: {
    name: string
    remoteIp: string
    psk: string
    ikeVersion: string
    dpdAction: string
    dpdDelay: string
    dpdTimeout: string
    rekeyTime: string
  }) => {
    if (editingPeerId === null) return
    const updates: PeerUpdateRequest = {}
    if (data.remoteIp) updates.remoteIp = data.remoteIp
    if (data.psk) updates.psk = data.psk
    if (data.ikeVersion) updates.ikeVersion = data.ikeVersion.toLowerCase()
    if (data.dpdAction) updates.dpdAction = data.dpdAction
    if (data.dpdDelay) updates.dpdDelay = parseInt(data.dpdDelay, 10)
    if (data.dpdTimeout) updates.dpdTimeout = parseInt(data.dpdTimeout, 10)
    if (data.rekeyTime) updates.rekeyTime = parseInt(data.rekeyTime, 10)
    await updatePeer(editingPeerId, updates)
    setEditingPeerId(null)
  }

  const handleDelete = async (peerId: number) => {
    const peer = peers.find((p) => p.peerId === peerId)
    await deletePeer(peerId)
    setDeleteSuccess(`Peer "${peer?.name}" deleted successfully`)
    setTimeout(() => setDeleteSuccess(null), DELETE_SUCCESS_TIMEOUT)
    if (editingPeerId === peerId) {
      setEditingPeerId(null)
    }
  }

  const handleInitiate = async (peerId: number) => {
    const peer = peers.find((p) => p.peerId === peerId)
    try {
      const result = await initiatePeer(peerId)
      const description =
        result.initiationMessage ||
        `Tunnel for peer "${peer?.name}" is being brought up`
      toaster.success({
        title: 'Tunnel Initiation',
        description,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to initiate tunnel'
      toaster.error({
        title: 'Tunnel Initiation Failed',
        description: message,
      })
    }
  }

  const handleToggleEnabled = async (peerId: number, enabled: boolean) => {
    const peer = peers.find((p) => p.peerId === peerId)
    try {
      const result = await toggleEnabled(peerId, enabled)
      toaster.success({
        title: enabled ? 'Peer Enabled' : 'Peer Disabled',
        description: `Peer "${peer?.name}" has been ${enabled ? 'enabled' : 'disabled'}`,
      })
      if (result.warning) {
        toaster.warning({
          title: 'Daemon Warning',
          description: result.warning,
        })
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update peer'
      toaster.error({
        title: 'Update Failed',
        description: message,
      })
    }
  }

  const editingPeer = editingPeerId !== null
    ? peers.find((p) => p.peerId === editingPeerId)
    : null

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
                IPsec Peer Configuration
              </Heading>
              <Text maxW="lg" color="gray.600">
                Manage IPsec peers with encrypted pre-shared keys and tunnel parameters.
              </Text>
            </Box>
            <HStack gap={2}>
              <Button onClick={() => navigate('/dashboard')} variant="outline" size="sm">
                Dashboard
              </Button>
              <Button onClick={() => navigate('/interfaces')} variant="outline" size="sm">
                Interfaces
              </Button>
              <Button onClick={() => navigate('/routes')} variant="outline" size="sm">
                Routes
              </Button>
              <Button onClick={handleLogout} variant="outline" size="sm">
                Logout{user ? ` (${user.username})` : ''}
              </Button>
            </HStack>
          </HStack>

          {deleteSuccess && (
            <Box bg="green.50" border="1px solid" borderColor="green.200" color="green.700" px={4} py={3} rounded="md">
              {deleteSuccess}
            </Box>
          )}

          {error && (
            <Box bg="red.50" border="1px solid" borderColor="red.200" color="red.700" px={4} py={3} rounded="md">
              {error}
            </Box>
          )}

          {loading && (
            <Text color="gray.500">Loading peers...</Text>
          )}

          <HStack>
            <Button
              colorPalette="orange"
              onClick={() => { setShowCreateForm(true); setEditingPeerId(null) }}
              disabled={showCreateForm}
            >
              Add Peer
            </Button>
          </HStack>

          {peers.length === 0 && !loading && !showCreateForm && (
            <Box
              border="1px dashed"
              borderColor="gray.300"
              borderRadius="16px"
              padding={8}
              textAlign="center"
              color="gray.500"
            >
              <Text>No peers configured yet. Click "Add Peer" to create one.</Text>
            </Box>
          )}

          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={6}>
            {peers.map((peer) => (
              <PeerCard
                key={peer.peerId}
                peer={peer}
                onEdit={(id) => { setEditingPeerId(id); setShowCreateForm(false) }}
                onDelete={handleDelete}
                onToggleEnabled={handleToggleEnabled}
                onInitiate={handleInitiate}
              />
            ))}
          </SimpleGrid>

          {showCreateForm && (
            <PeerForm
              mode="create"
              onSubmit={handleCreate}
              onCancel={() => setShowCreateForm(false)}
            />
          )}

          {editingPeer && (
            <PeerForm
              mode="edit"
              initialData={{
                name: editingPeer.name,
                remoteIp: editingPeer.remoteIp,
                ikeVersion: editingPeer.ikeVersion,
                dpdAction: editingPeer.dpdAction || 'restart',
                dpdDelay: String(editingPeer.dpdDelay ?? 30),
                dpdTimeout: String(editingPeer.dpdTimeout ?? 150),
                rekeyTime: String(editingPeer.rekeyTime ?? 3600),
              }}
              onSubmit={handleUpdate}
              onCancel={() => setEditingPeerId(null)}
            />
          )}
        </Stack>
      </Container>
    </Box>
  )
}
