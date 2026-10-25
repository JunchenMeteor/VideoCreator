import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@radix-ui/themes/styles.css';
import { App } from './App';
import { initializeProductAuthorization } from './productAuthorization';
import { bootstrapWorkbenchFromRuntime } from './workbenchBootstrap';
import './styles.css';

// ADR0081: the launcher may hand this page the per-process authorization secret
// through a one-time URL fragment (`#a=...`) or the desktop preload global.
// Capture it before React mounts and strip the fragment immediately; the module
// keeps it in memory only (never storage, DOM, console or logs).
initializeProductAuthorization();

// Static production pages and the dev server both resolve the managed-proxy
// origin at runtime: a launcher-injected window.__VIDEO_CREATOR_BOOT__ must name
// this exact loopback origin, otherwise the page's own origin is used (relative
// `/api/...` through the same-origin proxy). No token is read or stored here.
bootstrapWorkbenchFromRuntime();

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

const root = document.getElementById('root');
if (!root) throw new Error('Workbench root element is missing.');

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
