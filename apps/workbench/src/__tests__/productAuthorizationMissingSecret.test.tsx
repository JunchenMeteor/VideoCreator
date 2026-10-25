import { expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { authorizationSessionSecretAvailable } from '../productAuthorization';
import { expectNoSecretStored, mockApi, renderGate } from './fixtures';

// No initializeProductAuthorization() here: this file checks the page without a
// launcher-injected secret, which is the honest "read-only, cannot decide" path.
it('without a launcher secret the page disables both actions and says why', async () => {
  expect(authorizationSessionSecretAvailable()).toBe(false);
  mockApi('pending');
  renderGate();
  expect(await screen.findByRole('heading', { name: '需要你的授权' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '同意并继续' })).toBeDisabled();
  expect(screen.getByRole('button', { name: '拒绝' })).toBeDisabled();
  expect(screen.getByText(/没有拿到启动器注入的授权会话凭据/)).toBeInTheDocument();
  expectNoSecretStored();
});
