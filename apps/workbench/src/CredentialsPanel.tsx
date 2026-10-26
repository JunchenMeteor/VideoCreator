import { useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Callout, Select, TextField } from '@radix-ui/themes';
import { Info, KeyRound, Trash2 } from 'lucide-react';
import {
  CREDENTIAL_PROVIDERS, CREDENTIAL_TEST_NOTE, EMPTY_CREDENTIALS_TEXT,
  createCredential, credentialFailureText, createdAtText, deleteCredential, fingerprintPrefix,
  readCredentials, CredentialApiFailure,
  type CredentialProvider, type CredentialSummary,
} from './credentialApi';

type Notice = { tone: 'success' | 'error' | 'info'; text: string; references?: readonly string[] };
type Busy = null | 'save' | `delete:${string}`;

function NoticeView({ notice }: { notice: Notice }) {
  return <div className={`credential-notice is-${notice.tone}`} role={notice.tone === 'error' ? 'alert' : 'status'}>
    <p>{notice.text}</p>
    {notice.references?.length
      ? <ul className="credential-references" aria-label="仍引用该凭证的记录">
          {notice.references.map(reference => <li key={reference}><code>{reference}</code></li>)}
        </ul>
      : null}
  </div>;
}

export function CredentialsPanel({ connected, instanceId }: { connected: boolean; instanceId?: string }) {
  const queryClient = useQueryClient();
  const queryKey = ['credentials', instanceId] as const;
  const list = useQuery({
    queryKey,
    enabled: connected,
    queryFn: () => readCredentials(),
    retry: false,
  });
  const [provider, setProvider] = useState<CredentialProvider>('deepseek');
  const [label, setLabel] = useState('');
  const [secret, setSecret] = useState('');
  const [busy, setBusy] = useState<Busy>(null);
  const [formNotice, setFormNotice] = useState<Notice | null>(null);
  const [deleteNotice, setDeleteNotice] = useState<Notice | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy !== null || !connected || !label.trim() || !secret) return;
    setBusy('save');
    setFormNotice(null);
    setDeleteNotice(null);
    try {
      const saved = await createCredential({ provider, label, secret });
      // The secret is dropped from page state the moment the request settles.
      // The success text carries only the fingerprint, never a masked echo.
      setSecret('');
      setFormNotice({ tone: 'success', text: `已保存，指纹 ${fingerprintPrefix(saved.fingerprint)}` });
      queryClient.setQueryData<CredentialSummary[]>(queryKey, current => [...(current ?? []), saved]);
      void queryClient.invalidateQueries({ queryKey });
    } catch (failure) {
      // A failed attempt must not leave the typed secret in the page either.
      setSecret('');
      setFormNotice({ tone: 'error', text: credentialFailureText(failure) });
    } finally {
      setBusy(null);
    }
  };

  const saveAndTest = () => {
    // No connection-test endpoint exists yet. Say exactly that: nothing is
    // saved and nothing is tested, so no success state can be mistaken for a pass.
    setFormNotice({ tone: 'info', text: `${CREDENTIAL_TEST_NOTE}；本次没有保存，也没有执行连接测试。需要单独保存时，请使用“保存”。` });
  };

  const remove = async (item: CredentialSummary) => {
    if (busy !== null) return;
    setDeleteNotice(null);
    setFormNotice(null);
    setBusy(`delete:${item.credential_ref}`);
    try {
      await deleteCredential(item.credential_ref);
      queryClient.setQueryData<CredentialSummary[]>(queryKey, current => (current ?? []).filter(entry => entry.credential_ref !== item.credential_ref));
      void queryClient.invalidateQueries({ queryKey });
    } catch (failure) {
      setDeleteNotice({
        tone: 'error',
        text: credentialFailureText(failure),
        references: failure instanceof CredentialApiFailure && failure.code === 'credential_in_use'
          ? failure.references
          : undefined,
      });
    } finally {
      setBusy(null);
    }
  };

  return <section className="product-section credentials-panel" aria-labelledby="credentials-title">
    <div className="r2-heading">
      <KeyRound size={21} strokeWidth={1.7} aria-hidden="true" />
      <div className="stage-heading">
        <span className="section-kicker">设置</span>
        <h2 id="credentials-title">模型凭证</h2>
        <p>密钥只写入本机操作系统保险库；列表只显示指纹，工作台不保存、不缓存、不回显密钥。</p>
      </div>
    </div>

    {!connected ? <p className="small-note" role="status">未连接本机实例，无法读取模型凭证。</p> : null}
    {connected && list.isPending ? <p className="small-note" role="status">正在读取模型凭证…</p> : null}
    {list.error ? <Callout.Root color="red" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{credentialFailureText(list.error)}</Callout.Text></Callout.Root> : null}
    {connected && list.data?.length === 0 ? <p className="credential-empty">{EMPTY_CREDENTIALS_TEXT}</p> : null}
    {list.data?.length ? <ul className="credential-list" aria-label="已配置的模型凭证">
      {list.data.map(item => <li className="credential-row" key={item.credential_ref}>
        <div className="credential-identity"><strong>{item.provider}</strong><span>{item.label}</span></div>
        <span className="credential-fingerprint">指纹 <code>{fingerprintPrefix(item.fingerprint)}</code></span>
        <time className="credential-created">{createdAtText(item.created_at_us)}</time>
        <Button size="1" variant="ghost" color="red" disabled={busy !== null || !connected}
          aria-label={`删除凭证：${item.label}`} onClick={() => void remove(item)}>
          <Trash2 size={14} />删除
        </Button>
      </li>)}
    </ul> : null}
    {deleteNotice ? <NoticeView notice={deleteNotice} /> : null}

    <form className="credential-form" onSubmit={submit} noValidate>
      <h3>添加模型凭证</h3>
      <div className="credential-form-grid">
        <div>
          <label className="field-label" htmlFor="credential-provider">模型服务</label>
          <Select.Root value={provider} disabled={busy !== null} onValueChange={value => setProvider(value as CredentialProvider)}>
            <Select.Trigger id="credential-provider" aria-label="模型服务" />
            <Select.Content>{CREDENTIAL_PROVIDERS.map(item => <Select.Item key={item} value={item}>{item}</Select.Item>)}</Select.Content>
          </Select.Root>
        </div>
        <div>
          <label className="field-label" htmlFor="credential-label">名称</label>
          <TextField.Root id="credential-label" value={label} maxLength={200} required disabled={busy !== null}
            placeholder="例如：主账号" onChange={event => setLabel(event.target.value)} />
        </div>
        <div className="credential-secret-field">
          <label className="field-label" htmlFor="credential-secret">密钥</label>
          <TextField.Root id="credential-secret" type="password" value={secret} maxLength={4096}
            autoComplete="off" spellCheck={false} required disabled={busy !== null}
            placeholder="粘贴模型服务密钥" aria-describedby="credential-secret-note"
            onChange={event => setSecret(event.target.value)} />
          <p className="small-note" id="credential-secret-note">提交后立即清空，不进入浏览器存储、页面地址或日志。</p>
        </div>
      </div>
      <div className="credential-actions">
        <Button type="submit" disabled={!connected || busy !== null || !label.trim() || !secret}>
          {busy === 'save' ? '正在保存' : '保存'}
        </Button>
        <Button type="button" variant="soft" disabled={busy !== null} aria-describedby="credential-test-note" onClick={saveAndTest}>
          保存并测试
        </Button>
        <span className="credential-test-note" id="credential-test-note">{CREDENTIAL_TEST_NOTE}</span>
      </div>
      {formNotice ? <NoticeView notice={formNotice} /> : null}
    </form>
  </section>;
}
