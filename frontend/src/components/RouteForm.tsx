import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Field,
  Heading,
  HStack,
  Input,
  Stack,
  Text,
} from '@chakra-ui/react'
import { usePeersStore } from '../state/peersStore'
import type { Peer } from '../state/peersStore'

type RouteFormData = {
  peerId: string
  destinationCidr: string
}

type RouteFormProps = {
  mode: 'create' | 'edit'
  initialData?: Partial<RouteFormData>
  onSubmit: (data: RouteFormData) => Promise<void>
  onCancel: () => void
}

const CIDR_PATTERN = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/

function validateCidr(cidr: string): string | null {
  if (!cidr.trim()) return 'Destination CIDR is required'
  if (!CIDR_PATTERN.test(cidr)) return 'Invalid CIDR format (e.g., 192.168.1.0/24)'

  const [ip, prefix] = cidr.split('/')
  const octets = ip.split('.').map(Number)
  if (octets.some((o) => o < 0 || o > 255)) return 'IP octets must be 0-255'

  const prefixLen = parseInt(prefix, 10)
  if (prefixLen < 0 || prefixLen > 32) return 'Prefix length must be 0-32'

  return null
}

function validateForm(data: RouteFormData, mode: 'create' | 'edit'): string | null {
  if (mode === 'create' && !data.peerId) return 'Peer selection is required'

  const cidrError = validateCidr(data.destinationCidr)
  if (cidrError) return cidrError

  return null
}

export function RouteForm({ mode, initialData, onSubmit, onCancel }: RouteFormProps) {
  const { peers, fetchPeers } = usePeersStore()
  const [formData, setFormData] = useState<RouteFormData>({
    peerId: initialData?.peerId || '',
    destinationCidr: initialData?.destinationCidr || '',
  })
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (mode === 'create' && peers.length === 0) {
      fetchPeers()
    }
  }, [mode, peers.length, fetchPeers])

  const handleChange = (field: keyof RouteFormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validateForm(formData, mode)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setSaving(true)
    try {
      await onSubmit(formData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Box
      border="1px solid"
      borderColor="orange.200"
      borderRadius="16px"
      padding={{ base: 4, md: 6 }}
      background="white"
      boxShadow="lg"
    >
      <Heading size="md" mb={4}>
        {mode === 'create' ? 'Add New Route' : 'Edit Route'}
      </Heading>

      {error && (
        <Box bg="red.50" border="1px solid" borderColor="red.200" color="red.700" px={4} py={3} rounded="md" mb={4}>
          {error}
        </Box>
      )}

      <form onSubmit={handleSubmit}>
        <Stack gap={4}>
          {mode === 'create' && (
            <Field.Root required>
              <Field.Label>Peer</Field.Label>
              <select
                value={formData.peerId}
                onChange={handleChange('peerId') as (e: React.ChangeEvent<HTMLSelectElement>) => void}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid #e2e8f0',
                  fontSize: '14px',
                }}
                aria-label="Select peer"
              >
                <option value="">Select a peer...</option>
                {peers.map((peer: Peer) => (
                  <option key={peer.peerId} value={String(peer.peerId)}>
                    {peer.name} ({peer.remoteIp})
                  </option>
                ))}
              </select>
            </Field.Root>
          )}

          <Field.Root required>
            <Field.Label>Destination CIDR</Field.Label>
            <Input
              value={formData.destinationCidr}
              onChange={handleChange('destinationCidr')}
              placeholder="192.168.1.0/24"
              fontFamily="mono"
              aria-label="Destination CIDR"
            />
            <Text fontSize="xs" color="gray.500">IPv4 CIDR notation (e.g., 192.168.1.0/24, 10.0.0.0/8)</Text>
          </Field.Root>

          <HStack gap={3}>
            <Button type="submit" colorPalette="orange" loading={saving}>
              {mode === 'create' ? 'Create Route' : 'Save Changes'}
            </Button>
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          </HStack>
        </Stack>
      </form>
    </Box>
  )
}
