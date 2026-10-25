import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// ADR0081 workbench tests run in jsdom at the trusted loopback origin so the
// managed-proxy client can be exercised exactly as the product bootstraps it.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://127.0.0.1:1420/' } },
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/__tests__/**/*.test.tsx'],
    restoreMocks: true,
    testTimeout: 15_000,
  },
});
