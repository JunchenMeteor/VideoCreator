import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

const engineUrl = process.env.VIDEO_CREATOR_ENGINE_URL;
const sessionToken = process.env.VIDEO_CREATOR_API_TOKEN;
const workbenchOrigin = 'http://127.0.0.1:1420';
if (engineUrl) {
  const target = new URL(engineUrl);
  if (target.protocol !== 'http:' || !['127.0.0.1', '[::1]'].includes(target.hostname) || target.username || target.password || target.pathname !== '/' || target.search || target.hash || !sessionToken || sessionToken.length < 32) {
    throw new Error('Development proxy requires a loopback HTTP origin and a private process session token');
  }
}

const localApiGuard: Plugin = {
  name: 'video-creator-local-api-guard',
  configureServer(server) {
    server.middlewares.use((request, response, next) => {
      if (!request.url?.startsWith('/api/')) return next();
      const origin = request.headers.origin;
      const fetchSite = request.headers['sec-fetch-site'];
      const originAllowed = origin === workbenchOrigin || (origin === undefined && fetchSite === 'same-origin');
      if (!engineUrl || !originAllowed || (fetchSite !== undefined && fetchSite !== 'same-origin') || request.headers['x-video-creator-client'] !== 'workbench') {
        response.statusCode = 403;
        response.setHeader('Content-Type', 'application/json');
        response.setHeader('Cache-Control', 'no-store');
        response.end(JSON.stringify({ code: 'local_proxy_denied', message: 'A configured same-origin workbench session is required' }));
        return;
      }
      next();
    });
  },
};

export default defineConfig({
  plugins: [react(), localApiGuard],
  server: {
    host: '127.0.0.1',
    allowedHosts: ['127.0.0.1'],
    port: 1420,
    strictPort: true,
    proxy: engineUrl ? { '/api/': {
      target: engineUrl,
      changeOrigin: true,
      configure(proxy) {
        proxy.on('proxyReq', (request) => { request.setHeader('Authorization', 'Bearer ' + sessionToken); request.removeHeader('X-Video-Creator-Client'); });
        proxy.on('proxyRes', (response) => { response.headers['cache-control'] = 'no-store'; });
      },
    } } : undefined,
  },
  build: { target: 'es2022', sourcemap: true },
});
