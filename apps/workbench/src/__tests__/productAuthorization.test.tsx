import { beforeAll, describe, expect, it } from 'vitest';
import { fireEvent, screen } from '@testing-library/react';
import { authorizationSessionSecretAvailable, initializeProductAuthorization } from '../productAuthorization';
import { bootstrapManagedWorkbench } from '../engine';
import { SECRET, expectNoSecretStored, mockApi, pendingView, renderGate, renderWorkbench } from './fixtures';

beforeAll(() => {
  window.history.replaceState(null, '', '/#a=' + SECRET);
  initializeProductAuthorization();
  expect(window.location.hash).toBe('');
  expect(authorizationSessionSecretAvailable()).toBe(true);
});

describe('ADR0081 startup health states', () => {
  it('pending -> the authorization page replaces the old dead state', async () => {
    mockApi('pending');
    const dispose = bootstrapManagedWorkbench('http://127.0.0.1:1420');
    try {
      renderWorkbench();
      expect(await screen.findByRole('heading', { name: '需要你的授权' })).toBeInTheDocument();
      expect(screen.queryByText('建项目')).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: '同意并继续' })).toBeEnabled();
      expect(screen.getByText('不接受就不会写入')).toBeInTheDocument();
      expect(screen.getByText('初始化本机 Owner（首次授权）')).toBeInTheDocument();
      expect(screen.getByText(/本机 Owner（本机用户）/)).toBeInTheDocument();
      expectNoSecretStored();
    } finally { dispose(); }
  });

  it('complete -> restart guidance with a clear next step', async () => {
    mockApi('complete');
    const dispose = bootstrapManagedWorkbench('http://127.0.0.1:1420');
    try {
      renderWorkbench();
      expect(await screen.findByRole('heading', { name: '授权已完成，请重启应用' })).toBeInTheDocument();
      expect(screen.getByText(/重新运行启动器/)).toBeInTheDocument();
      expect(screen.getByText('关闭当前工作台窗口。')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '重新检查状态' })).toBeInTheDocument();
      expect(screen.queryByText('建项目')).not.toBeInTheDocument();
    } finally { dispose(); }
  });

  it('none -> the ordinary five-step workbench', async () => {
    mockApi('none');
    const dispose = bootstrapManagedWorkbench('http://127.0.0.1:1420');
    try {
      renderWorkbench();
      expect(await screen.findByText('建项目')).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: '需要你的授权' })).not.toBeInTheDocument();
      expect(screen.queryByText('授权已完成，请重启应用')).not.toBeInTheDocument();
    } finally { dispose(); }
  });

  it('error -> honest unavailable state, not a fake authorization page', async () => {
    mockApi('error');
    const dispose = bootstrapManagedWorkbench('http://127.0.0.1:1420');
    try {
      renderWorkbench();
      expect(await screen.findByText(/实例连接暂不可用/)).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: '需要你的授权' })).not.toBeInTheDocument();
    } finally { dispose(); }
  });
});

describe('ADR0081 authorization page', () => {
  it('shows scope, validity, one-time nature, and GET pending carries the secret header', async () => {
    const { fetchMock } = mockApi('pending');
    renderGate();
    expect(await screen.findByRole('heading', { name: '需要你的授权' })).toBeInTheDocument();
    const pendingCall = fetchMock.mock.calls.find(call => String(call[0]).includes('/authorization/pending'));
    expect(pendingCall).toBeTruthy();
    expect(((pendingCall![1] as RequestInit).headers as Record<string, string>)['X-VideoCreator-Authorization']).toBe(SECRET);
    expect(screen.getByText('授权有效期')).toBeInTheDocument();
    expect(screen.getByText('本次确认')).toBeInTheDocument();
    expect(screen.getByText(/剩余 (9:5|10:0)/)).toBeInTheDocument();
    expect(screen.getByText('一次性')).toBeInTheDocument();
    expect(screen.getByText(/确认后用过的凭据立即失效/)).toBeInTheDocument();
    expect(screen.getByText('首次初始化本机 Owner')).toBeInTheDocument();
    expect(screen.getByText('本机 Owner 绑定')).toBeInTheDocument();
    expect(screen.getByText(/本机实例/)).toBeInTheDocument();
    expectNoSecretStored();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it('can_decide=false disables both actions and explains why', async () => {
    mockApi('pending', { ...pendingView, can_decide: false });
    renderGate();
    await screen.findByRole('heading', { name: '需要你的授权' });
    expect(screen.getByRole('button', { name: '同意并继续' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '拒绝' })).toBeDisabled();
    expect(screen.getByText(/不能由此窗口确认/)).toBeInTheDocument();
  });

  it('a missing one-time nonce is surfaced instead of invented', async () => {
    mockApi('pending', { ...pendingView, nonce: null });
    renderGate();
    await screen.findByRole('heading', { name: '需要你的授权' });
    expect(screen.getByRole('button', { name: '同意并继续' })).toBeDisabled();
    expect(screen.getByText(/没有随视图提供一次性确认凭据/)).toBeInTheDocument();
  });

  it('approve submits the frozen body + header, then shows restart guidance', async () => {
    const { fetchMock } = mockApi('pending');
    renderGate();
    await screen.findByRole('heading', { name: '需要你的授权' });
    fireEvent.click(screen.getByRole('button', { name: '同意并继续' }));
    expect(await screen.findByRole('heading', { name: '授权已完成，请重启应用' })).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(call => String(call[0]).endsWith('/approve'));
    expect(post).toBeTruthy();
    const init = post![1] as RequestInit;
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>)['X-VideoCreator-Authorization']).toBe(SECRET);
    expect(JSON.parse(String(init.body))).toEqual({ scope_sha256: pendingView.scope_sha256, nonce: pendingView.nonce });
    expect(authorizationSessionSecretAvailable()).toBe(false);
    expectNoSecretStored();
    expect(screen.getByText(/重新运行启动器/)).toBeInTheDocument();
  });

  // Real-chain verification is deliberately out of the unit suite: it needs a
  // restricted engine started with VIDEO_CREATOR_AUTHORIZATION_SESSION_SECRET,
  // a launcher that opens the page with #a=<secret>, a real Owner binding write,
  // audit SHA equality, and an engine restart back to health=none.
  it.skip('real restricted engine round trip (live engine + launcher secret)', () => {
    // Intentionally no assertions here: this unit file only mocks the API.
  });
});
