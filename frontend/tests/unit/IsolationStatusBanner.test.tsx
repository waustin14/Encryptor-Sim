import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { IsolationStatusBanner } from '../../src/components/IsolationStatusBanner'
import type { IsolationStatus } from '../../src/state/systemStatus'

describe('IsolationStatusBanner', () => {
  it('renders a failure banner when status is failed', () => {
    const status: IsolationStatus = {
      status: 'fail',
      timestamp: '2026-01-25T12:00:00Z',
      checks: [],
      failures: ['PT/CT isolation check failed'],
      duration: 1.2,
    }

    render(
      <ChakraProvider value={defaultSystem}>
        <IsolationStatusBanner status={status} isLoading={false} error={null} />
      </ChakraProvider>,
    )

    expect(screen.getByText('Isolation validation failed')).toBeTruthy()
    expect(screen.getByText(/PT\/CT isolation check failed/)).toBeTruthy()
  })
})
