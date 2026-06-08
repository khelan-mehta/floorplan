/// <reference types="vitest/config" />
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const root = dirname(fileURLToPath(import.meta.url));
const pkg = (p: string) => resolve(root, '../../packages', p);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@fpg/ui': pkg('ui/src/index.ts'),
      '@fpg/schemas': pkg('schemas/src/index.ts'),
      '@fpg/geometry-core': pkg('geometry-core/src/index.ts'),
    },
    dedupe: ['react', 'react-dom', 'three'],
  },
  server: { port: 5173, host: true },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
