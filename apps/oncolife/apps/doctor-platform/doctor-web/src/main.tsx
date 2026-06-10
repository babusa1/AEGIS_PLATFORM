/**
 * OncoLife Physician Application
 * Clinical Dashboard for Care Teams
 * 
 * Entry point with:
 * - OncoLife Theme Provider (with dark mode support)
 * - Global Styles with animations
 * - React Query for server state
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { 
  OncolifeThemeProvider, 
  GlobalStyles,
  ErrorBoundary,
} from '@oncolife/ui-components'
import App from './App.tsx'

// Configure React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <OncolifeThemeProvider 
      appType="doctor" 
      storageKey="oncolife-doctor-theme"
    >
      <GlobalStyles />
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ErrorBoundary>
    </OncolifeThemeProvider>
  </StrictMode>,
)
