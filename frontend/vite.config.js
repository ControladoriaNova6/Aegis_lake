import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Redireciona /api/* pro backend Flask — assim o navegador nunca
      // enxerga uma origem diferente (evita CORS por completo, e o
      // cookie de sessão funciona normalmente, igual a same-origin).
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
