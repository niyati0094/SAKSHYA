// Imported from vitest/config so the `test` block is typed; it re-exports
// vite's defineConfig, so the dev/build behaviour is unchanged.
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
  server: {
    port: 5173,
    // Proxying keeps the browser same-origin in development, so the app never
    // depends on CORS during the demo.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
