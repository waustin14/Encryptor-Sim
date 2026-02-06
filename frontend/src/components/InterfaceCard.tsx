import { Badge, Box, HStack, Stack, Text } from '@chakra-ui/react'
import type { InterfaceConfig } from '../state/interfacesStore'

type InterfaceCardProps = {
  config: InterfaceConfig
  onConfigure: (name: string) => void
}

const getStatusInfo = (config: InterfaceConfig) => {
  if (config.ipAddress) {
    return { label: 'Configured', colorScheme: 'green' }
  }
  return { label: 'Unconfigured', colorScheme: 'gray' }
}

const INTERFACE_LABELS: Record<string, string> = {
  CT: 'Cleartext (CT)',
  PT: 'Plaintext (PT)',
  MGMT: 'Management (MGMT)',
}

export function InterfaceCard({ config, onConfigure }: InterfaceCardProps) {
  const status = getStatusInfo(config)
  const label = INTERFACE_LABELS[config.name] || config.name

  return (
    <Box
      border="1px solid"
      borderColor="gray.200"
      borderRadius="16px"
      padding={{ base: 4, md: 6 }}
      background="whiteAlpha.900"
      boxShadow="md"
      cursor="pointer"
      onClick={() => onConfigure(config.name)}
      _hover={{ borderColor: 'orange.300', boxShadow: 'lg' }}
      transition="all 0.2s"
    >
      <HStack justify="space-between" align="flex-start" mb={3}>
        <Box>
          <Text fontSize="sm" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
            {config.namespace} / {config.device}
          </Text>
          <Text fontSize="lg" fontWeight="600">
            {label}
          </Text>
        </Box>
        <Badge
          colorPalette={status.colorScheme}
          fontSize="0.8rem"
          paddingX={3}
          paddingY={1}
          borderRadius="999px"
        >
          {status.label}
        </Badge>
      </HStack>

      <Stack gap={1}>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="80px">IP Address</Text>
          <Text fontSize="sm" fontFamily="mono">{config.ipAddress || '—'}</Text>
        </HStack>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="80px">Netmask</Text>
          <Text fontSize="sm" fontFamily="mono">{config.netmask || '—'}</Text>
        </HStack>
        <HStack>
          <Text fontSize="sm" color="gray.500" minW="80px">Gateway</Text>
          <Text fontSize="sm" fontFamily="mono">{config.gateway || '—'}</Text>
        </HStack>
      </Stack>
    </Box>
  )
}
