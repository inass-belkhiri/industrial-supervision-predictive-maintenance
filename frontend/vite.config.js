import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,  // ← forcer le port 5173, ne pas changer automatiquement
    proxy: {
      '/ws': {
        target: 'http://localhost:8001',
        ws: true,
        changeOrigin: true,
      }
    }
  }
})
