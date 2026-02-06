/**
 * InterfaceStatsCard component for displaying real-time interface statistics.
 *
 * Shows bytes/packets/errors with human-readable formatting.
 */

import { Box, HStack, SimpleGrid, Stack, Text } from '@chakra-ui/react'
import type { InterfaceStats } from '../state/interfacesStore'

type InterfaceStatsCardProps = {
  interfaceName: string
  stats: InterfaceStats
}

const INTERFACE_LABELS: Record<string, string> = {
  CT: 'Cleartext (CT)',
  PT: 'Plaintext (PT)',
  MGMT: 'Management (MGMT)',
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`
  }
  return num.toString()
}

export function InterfaceStatsCard({ interfaceName, stats }: InterfaceStatsCardProps) {
  const label = INTERFACE_LABELS[interfaceName] || interfaceName

  return (
    <Box
      border="1px solid"
      borderColor="gray.200"
      borderRadius="16px"
      padding={{ base: 4, md: 5 }}
      background="whiteAlpha.900"
      boxShadow="md"
    >
      <HStack justify="space-between" align="flex-start" mb={4}>
        <Text fontSize="lg" fontWeight="600">
          {label}
        </Text>
        <Text fontSize="xs" color="gray.500">
          {new Date(stats.timestamp).toLocaleTimeString()}
        </Text>
      </HStack>

      <SimpleGrid columns={2} gap={4}>
        <Stack gap={1}>
          <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.05em">
            Bytes Rx / Tx
          </Text>
          <Text fontSize="sm" fontFamily="mono" data-testid={`stats-${interfaceName}-bytes`}>
            {formatBytes(stats.bytesRx)} / {formatBytes(stats.bytesTx)}
          </Text>
        </Stack>

        <Stack gap={1}>
          <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.05em">
            Packets Rx / Tx
          </Text>
          <Text fontSize="sm" fontFamily="mono" data-testid={`stats-${interfaceName}-packets`}>
            {formatNumber(stats.packetsRx)} / {formatNumber(stats.packetsTx)}
          </Text>
        </Stack>

        <Stack gap={1}>
          <Text fontSize="xs" color="gray.500" textTransform="uppercase" letterSpacing="0.05em">
            Errors Rx / Tx
          </Text>
          <Text
            fontSize="sm"
            fontFamily="mono"
            color={stats.errorsRx > 0 || stats.errorsTx > 0 ? 'red.500' : 'inherit'}
            data-testid={`stats-${interfaceName}-errors`}
          >
            {stats.errorsRx} / {stats.errorsTx}
          </Text>
        </Stack>
      </SimpleGrid>
    </Box>
  )
}
