import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const engineUrl = process.env.VIDEO_CREATOR_ENGINE_URL;
if (engineUrl) {
  const target = new URL(engineUrl);
  if (target.protocol !== 'http:' || !['127.0.0.1', '[::1]'].includes(target.hostname) || target.username || target.password || target.pathname !== '/' || target.search || target.hash) {
    throw new Error('VIDEO_CREATOR_ENGINE_URL must be a credential-free loopback HTTP origin');
  }
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 1420,
    strictPort: true,
    proxy: engineUrl ? { '/api': { target: engineUrl, changeOrigin: false } } : undefined,
  },
  build: { target: 'es2022', sourcemap: true },
});
