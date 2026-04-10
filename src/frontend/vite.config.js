import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get the API target from environment or default to localhost
// In Docker: use 'http://backend:8000'
// Local dev: use 'http://localhost:8000'
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      }
    }
  }
})
