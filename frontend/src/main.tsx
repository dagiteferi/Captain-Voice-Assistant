import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RoleProvider } from '@/shared/lib/roles'
import { SettingsProvider } from '@/shared/lib/useSettings'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <RoleProvider>
          <SettingsProvider>
            <App />
          </SettingsProvider>
        </RoleProvider>
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
