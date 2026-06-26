import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  test: {
    environment: 'happy-dom',
    include: ['tests/unit/**/*.test.js', 'tests/unit/**/*.spec.js'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      include: ['src/utils/**/*.js', 'src/composables/**/*.js', 'src/stores/**/*.js']
    }
  }
})