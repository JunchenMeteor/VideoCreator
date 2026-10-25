import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@radix-ui/themes/styles.css';
import { App } from './App';
import { bootstrapManagedWorkbench } from './engine';
import { initializeProductAuthorization } from './productAuthorization';
import './styles.css';

// ADR0081: the launcher may hand this page the per-process authorization secret
// through a one-time URL fragment (`#a=...`) or the desktop preload global.
// Capture it before React mounts and strip the fragment immediately; the module
// keeps it in memory only (never storage, DOM, console or logs).
initializeProductAuthorization();

// Integration may define this non-secret constant only from the actual trusted
// DevRuntime ready/configured origin. It is absent in static/native builds until
// their real host bootstrap exists; ordinary location/origin never supplies it.
declare const __VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN__: string | undefined;
if (typeof __VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN__ === 'string') {
  try { bootstrapManagedWorkbench(__VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN__); }
  catch { /* Keep the UI available with an honest disconnected state. */ }
}

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
