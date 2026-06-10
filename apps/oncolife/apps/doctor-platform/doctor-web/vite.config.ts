import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()] as any,
  server: {
    host: true,
    port: 5174, // Different port from patient-web (5173)
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8001', // Assuming doctor-api runs on different port
        changeOrigin: true,
        secure: false
      }
    }
  },
  define: {
    global: 'globalThis',
  }
})
