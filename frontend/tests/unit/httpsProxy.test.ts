/**
 * Tests for HTTPS proxy configuration in vite.config.ts (Task 4, AC: #1).
 *
 * Validates that the Vite dev server proxies API calls to HTTPS backend
 * with self-signed certificate acceptance.
 */
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { describe, expect, it } from 'vitest'

const viteConfigPath = resolve(__dirname, '../../vite.config.ts')
const viteConfigContent = readFileSync(viteConfigPath, 'utf-8')

describe('Vite HTTPS Proxy Configuration', () => {
  it('configures proxy for /api path', () => {
    expect(viteConfigContent).toContain("'/api'")
  })

  it('uses HTTPS target for proxy', () => {
    expect(viteConfigContent).toContain('https://')
  })

  it('sets secure: false to accept self-signed certificate', () => {
    expect(viteConfigContent).toContain('secure: false')
  })

  it('sets changeOrigin: true for proxy', () => {
    expect(viteConfigContent).toContain('changeOrigin: true')
  })

  it('targets port 443', () => {
    expect(viteConfigContent).toContain(':443')
  })
})

describe('Frontend .env.example', () => {
  it('exists and includes HTTPS API base URL', () => {
    const envExamplePath = resolve(__dirname, '../../.env.example')
    const envContent = readFileSync(envExamplePath, 'utf-8')
    expect(envContent).toContain('https://')
  })

  it('references VITE_API_BASE_URL', () => {
    const envExamplePath = resolve(__dirname, '../../.env.example')
    const envContent = readFileSync(envExamplePath, 'utf-8')
    expect(envContent).toContain('VITE_API_BASE_URL')
  })
})
