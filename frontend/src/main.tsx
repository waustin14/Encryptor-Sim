import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ChakraProvider, defaultSystem } from '@chakra-ui/react'
import './index.css'
import { App } from './App'
import { AppToaster } from './components/ui/toaster'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ChakraProvider value={defaultSystem}>
      <App />
      <AppToaster />
    </ChakraProvider>
  </StrictMode>,
)
