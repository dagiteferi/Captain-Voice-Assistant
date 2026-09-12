import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Disable caching for audio preview responses so the browser always
        // fetches fresh audio bytes from the backend instead of getting a 304.
        configure: (proxy) => {
          proxy.on('proxyRes', (_proxyRes, req, res) => {
            if (req.url?.includes('/audio/preview')) {
              res.setHeader('Cache-Control', 'no-store')
              res.removeHeader('ETag')
              res.removeHeader('Last-Modified')
            }
          })
        },
      },
    },
  },
})
