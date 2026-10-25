import { afterEach, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { bootstrapWorkbenchFromRuntime, resolveWorkbenchOrigin } from '../workbenchBootstrap';
import { mockApi, renderWorkbench } from './fixtures';

afterEach(() => {
  // Bootstrap consumes the descriptor; this only cleans up failed/early tests.
  delete window.__VIDEO_CREATOR_BOOT__;
});

it('boots a static production page from its same-origin proxy without the dev define', async () => {
  // Simulate the built artifact: no build-time trusted-origin define exists.
  expect('__VIDEO_CREATOR_TRUSTED_WORKBENCH_ORIGIN__' in globalThis).toBe(false);
  delete window.__VIDEO_CREATOR_BOOT__;
  const { calls } = mockApi('none');
  const dispose = bootstrapWorkbenchFromRuntime();
  expect(typeof dispose).toBe('function');
  try {
    renderWorkbench();
    expect(await screen.findByText('建项目')).toBeInTheDocument();
    // The old failure mode was `trusted_connection_missing` and an unavailable banner.
    expect(screen.queryByText(/trusted_connection_missing|实例连接暂不可用/)).not.toBeInTheDocument();
    expect(calls.some(call => call.url.startsWith(window.location.origin + '/api/'))).toBe(true);
  } finally { dispose?.(); }
});

it('accepts an injected boot descriptor but never exposes its token', async () => {
  const token = 'boot-token-must-not-be-exposed';
  window.__VIDEO_CREATOR_BOOT__ = { mode: 'managed-proxy', origin: window.location.origin, token };
  const spies = [vi.spyOn(console, 'log'), vi.spyOn(console, 'info'), vi.spyOn(console, 'warn'), vi.spyOn(console, 'error')];
  spies.forEach(spy => spy.mockImplementation(() => {}));
  mockApi('none');
  const dispose = bootstrapWorkbenchFromRuntime();
  expect(typeof dispose).toBe('function');
  // The descriptor (which may carry a host token) is consumed and removed.
  expect(window.__VIDEO_CREATOR_BOOT__).toBeUndefined();
  try {
    renderWorkbench();
    expect(await screen.findByText('建项目')).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain(token);
    expect(JSON.stringify(localStorage)).not.toContain(token);
    expect(JSON.stringify(sessionStorage)).not.toContain(token);
    expect(spies.some(spy => spy.mock.calls.some(args => args.some(arg => String(arg).includes(token))))).toBe(false);
  } finally {
    dispose?.();
    delete window.__VIDEO_CREATOR_BOOT__;
  }
});

it('does not trust a non-loopback boot origin', () => {
  expect(resolveWorkbenchOrigin(
    { origin: 'http://example.com', protocol: 'http:', hostname: 'example.com' },
    { mode: 'managed-proxy', origin: 'http://example.com' },
  )).toBeUndefined();
});
