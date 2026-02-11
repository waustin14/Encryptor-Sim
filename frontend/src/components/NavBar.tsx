import { Button, HStack } from '@chakra-ui/react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../state/authStore'

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Interfaces', path: '/interfaces' },
  { label: 'Peers', path: '/peers' },
  { label: 'Routes', path: '/routes' },
]

export function NavBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, user } = useAuthStore()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <HStack gap={2}>
      {NAV_ITEMS.map((item) => {
        const isActive = location.pathname === item.path
        return (
          <Button
            key={item.path}
            onClick={() => navigate(item.path)}
            variant={isActive ? 'solid' : 'outline'}
            colorPalette={isActive ? 'orange' : undefined}
            size="sm"
          >
            {item.label}
          </Button>
        )
      })}
      <Button onClick={handleLogout} variant="outline" size="sm">
        Logout{user ? ` (${user.username})` : ''}
      </Button>
    </HStack>
  )
}
