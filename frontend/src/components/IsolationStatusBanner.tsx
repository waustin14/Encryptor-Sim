import {
  AlertContent,
  AlertDescription,
  AlertIndicator,
  AlertRoot,
  AlertTitle,
  Badge,
  Box,
  HStack,
  Stack,
  Text,
} from '@chakra-ui/react'
import type { IsolationStatus } from '../state/systemStatus'

type IsolationStatusBannerProps = {
  status: IsolationStatus | null
  isLoading: boolean
  error: string | null
}

const formatTimestamp = (value?: string) => {
  if (!value) {
    return 'Not yet run'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

const getStatusTone = (status?: string) => {
  if (status === 'fail') {
    return { label: 'Failed', colorScheme: 'red' }
  }
  if (status === 'pass') {
    return { label: 'Passed', colorScheme: 'green' }
  }
  return { label: 'Unknown', colorScheme: 'gray' }
}

export function IsolationStatusBanner({
  status,
  isLoading,
  error,
}: IsolationStatusBannerProps) {
  const tone = getStatusTone(status?.status)
  const lastRun = formatTimestamp(status?.timestamp)
  const primaryFailure = status?.failures?.[0]

  return (
    <Stack gap={4}>
      <Box
        border="1px solid"
        borderColor="gray.200"
        borderRadius="16px"
        padding={{ base: 4, md: 6 }}
        background="whiteAlpha.900"
        boxShadow="lg"
      >
        <HStack gap={4} justify="space-between" flexWrap="wrap">
          <Box>
            <Text fontSize="sm" color="gray.500" textTransform="uppercase" letterSpacing="0.08em">
              Isolation Validation
            </Text>
            <Text fontSize="lg" fontWeight="600">
              Status signal is always visible for operators
            </Text>
            <Text fontSize="sm" color="gray.600">
              Last run: {lastRun}
            </Text>
            {error ? (
              <Text fontSize="sm" color="red.600">
                Status load error: {error}
              </Text>
            ) : null}
            {isLoading ? (
              <Text fontSize="sm" color="gray.500">
                Loading latest status...
              </Text>
            ) : null}
          </Box>
          <Badge
            colorPalette={tone.colorScheme}
            fontSize="0.9rem"
            paddingX={4}
            paddingY={2}
            borderRadius="999px"
          >
            {tone.label}
          </Badge>
        </HStack>
      </Box>

      {status?.status === 'fail' ? (
        <AlertRoot status="error" variant="solid" borderRadius="16px">
          <AlertIndicator />
          <AlertContent>
            <AlertTitle>Isolation validation failed</AlertTitle>
            <AlertDescription>
              {primaryFailure
                ? `Primary failure: ${primaryFailure}`
                : 'Review the system logs for detailed failure context.'}
              <Text marginTop={2} fontSize="sm">
                Last run: {lastRun}
              </Text>
            </AlertDescription>
          </AlertContent>
        </AlertRoot>
      ) : null}
    </Stack>
  )
}
