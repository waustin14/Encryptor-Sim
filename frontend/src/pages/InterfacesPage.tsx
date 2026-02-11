import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Container,
  Field,
  Heading,
  HStack,
  Input,
  SimpleGrid,
  Stack,
  Text,
} from '@chakra-ui/react'

import { InterfaceCard } from '../components/InterfaceCard'
import { NavBar } from '../components/NavBar'
import { useInterfacesStore } from '../state/interfacesStore'

const IPV4_PATTERN = /^(\d{1,3}\.){3}\d{1,3}$/

function validateIpAddress(value: string): string | null {
  if (!IPV4_PATTERN.test(value)) return 'Invalid IP address format'
  const octets = value.split('.').map(Number)
  if (octets.some((o) => o < 0 || o > 255)) return 'IP octets must be 0-255'
  if (value === '0.0.0.0') return 'Reserved address not allowed'
  if (value === '255.255.255.255') return 'Broadcast address not allowed'
  return null
}

function validateNetmask(value: string): string | null {
  if (!IPV4_PATTERN.test(value)) return 'Invalid netmask format'
  const octets = value.split('.').map(Number)
  if (octets.some((o) => o < 0 || o > 255)) return 'Netmask octets must be 0-255'
  const binary = octets.map((o) => o.toString(2).padStart(8, '0')).join('')
  const zeroIndex = binary.indexOf('0')
  if (zeroIndex !== -1 && binary.indexOf('1', zeroIndex) !== -1) {
    return 'Invalid netmask: must be contiguous'
  }
  return null
}

function validateGateway(value: string): string | null {
  if (!IPV4_PATTERN.test(value)) return 'Invalid gateway format'
  const octets = value.split('.').map(Number)
  if (octets.some((o) => o < 0 || o > 255)) return 'Gateway octets must be 0-255'
  return null
}

function validateGatewayInSubnet(gateway: string, ipAddress: string, netmask: string): string | null {
  try {
    const ipOctets = ipAddress.split('.').map(Number)
    const maskOctets = netmask.split('.').map(Number)
    const gwOctets = gateway.split('.').map(Number)

    // Calculate network address for IP
    const ipNetwork = ipOctets.map((octet, i) => octet & maskOctets[i])

    // Calculate network address for gateway
    const gwNetwork = gwOctets.map((octet, i) => octet & maskOctets[i])

    // Check if both are in same network
    if (!ipNetwork.every((octet, i) => octet === gwNetwork[i])) {
      return `Gateway must be in same subnet as IP address`
    }

    return null
  } catch {
    return 'Unable to validate gateway subnet'
  }
}

export function InterfacesPage() {
  const { interfaces, loading, error, fetchInterfaces, updateInterface } = useInterfacesStore()

  const [editingName, setEditingName] = useState<string | null>(null)
  const [formIp, setFormIp] = useState('')
  const [formNetmask, setFormNetmask] = useState('')
  const [formGateway, setFormGateway] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchInterfaces()
  }, [fetchInterfaces])

  const handleConfigure = (name: string) => {
    const iface = interfaces.find((i) => i.name === name)
    setEditingName(name)
    setFormIp(iface?.ipAddress || '')
    setFormNetmask(iface?.netmask || '')
    setFormGateway(iface?.gateway || '')
    setFormError(null)
  }

  const handleCancel = () => {
    setEditingName(null)
    setFormError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingName) return

    const ipErr = validateIpAddress(formIp)
    if (ipErr) { setFormError(ipErr); return }

    const maskErr = validateNetmask(formNetmask)
    if (maskErr) { setFormError(maskErr); return }

    const gwErr = validateGateway(formGateway)
    if (gwErr) { setFormError(gwErr); return }

    const subnetErr = validateGatewayInSubnet(formGateway, formIp, formNetmask)
    if (subnetErr) { setFormError(subnetErr); return }

    setFormError(null)
    setSaving(true)

    try {
      await updateInterface(editingName, {
        ipAddress: formIp,
        netmask: formNetmask,
        gateway: formGateway,
      })
      setEditingName(null)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Configuration failed')
    } finally {
      setSaving(false)
    }
  }

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
                Interface Configuration
              </Heading>
              <Text maxW="lg" color="gray.600">
                Configure IP settings for CT, PT, and MGMT network interfaces.
              </Text>
            </Box>
            <NavBar />
          </HStack>

          {error && (
            <Box bg="red.50" border="1px solid" borderColor="red.200" color="red.700" px={4} py={3} rounded="md">
              {error}
            </Box>
          )}

          {loading && (
            <Text color="gray.500">Loading interfaces...</Text>
          )}

          <SimpleGrid columns={{ base: 1, md: 3 }} gap={6}>
            {interfaces.map((iface) => (
              <InterfaceCard
                key={iface.interfaceId}
                config={iface}
                onConfigure={handleConfigure}
              />
            ))}
          </SimpleGrid>

          {editingName && (
            <Box
              border="1px solid"
              borderColor="orange.200"
              borderRadius="16px"
              padding={{ base: 4, md: 6 }}
              background="white"
              boxShadow="lg"
            >
              <Heading size="md" mb={4}>
                Configure {editingName} Interface
              </Heading>

              {formError && (
                <Box bg="red.50" border="1px solid" borderColor="red.200" color="red.700" px={4} py={3} rounded="md" mb={4}>
                  {formError}
                </Box>
              )}

              <form onSubmit={handleSubmit}>
                <Stack gap={4}>
                  <Field.Root required>
                    <Field.Label>IP Address</Field.Label>
                    <Input
                      value={formIp}
                      onChange={(e) => setFormIp(e.target.value)}
                      placeholder="192.168.10.1"
                      fontFamily="mono"
                    />
                  </Field.Root>

                  <Field.Root required>
                    <Field.Label>Netmask</Field.Label>
                    <Input
                      value={formNetmask}
                      onChange={(e) => setFormNetmask(e.target.value)}
                      placeholder="255.255.255.0"
                      fontFamily="mono"
                    />
                  </Field.Root>

                  <Field.Root required>
                    <Field.Label>Gateway</Field.Label>
                    <Input
                      value={formGateway}
                      onChange={(e) => setFormGateway(e.target.value)}
                      placeholder="192.168.10.254"
                      fontFamily="mono"
                    />
                  </Field.Root>

                  <HStack gap={3}>
                    <Button type="submit" colorPalette="orange" loading={saving}>
                      Apply Configuration
                    </Button>
                    <Button variant="outline" onClick={handleCancel}>
                      Cancel
                    </Button>
                  </HStack>
                </Stack>
              </form>
            </Box>
          )}
        </Stack>
      </Container>
    </Box>
  )
}
