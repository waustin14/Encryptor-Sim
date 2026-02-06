import { useState } from 'react'
import { Badge, Box, Button, HStack, Stack, Text } from '@chakra-ui/react'
import type { Peer } from '../state/peersStore'

type PeerCardProps = {
  peer: Peer
  onEdit: (peerId: number) => void
  onDelete: (peerId: number) => Promise<void>
  onInitiate: (peerId: number) => Promise<void>
  onToggleEnabled: (peerId: number, enabled: boolean) => Promise<void>
}

export function PeerCard({ peer, onEdit, onDelete, onInitiate, onToggleEnabled }: PeerCardProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [initiating, setInitiating] = useState(false)
  const [confirmingDisable, setConfirmingDisable] = useState(false)
  const [toggling, setToggling] = useState(false)

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setConfirmingDelete(true)
    setDeleteError(null)
  }

  const handleConfirmDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setDeleting(true)
    setDeleteError(null)
    try {
      await onDelete(peer.peerId)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete peer'
      setDeleteError(message)
      setDeleting(false)
    }
  }

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setConfirmingDelete(false)
  }

  const handleInitiate = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setInitiating(true)
    try {
      await onInitiate(peer.peerId)
    } finally {
      setInitiating(false)
    }
  }

  const handleToggleEnabledClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!peer.enabled) {
      // Enabling - do it immediately
      handleConfirmToggleEnabled()
    } else {
      // Disabling - show confirmation
      setConfirmingDisable(true)
    }
  }

  const handleConfirmToggleEnabled = async () => {
    setToggling(true)
    try {
      await onToggleEnabled(peer.peerId, !peer.enabled)
    } finally {
      setToggling(false)
      setConfirmingDisable(false)
    }
  }

  const handleCancelDisable = (e: React.MouseEvent) => {
    e.stopPropagation()
    setConfirmingDisable(false)
  }

  return (
    <Box
      border="1px solid"
      borderColor="gray.200"
      borderRadius="16px"
      padding={{ base: 4, md: 6 }}
      background="whiteAlpha.900"
      boxShadow="md"
      cursor="pointer"
      onClick={() => onEdit(peer.peerId)}
      _hover={{ borderColor: 'orange.300', boxShadow: 'lg' }}
      transition="all 0.2s"
    >
      <HStack justify="space-between" align="flex-start" mb={3}>
        <Box>
          <Text fontSize="sm" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
            {peer.remoteIp}
          </Text>
          <Text fontSize="lg" fontWeight="600">
            {peer.name}
          </Text>
        </Box>
        <HStack gap={2}>
          <Badge
            colorPalette="blue"
            fontSize="0.8rem"
            paddingX={3}
            paddingY={1}
            borderRadius="999px"
          >
            {peer.ikeVersion.toUpperCase()}
          </Badge>
          {!peer.enabled && (
            <Badge
              colorPalette="gray"
              fontSize="0.8rem"
              paddingX={3}
              paddingY={1}
              borderRadius="999px"
              data-testid="disabled-badge"
              title="Peer is disabled. Enable to allow tunnel operations."
            >
              Disabled
            </Badge>
          )}
          <Badge
            colorPalette={peer.operationalStatus === 'ready' ? 'green' : 'yellow'}
            fontSize="0.8rem"
            paddingX={3}
            paddingY={1}
            borderRadius="999px"
            data-testid="operational-status-badge"
            title={
              peer.operationalStatus === 'ready'
                ? 'All required fields configured. Peer is ready for tunnel establishment.'
                : 'Missing required fields or invalid configuration. Complete all fields to mark peer as ready.'
            }
          >
            {peer.operationalStatus === 'ready' ? 'Ready' : 'Incomplete'}
          </Badge>
          {!confirmingDelete && !confirmingDisable && (
            <>
              <Button
                size="xs"
                colorPalette="orange"
                variant="outline"
                onClick={handleInitiate}
                disabled={peer.operationalStatus !== 'ready' || initiating || !peer.enabled}
                loading={initiating}
                aria-label={`Bring up tunnel for ${peer.name}`}
                data-testid="initiate-button"
                title={!peer.enabled ? 'Enable peer to initiate tunnel' : undefined}
              >
                Bring Up Tunnel
              </Button>
              <Button
                size="xs"
                colorPalette={peer.enabled ? 'yellow' : 'green'}
                variant="outline"
                onClick={handleToggleEnabledClick}
                disabled={toggling}
                loading={toggling}
                aria-label={peer.enabled ? `Disable peer ${peer.name}` : `Enable peer ${peer.name}`}
                data-testid="toggle-enabled-button"
              >
                {peer.enabled ? 'Disable' : 'Enable'}
              </Button>
              <Button
                size="xs"
                colorPalette="red"
                variant="outline"
                onClick={handleDeleteClick}
                aria-label={`Delete peer ${peer.name}`}
              >
                Delete
              </Button>
            </>
          )}
        </HStack>
      </HStack>

      {confirmingDelete && (
        <Box
          bg="red.50"
          border="1px solid"
          borderColor="red.200"
          borderRadius="8px"
          padding={3}
          mb={3}
        >
          <Text fontSize="sm" color="red.700" mb={2}>
            Delete peer "{peer.name}"? This cannot be undone.
          </Text>
          {deleteError && (
            <Text fontSize="sm" color="red.600" mb={2} fontWeight="600">
              Error: {deleteError}
            </Text>
          )}
          <HStack gap={2}>
            <Button
              size="xs"
              colorPalette="red"
              onClick={handleConfirmDelete}
              loading={deleting}
              aria-label="Confirm delete"
            >
              Confirm Delete
            </Button>
            <Button
              size="xs"
              variant="outline"
              onClick={handleCancelDelete}
              disabled={deleting}
              aria-label="Cancel delete"
            >
              Cancel
            </Button>
          </HStack>
        </Box>
      )}

      {confirmingDisable && (
        <Box
          bg="yellow.50"
          border="1px solid"
          borderColor="yellow.200"
          borderRadius="8px"
          padding={3}
          mb={3}
          data-testid="disable-confirmation"
        >
          <Text fontSize="sm" color="yellow.800" mb={2}>
            Disable peer "{peer.name}"? This will tear down any active tunnel and remove strongSwan configuration.
          </Text>
          <HStack gap={2}>
            <Button
              size="xs"
              colorPalette="yellow"
              onClick={handleConfirmToggleEnabled}
              loading={toggling}
              aria-label="Confirm disable"
              data-testid="confirm-disable-button"
            >
              Confirm Disable
            </Button>
            <Button
              size="xs"
              variant="outline"
              onClick={handleCancelDisable}
              disabled={toggling}
              aria-label="Cancel"
            >
              Cancel
            </Button>
          </HStack>
        </Box>
      )}

      <Stack gap={1}>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="90px">Remote IP</Text>
          <Text fontSize="sm" fontFamily="mono">{peer.remoteIp}</Text>
        </HStack>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="90px">DPD Action</Text>
          <Text fontSize="sm">{peer.dpdAction || 'restart'}</Text>
        </HStack>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="90px">DPD Delay</Text>
          <Text fontSize="sm">{peer.dpdDelay ?? 30}s</Text>
        </HStack>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="90px">DPD Timeout</Text>
          <Text fontSize="sm">{peer.dpdTimeout ?? 150}s</Text>
        </HStack>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="90px">Rekey Time</Text>
          <Text fontSize="sm">{peer.rekeyTime ?? 3600}s</Text>
        </HStack>
      </Stack>

      {peer.operationalStatus === 'incomplete' && (
        <Text color="orange.500" fontSize="sm" mt={2} data-testid="incomplete-warning">
          This peer is incomplete. Configure all required fields (name, remote IP, PSK, IKE version) to enable tunnel operations.
        </Text>
      )}
    </Box>
  )
}
