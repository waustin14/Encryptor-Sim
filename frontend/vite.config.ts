import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Output to backend/static for FastAPI to serve
    outDir: '../backend/static',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
  },
})
