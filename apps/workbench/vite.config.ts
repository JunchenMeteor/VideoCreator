import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

const engineUrl = process.env.VIDEO_CREATOR_ENGINE_URL;
const sessionToken = process.env.VIDEO_CREATOR_API_TOKEN;
// Trusted host-only environment; never VITE_ or frontend runtime credentials.
const workbenchPortText = process.env.VIDEO_CREATOR_WORKBENCH_PORT ?? '1420';
if (!/^[1-9][0-9]{0,4}$/.test(workbenchPortText) || String(Number(workbenchPortText)) !== workbenchPortText || Number(workbenchPortText) < 1024 || Number(workbenchPortText) > 65535) throw new Error('workbench_port_invalid');
const workbenchPort = Number(workbenchPortText);
const workbenchOrigin = 'http://127.0.0.1:' + workbenchPort;
if (engineUrl) {
  const target = new URL(engineUrl);
  if (target.protocol !== 'http:' || !['127.0.0.1', '[::1]'].includes(target.hostname) || target.username || target.password || target.pathname !== '/' || target.search || target.hash || !sessionToken || sessionToken.length < 32) {
    throw new Error('Development proxy requires a loopback HTTP origin and a private process session token');
  }
}

// These inputs come from the trusted host after its owned API ready handshake.
// They do not authorize a webpage; the private proxy session remains the boundary.
const bootstrapMode = process.env.VIDEO_CREATOR_WORKBENCH_BOOTSTRAP_MODE;
const bootstrapSource = process.env.VIDEO_CREATOR_WORKBENCH_BOOTSTRAP_SOURCE;
const bootstrapOrigin = process.env.VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN;
const bootstrapInstance = process.env.VIDEO_CREATOR_WORKBENCH_INSTANCE_ID;
const hasBootstrap = [bootstrapMode, bootstrapSource, bootstrapOrigin, bootstrapInstance].some(value => value !== undefined);
if (hasBootstrap && (bootstrapMode !== 'managed-proxy' || bootstrapSource !== 'dev-runtime-api-ready' ||
    bootstrapOrigin !== workbenchOrigin || !engineUrl || !sessionToken ||
    !bootstrapInstance || bootstrapInstance.length > 128 || /[\r\n]/.test(bootstrapInstance))) {
  throw new Error('trusted_workbench_bootstrap_invalid');
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

export default defineConfig(({ command, mode }) => ({
  plugins: [react(), localApiGuard],
  // Static/native/production bundles never acquire development owner bootstrap.
  define: {
    __VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN__: command === 'serve' && mode === 'development' && hasBootstrap
      ? JSON.stringify(bootstrapOrigin) : 'undefined',
  },
  server: {
    host: '127.0.0.1',
    allowedHosts: ['127.0.0.1'],
    port: workbenchPort,
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
}));
