import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Shim manual de Storage. vitest 1.6 + jsdom 24 + node 26 expone window.localStorage
// como `undefined` (regresión conocida). Inyectamos un Storage mínimo en window
// y globalThis para que los tests funcionen igual que en un navegador.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length() {
    return this.store.size;
  }
  clear() {
    this.store.clear();
  }
  getItem(key: string) {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }
  setItem(key: string, value: string) {
    this.store.set(key, String(value));
  }
  removeItem(key: string) {
    this.store.delete(key);
  }
  key(idx: number) {
    return Array.from(this.store.keys())[idx] ?? null;
  }
}

const memoryStorage = new MemoryStorage();

if (typeof window !== 'undefined') {
  if (!('localStorage' in window) || window.localStorage === undefined) {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: memoryStorage,
    });
  }
  if (!('sessionStorage' in window) || window.sessionStorage === undefined) {
    Object.defineProperty(window, 'sessionStorage', {
      configurable: true,
      value: memoryStorage,
    });
  }
}

if (typeof globalThis.localStorage === 'undefined') {
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: memoryStorage,
  });
}

afterEach(() => {
  cleanup();
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.clear();
  }
});

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver =
  (globalThis as unknown as { ResizeObserver?: typeof ResizeObserverMock }).ResizeObserver ??
  ResizeObserverMock;

if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}
