import { describe, expect, it } from 'vitest'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { render, screen } from '@testing-library/react'
import { App } from '../../src/App'

describe('App', () => {
  it('renders the system dashboard heading', () => {
    render(
      <ChakraProvider value={defaultSystem}>
        <App />
      </ChakraProvider>,
    )
    expect(screen.getByText('System Dashboard')).toBeTruthy()
  })
})
