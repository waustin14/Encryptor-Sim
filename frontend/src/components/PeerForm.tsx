import { useState } from 'react'
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

type PeerFormData = {
  name: string
  remoteIp: string
  psk: string
  ikeVersion: string
  dpdAction: string
  dpdDelay: string
  dpdTimeout: string
  rekeyTime: string
}

type PeerFormProps = {
  mode: 'create' | 'edit'
  initialData?: Partial<PeerFormData>
  onSubmit: (data: PeerFormData) => Promise<void>
  onCancel: () => void
}

const IPV4_PATTERN = /^(\d{1,3}\.){3}\d{1,3}$/
const VALID_IKE_VERSIONS = ['ikev1', 'ikev2']
const VALID_DPD_ACTIONS = ['clear', 'hold', 'restart']

function validateForm(data: PeerFormData, mode: 'create' | 'edit'): string | null {
  if (mode === 'create' && !data.name.trim()) return 'Name is required'

  if (mode === 'create' || data.remoteIp) {
    if (!IPV4_PATTERN.test(data.remoteIp)) return 'Invalid IP address format'
    const octets = data.remoteIp.split('.').map(Number)
    if (octets.some((o) => o < 0 || o > 255)) return 'IP octets must be 0-255'
    if (data.remoteIp === '0.0.0.0') return 'Reserved address not allowed'
    if (data.remoteIp === '255.255.255.255') return 'Broadcast address not allowed'
    if (data.remoteIp.startsWith('127.')) return 'Loopback address not allowed'
  }

  if (mode === 'create' && !data.psk.trim()) return 'Pre-shared key is required'

  const ikeVersion = data.ikeVersion.toLowerCase()
  if (!VALID_IKE_VERSIONS.includes(ikeVersion)) {
    return 'IKE version must be ikev1 or ikev2'
  }

  if (data.dpdAction && !VALID_DPD_ACTIONS.includes(data.dpdAction)) {
    return 'DPD action must be clear, hold, or restart'
  }

  if (data.dpdDelay) {
    const delay = parseInt(data.dpdDelay, 10)
    if (isNaN(delay) || delay < 10 || delay > 300) return 'DPD delay must be 10-300 seconds'
  }

  if (data.dpdTimeout) {
    const timeout = parseInt(data.dpdTimeout, 10)
    if (isNaN(timeout) || timeout < 10 || timeout > 600) return 'DPD timeout must be 10-600 seconds'
  }

  if (data.dpdDelay && data.dpdTimeout) {
    const delay = parseInt(data.dpdDelay, 10)
    const timeout = parseInt(data.dpdTimeout, 10)
    if (!isNaN(delay) && !isNaN(timeout) && timeout <= delay) {
      return 'DPD timeout must be greater than DPD delay'
    }
  }

  if (data.rekeyTime) {
    const rekey = parseInt(data.rekeyTime, 10)
    if (isNaN(rekey) || rekey < 300 || rekey > 86400) return 'Rekey time must be 300-86400 seconds'
  }

  return null
}

export function PeerForm({ mode, initialData, onSubmit, onCancel }: PeerFormProps) {
  const [formData, setFormData] = useState<PeerFormData>({
    name: initialData?.name || '',
    remoteIp: initialData?.remoteIp || '',
    psk: '',
    ikeVersion: initialData?.ikeVersion || 'ikev2',
    dpdAction: initialData?.dpdAction || 'restart',
    dpdDelay: initialData?.dpdDelay || '30',
    dpdTimeout: initialData?.dpdTimeout || '150',
    rekeyTime: initialData?.rekeyTime || '3600',
  })
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const handleChange = (field: keyof PeerFormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
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
        {mode === 'create' ? 'Add New Peer' : `Edit Peer: ${initialData?.name || ''}`}
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
              <Field.Label>Peer Name</Field.Label>
              <Input
                value={formData.name}
                onChange={handleChange('name')}
                placeholder="site-a-encryptor"
              />
            </Field.Root>
          )}

          <Field.Root required={mode === 'create'}>
            <Field.Label>Remote IP Address</Field.Label>
            <Input
              value={formData.remoteIp}
              onChange={handleChange('remoteIp')}
              placeholder="10.1.1.100"
              fontFamily="mono"
            />
          </Field.Root>

          <Field.Root required={mode === 'create'}>
            <Field.Label>Pre-Shared Key{mode === 'edit' ? ' (leave blank to keep current)' : ''}</Field.Label>
            <Input
              type="password"
              value={formData.psk}
              onChange={handleChange('psk')}
              placeholder="Enter pre-shared key"
            />
          </Field.Root>

          <Field.Root required>
            <Field.Label>IKE Version</Field.Label>
            <Input
              value={formData.ikeVersion}
              onChange={handleChange('ikeVersion')}
              placeholder="ikev2"
            />
            <Text fontSize="xs" color="gray.500">ikev1 or ikev2</Text>
          </Field.Root>

          <Field.Root>
            <Field.Label>DPD Action</Field.Label>
            <Input
              value={formData.dpdAction}
              onChange={handleChange('dpdAction')}
              placeholder="restart"
            />
            <Text fontSize="xs" color="gray.500">clear, hold, or restart</Text>
          </Field.Root>

          <HStack gap={4}>
            <Field.Root>
              <Field.Label>DPD Delay (s)</Field.Label>
              <Input
                type="number"
                value={formData.dpdDelay}
                onChange={handleChange('dpdDelay')}
                placeholder="30"
              />
            </Field.Root>

            <Field.Root>
              <Field.Label>DPD Timeout (s)</Field.Label>
              <Input
                type="number"
                value={formData.dpdTimeout}
                onChange={handleChange('dpdTimeout')}
                placeholder="150"
              />
            </Field.Root>
          </HStack>

          <Field.Root>
            <Field.Label>Rekey Time (s)</Field.Label>
            <Input
              type="number"
              value={formData.rekeyTime}
              onChange={handleChange('rekeyTime')}
              placeholder="3600"
            />
          </Field.Root>

          <HStack gap={3}>
            <Button type="submit" colorPalette="orange" loading={saving}>
              {mode === 'create' ? 'Create Peer' : 'Save Changes'}
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
