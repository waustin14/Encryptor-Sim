import { useState } from 'react'
import { Badge, Box, Button, HStack, Text } from '@chakra-ui/react'
import type { Route } from '../state/routesStore'

type RouteCardProps = {
  route: Route
  onEdit: (routeId: number) => void
  onDelete: (routeId: number) => Promise<void>
}

export function RouteCard({ route, onEdit, onDelete }: RouteCardProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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
      await onDelete(route.routeId)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete route'
      setDeleteError(message)
      setDeleting(false)
    }
  }

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setConfirmingDelete(false)
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
      onClick={() => onEdit(route.routeId)}
      _hover={{ borderColor: 'orange.300', boxShadow: 'lg' }}
      transition="all 0.2s"
    >
      <HStack justify="space-between" align="flex-start" mb={3}>
        <Box>
          <Text fontSize="sm" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
            Route
          </Text>
          <Text fontSize="lg" fontWeight="600" fontFamily="mono">
            {route.destinationCidr}
          </Text>
        </Box>
        <HStack gap={2}>
          <Badge
            colorPalette="green"
            fontSize="0.8rem"
            paddingX={3}
            paddingY={1}
            borderRadius="999px"
          >
            {route.peerName}
          </Badge>
          {!confirmingDelete && (
            <Button
              size="xs"
              colorPalette="red"
              variant="outline"
              onClick={handleDeleteClick}
              aria-label={`Delete route ${route.destinationCidr}`}
            >
              Delete
            </Button>
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
            Delete route "{route.destinationCidr}"? This cannot be undone.
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

      <HStack>
        <Text fontSize="sm" color="gray.500" minW="70px">Peer</Text>
        <Text fontSize="sm">{route.peerName}</Text>
      </HStack>
    </Box>
  )
}
