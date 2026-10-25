import { beforeAll, expect, it } from 'vitest';
import { fireEvent, screen } from '@testing-library/react';
import { authorizationSessionSecretAvailable, initializeProductAuthorization } from '../productAuthorization';
import { SECRET, expectNoSecretStored, mockApi, pendingView, renderGate } from './fixtures';

// Separate file so this module starts with a fresh, captured session secret.
beforeAll(() => {
  window.history.replaceState(null, '', '/#a=' + SECRET);
  initializeProductAuthorization();
  expect(authorizationSessionSecretAvailable()).toBe(true);
});

it('deny submits a decision but states honestly that nothing was written', async () => {
  const { fetchMock } = mockApi('pending');
  renderGate();
  expect(await screen.findByRole('heading', { name: '需要你的授权' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '拒绝' }));
  expect(await screen.findByRole('heading', { name: '没有写入任何授权' })).toBeInTheDocument();
  expect(screen.getByText(/你拒绝了这次授权/)).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: '授权已完成，请重启应用' })).not.toBeInTheDocument();
  const post = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/deny'));
  expect(post).toBeTruthy();
  const init = post![1] as RequestInit;
  expect(init.method).toBe('POST');
  expect((init.headers as Record<string, string>)['X-VideoCreator-Authorization']).toBe(SECRET);
  expect(JSON.parse(String(init.body))).toEqual({ scope_sha256: pendingView.scope_sha256, nonce: pendingView.nonce });
  expect(authorizationSessionSecretAvailable()).toBe(false);
  expectNoSecretStored();
});
