import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    environmentOptions: {
      jsdom: {
        // about:blank tiene origen "null", lo que hace que jsdom rechace
        // localStorage por SecurityError. Forzamos un origen válido.
        url: 'http://localhost',
      },
    },
    setupFiles: ['./tests/setup.ts'],
    css: false,
  },
});
