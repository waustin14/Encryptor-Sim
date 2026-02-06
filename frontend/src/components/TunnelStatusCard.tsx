/**
 * TunnelStatusCard component for displaying real-time tunnel status.
 *
 * Shows peer name, tunnel status with color-coded badges, establishment time,
 * and traffic-flow indicator:
 * - green: up
 * - red: down
 * - yellow: negotiating
 * - gray: unknown
 */

import { Badge, Box, HStack, VStack, Text } from '@chakra-ui/react'
import type { TunnelStatus } from '../state/tunnelsStore'

type TunnelStatusCardProps = {
  tunnel: TunnelStatus
}

const STATUS_COLORS: Record<TunnelStatus['status'], string> = {
  up: 'green',
  down: 'red',
  negotiating: 'yellow',
  unknown: 'gray',
}

const STATUS_LABELS: Record<TunnelStatus['status'], string> = {
  up: 'Up',
  down: 'Down',
  negotiating: 'Negotiating',
  unknown: 'Unknown',
}

/**
 * Format seconds into human-readable duration (e.g., "1h 23m", "45s").
 */
function formatDuration(seconds: number): string {
  if (seconds === 0) return '0s'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  }
  if (minutes > 0) {
    return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`
  }
  return `${secs}s`
}

export function TunnelStatusCard({ tunnel }: TunnelStatusCardProps) {
  const colorScheme = STATUS_COLORS[tunnel.status] || 'gray'
  const label = STATUS_LABELS[tunnel.status] || tunnel.status

  // Only show telemetry for 'up' tunnels (AC: #2, Task 3.4)
  const showTelemetry = tunnel.status === 'up'

  return (
    <Box
      border="1px solid"
      borderColor="gray.200"
      borderRadius="12px"
      padding={4}
      background="whiteAlpha.900"
      boxShadow="sm"
    >
      <HStack justify="space-between" align="flex-start">
        <VStack align="flex-start" gap={1} flex={1}>
          <Text fontSize="md" fontWeight="600">
            {tunnel.peerName}
          </Text>

          {/* Establishment time (AC: #2) */}
          {showTelemetry && tunnel.establishedSec > 0 && (
            <Text fontSize="xs" color="gray.600" data-testid="tunnel-established">
              Established: {formatDuration(tunnel.establishedSec)}
            </Text>
          )}

          {/* Traffic flow indicator (AC: #1, #4) */}
          {showTelemetry && (
            <Badge
              colorPalette={tunnel.isPassingTraffic ? 'green' : 'gray'}
              fontSize="0.75rem"
              paddingX={2}
              paddingY={0.5}
              borderRadius="999px"
              data-testid="tunnel-traffic-indicator"
            >
              {tunnel.isPassingTraffic ? 'Passing Traffic' : 'Idle'}
            </Badge>
          )}

          <Text fontSize="xs" color="gray.500">
            Last updated: {new Date(tunnel.lastUpdated).toLocaleTimeString()}
          </Text>
        </VStack>

        <Badge
          colorPalette={colorScheme}
          fontSize="0.85rem"
          paddingX={3}
          paddingY={1}
          borderRadius="999px"
          data-testid={`tunnel-status-${tunnel.peerName}`}
        >
          {label}
        </Badge>
      </HStack>
    </Box>
  )
}
