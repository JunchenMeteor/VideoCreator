import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// The workbench renders Radix Themes, which expects these browser APIs in jsdom.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const observerHost = globalThis as unknown as { ResizeObserver?: unknown };
if (typeof observerHost.ResizeObserver === 'undefined') observerHost.ResizeObserver = ResizeObserverMock;

const element = Element.prototype as unknown as Record<string, unknown>;
element.hasPointerCapture ??= () => false;
element.setPointerCapture ??= () => {};
element.releasePointerCapture ??= () => {};

afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
