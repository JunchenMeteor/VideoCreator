import { useEffect, useRef, useState } from 'react';
import {
  Badge, Button, Callout, Dialog, Flex, IconButton, Select, Tabs,
  TextArea, TextField, Theme,
} from '@radix-ui/themes';
import {
  ArrowRight, Check, ChevronDown, ChevronLeft, ChevronRight,
  Clapperboard, FileText, Film, FolderOpen, Headphones, Image,
  Info, Layers, PanelRightClose, PanelRightOpen,
  Settings2, ShieldCheck, Sparkles, Sun, Moon, Upload, X,
} from 'lucide-react';

// This draft is a browser form, not an API Project or a production revision.
// Backend entities will be consumed from the generated API client in F1.
type BrowserDraft = {
  title: string;
  goal: string;
  sourceText: string;
  mode: 'interactive' | 'unattended';
  aspectRatio: '9:16' | '16:9';
  durationSeconds: string;
};

type SessionPreview = { name: string; url: string; kind: 'video' | 'audio' };
type SaveState = 'idle' | 'saving' | 'saved' | 'failed';

const DRAFT_KEY = 'video-creator:browser-draft:1';
const EMPTY_DRAFT: BrowserDraft = {
  title: '未命名作品', goal: '', sourceText: '', mode: 'interactive',
  aspectRatio: '9:16', durationSeconds: '60',
};
const STEPS = ['建项目', '定方向', '看方案', '制作', '成片'] as const;

function readBrowserDraft(): { draft: BrowserDraft; error: string | null; stored: boolean } {
  try {
    const stored = localStorage.getItem(DRAFT_KEY);
    if (!stored) return { draft: { ...EMPTY_DRAFT }, error: null, stored: false };
    const value: unknown = JSON.parse(stored);
    if (!value || typeof value !== 'object') throw new Error('invalid browser draft');
    const fields = value as Record<string, unknown>;
    if (
      typeof fields.title !== 'string' || typeof fields.goal !== 'string' ||
      typeof fields.sourceText !== 'string' || typeof fields.durationSeconds !== 'string' ||
      !['interactive', 'unattended'].includes(String(fields.mode)) ||
      !['9:16', '16:9'].includes(String(fields.aspectRatio))
    ) throw new Error('unsupported browser draft');
    return { draft: fields as BrowserDraft, error: null, stored: true };
  } catch {
    return { draft: { ...EMPTY_DRAFT }, error: '本机草稿暂时无法读取。原记录未覆盖，请检查浏览器存储后重试。', stored: false };
  }
}

function EmptyResult({ icon, title, children }: {
  icon: 'direction' | 'plan' | 'production' | 'delivery';
  title: string;
  children: React.ReactNode;
}) {
  const Icon = { direction: Sparkles, plan: Layers, production: Clapperboard, delivery: Film }[icon];
  return (
    <div className="empty-result">
      <div className="empty-symbol"><Icon size={25} strokeWidth={1.6} aria-hidden="true" /></div>
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  );
}

export function App() {
  const [initial] = useState(readBrowserDraft);
  const [draft, setDraft] = useState(initial.draft);
  const [saveState, setSaveState] = useState<SaveState>(initial.error ? 'failed' : initial.stored ? 'saved' : 'idle');
  const [saveError, setSaveError] = useState(initial.error);
  const [activeStep, setActiveStep] = useState(0);
  const [activePage, setActivePage] = useState('projects');
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [appearance, setAppearance] = useState<'light' | 'dark'>('light');
  const [preview, setPreview] = useState<SessionPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [deliveryTab, setDeliveryTab] = useState('video');
  const [sourceExpanded, setSourceExpanded] = useState(Boolean(draft.sourceText));
  const [feedback, setFeedback] = useState('');
  const [offline, setOffline] = useState(!navigator.onLine);
  const [retrySave, setRetrySave] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [draftChanged, setDraftChanged] = useState(false);

  useEffect(() => {
    const online = () => setOffline(false);
    const offlineNow = () => setOffline(true);
    window.addEventListener('online', online);
    window.addEventListener('offline', offlineNow);
    return () => {
      window.removeEventListener('online', online);
      window.removeEventListener('offline', offlineNow);
    };
  }, []);

  useEffect(() => {
    if (!draftChanged && retrySave === 0) return;
    setSaveState('saving');
    const timer = window.setTimeout(() => {
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
        setSaveState('saved');
        setSaveError(null);
      } catch {
        setSaveState('failed');
        setSaveError('本机草稿保存失败，当前输入仍保留在页面。请检查存储空间并重试。');
      }
    }, 500);
    return () => window.clearTimeout(timer);
  }, [draft, draftChanged, retrySave]);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview.url);
  }, [preview]);

  const updateDraft = <K extends keyof BrowserDraft>(field: K, value: BrowserDraft[K]) => {
    setDraftChanged(true);
    setDraft(current => ({ ...current, [field]: value }));
  };

  const saveNow = () => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
      setSaveState('saved');
      setSaveError(null);
    } catch {
      setSaveState('failed');
      setSaveError('本机草稿保存失败，当前输入仍保留在页面。请检查存储空间并重试。');
    }
  };

  useEffect(() => {
    const handleSave = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveNow();
      }
      if (event.key === 'Escape') setAssistantOpen(false);
    };
    window.addEventListener('keydown', handleSave);
    return () => window.removeEventListener('keydown', handleSave);
  }, [draft]);

  const choosePreview = (file: File | undefined) => {
    if (!file) return;
    const kind = file.type.startsWith('video/') ? 'video' : file.type.startsWith('audio/') ? 'audio' : null;
    if (!kind) {
      setPreviewError('请选择浏览器可播放的视频或音频文件。');
      return;
    }
    setPreviewError(null);
    setPreview({ name: file.name, url: URL.createObjectURL(file), kind });
    setDeliveryTab(kind);
    setActivePage('projects');
    setActiveStep(4);
  };

  return (
    <Theme appearance={appearance} accentColor="teal" grayColor="slate" radius="medium" scaling="100%">
      <div className="workbench" data-appearance={appearance}>
        <a className="skip-link" href="#workspace-main">跳到创作区</a>
        <aside className="app-nav" aria-label="工作台导航">
          <a className="brand" href="#workspace-main" aria-label="VideoCreator创作工作台">
            <span className="brand-mark"><Clapperboard size={21} strokeWidth={1.7} aria-hidden="true" /></span>
            <span>VideoCreator</span>
          </a>
          <nav>
            {[
              { id: 'projects', label: '项目', icon: FolderOpen },
              { id: 'assets', label: '素材', icon: Image },
              { id: 'tasks', label: '任务', icon: Layers },
              { id: 'settings', label: '设置', icon: Settings2 },
            ].map(item => (
              <button key={item.id} type="button" className={`nav-button ${activePage === item.id ? 'is-active' : ''}`}
                aria-current={activePage === item.id ? 'page' : undefined} onClick={() => setActivePage(item.id)}>
                <item.icon size={18} strokeWidth={1.7} aria-hidden="true" /><span>{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="nav-bottom"><ShieldCheck size={16} aria-hidden="true" /><span>本地工具</span></div>
        </aside>

        <div className="app-body">
          <header className="project-header">
            <div className="project-heading">
              <span className="workspace-name">我的工作空间</span>
              <div className="project-title-row"><h1>{activePage === 'projects' ? draft.title : { assets: '素材库', tasks: '任务中心', settings: '设置' }[activePage]}</h1>
                <span className={`save-status ${saveState === 'failed' ? 'is-error' : ''}`} aria-live="polite">
                  {saveState === 'saved' ? <Check size={13} aria-hidden="true" /> : null}
                  {saveState === 'saving' ? '保存中' : saveState === 'saved' ? '本机草稿已保存' : saveState === 'failed' ? '保存失败' : '本机草稿'}
                </span>
              </div>
            </div>
            <div className="header-actions">
              <Badge color={offline ? 'amber' : 'gray'} variant="soft">{offline ? '离线' : '引擎待连接'}</Badge>
              <IconButton size="2" variant="ghost" color="gray" aria-label={appearance === 'light' ? '切换深色主题' : '切换浅色主题'}
                onClick={() => setAppearance(appearance === 'light' ? 'dark' : 'light')}>
                {appearance === 'light' ? <Moon size={17} /> : <Sun size={17} />}
              </IconButton>
              <IconButton size="2" variant="soft" color="gray" aria-label={assistantOpen ? '收起创作助手' : '展开创作助手'}
                aria-expanded={assistantOpen} aria-controls="creative-assistant" onClick={() => setAssistantOpen(!assistantOpen)}>
                {assistantOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}
              </IconButton>
            </div>
          </header>

          {activePage === 'projects' ? <nav className="step-nav" aria-label="创作步骤">
            {STEPS.map((step, index) => <button key={step} className={`step-button ${index === activeStep ? 'is-active' : ''}`} type="button"
              aria-current={index === activeStep ? 'step' : undefined} onClick={() => setActiveStep(index)}>
              <span className="step-number">{index + 1}</span><span>{step}</span>
              {index < STEPS.length - 1 ? <ChevronRight className="step-divider" size={14} aria-hidden="true" /> : null}
            </button>)}
          </nav> : null}

          <div className={`workspace-layout ${assistantOpen ? 'has-assistant' : ''}`}>
            <main id="workspace-main" className="workspace-main" tabIndex={-1}>
              {saveError ? <Callout.Root color="red" className="storage-error" role="alert">
                <Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{saveError}</Callout.Text>
                <Button variant="soft" color="red" size="1" onClick={() => setRetrySave(current => current + 1)}>重试保存</Button>
              </Callout.Root> : null}
              {activePage === 'projects' ? <>
                {activeStep === 0 ? <section className="creation-panel" aria-labelledby="create-title">
                  <div className="section-intro"><span className="section-kicker">从一个想法开始</span><h2 id="create-title">你想做什么视频？</h2>
                    <p>给出目标和资料，Agent负责洞察、剧本、分镜与制作。你来审核和指导。</p>
                  </div>
                  <label className="field-label" htmlFor="creative-goal">视频目标</label>
                  <TextArea id="creative-goal" className="goal-input" size="3" value={draft.goal}
                    placeholder="例如：用轻松的游戏解说，介绍这次更新里最值得体验的内容。"
                    onChange={event => updateDraft('goal', event.target.value)} />
                  <div className="input-bottom"><Button size="2" variant="ghost" color="gray" onClick={() => setSourceExpanded(!sourceExpanded)}
                    aria-expanded={sourceExpanded} aria-controls="source-input">
                    <FileText size={16} aria-hidden="true" />{sourceExpanded ? '收起文字资料' : '添加文字资料'}
                  </Button><span>不需要先写剧本和分镜</span></div>
                  {sourceExpanded ? <div className="source-input" id="source-input">
                    <label className="field-label" htmlFor="creative-source">可用资料</label>
                    <TextArea id="creative-source" size="2" value={draft.sourceText} placeholder="粘贴文章、产品介绍、故事设定或已有资料。"
                      onChange={event => updateDraft('sourceText', event.target.value)} />
                  </div> : null}
                  <div className="creation-options">
                    <div><label className="field-label" htmlFor="creation-mode">创作方式</label>
                      <Select.Root value={draft.mode} onValueChange={value => updateDraft('mode', value as BrowserDraft['mode'])}>
                        <Select.Trigger id="creation-mode" /><Select.Content><Select.Item value="interactive">审核与指导</Select.Item><Select.Item value="unattended">预授权自动制作</Select.Item></Select.Content>
                      </Select.Root>
                    </div>
                    <div><label className="field-label" htmlFor="aspect-ratio">画幅</label>
                      <Select.Root value={draft.aspectRatio} onValueChange={value => updateDraft('aspectRatio', value as BrowserDraft['aspectRatio'])}>
                        <Select.Trigger id="aspect-ratio" /><Select.Content><Select.Item value="9:16">竖屏 9:16</Select.Item><Select.Item value="16:9">横屏 16:9</Select.Item></Select.Content>
                      </Select.Root>
                    </div>
                    <div><label className="field-label" htmlFor="duration">参考时长</label>
                      <Select.Root value={draft.durationSeconds} onValueChange={value => updateDraft('durationSeconds', value)}>
                        <Select.Trigger id="duration" /><Select.Content><Select.Item value="30">约30秒</Select.Item><Select.Item value="60">约1分钟</Select.Item><Select.Item value="120">约2分钟</Select.Item></Select.Content>
                      </Select.Root>
                    </div>
                  </div>
                  <div className="start-row"><Button size="3" disabled title="制作引擎正在接入，此探针不会提交生成请求。"><Sparkles size={17} aria-hidden="true" />让Agent开始创作<ArrowRight size={17} aria-hidden="true" /></Button>
                    <p>制作引擎接入后，在已授权的能力和预算内开始。</p></div>
                  <div className="local-alternative"><span>手里已有素材？</span><Button size="2" variant="ghost" color="gray" onClick={() => fileInputRef.current?.click()}><Upload size={15} aria-hidden="true" />打开音视频预览</Button></div>
                  <details className="advanced-settings"><summary>项目选项<ChevronDown size={14} aria-hidden="true" /></summary><div>
                    <label className="field-label" htmlFor="project-title">作品名称</label><TextField.Root id="project-title" value={draft.title} onChange={event => updateDraft('title', event.target.value)} />
                    <p>审核方式只在方向、制作方案和最终成片请你确认；自动制作还需要实例授权。</p>
                  </div></details>
                </section> : null}

                {activeStep === 1 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">定方向</span><h2>把想法变成创作方向</h2><p>Agent研究资料、受众和制作可行性，推荐角度与表现形式。</p></div>
                  <EmptyResult icon="direction" title="还没有方向提案">制作命令受理后，真实生成的方向会出现在这里。你可以确认或给出修改意见。</EmptyResult>
                  <Button variant="soft" onClick={() => setActiveStep(0)}><ChevronLeft size={15} />回到项目目标</Button>
                </section> : null}

                {activeStep === 2 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">看方案</span><h2>先看完整方案，再开始制作</h2><p>剧本、分镜、角色与声音共享同一个方案版本。</p></div>
                  <Tabs.Root defaultValue="script" className="plan-tabs"><Tabs.List aria-label="制作方案视图"><Tabs.Trigger value="script">剧本</Tabs.Trigger><Tabs.Trigger value="storyboard">分镜</Tabs.Trigger><Tabs.Trigger value="voices">角色与声音</Tabs.Trigger></Tabs.List>
                    <Tabs.Content value="script"><EmptyResult icon="plan" title="剧本尚未生成">Agent会依据批准的方向提出剧本。你不必预先编写。</EmptyResult></Tabs.Content>
                    <Tabs.Content value="storyboard"><EmptyResult icon="plan" title="分镜尚未生成">镜头的画面、旁白、动作和素材计划将在这里一起呈现。</EmptyResult></Tabs.Content>
                    <Tabs.Content value="voices"><EmptyResult icon="plan" title="还没有角色与声音方案">启用的角色、参考素材和声音来源会随方案显示。</EmptyResult></Tabs.Content>
                  </Tabs.Root>
                </section> : null}

                {activeStep === 3 ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">制作</span><h2>让AI剧组完成视听制作</h2><p>镜头和音轨完成并校验后逐项出现；已有结果会保留。</p></div>
                  <EmptyResult icon="production" title="还没有制作任务">此工作台尚未连接引擎，不显示未经执行的角色状态或进度。</EmptyResult>
                  <details className="advanced-settings"><summary>AI剧组职责<ChevronDown size={14} aria-hidden="true" /></summary><div><p>导演把握创作，执行统筹安排任务，画面与声音落实素材，后期组织剪辑，审片检查结果。按任务启用或兼任。</p></div></details>
                </section> : null}

                {activeStep === 4 ? <section className="delivery-panel"><div className="stage-heading"><span className="section-kicker">成片</span><h2>查看作品与交付内容</h2><p>成片、独立音频和文本属于同一固定版本作品包。</p></div>
                  <Tabs.Root value={deliveryTab} onValueChange={setDeliveryTab}><Tabs.List aria-label="作品内容"><Tabs.Trigger value="video">视频</Tabs.Trigger><Tabs.Trigger value="audio">音频</Tabs.Trigger><Tabs.Trigger value="text">文本</Tabs.Trigger></Tabs.List>
                    <Tabs.Content value="video">
                      {preview?.kind === 'video' ? <div className="media-preview"><video key={preview.url} src={preview.url} controls preload="metadata" playsInline aria-label={`本地视频预览：${preview.name}`} onError={() => setPreviewError('这个文件无法在当前浏览器播放，请选择可解码的视频文件。')} /><div className="preview-caption"><span>{preview.name}</span><Badge color="gray">当前会话预览</Badge></div></div>
                        : <div className="media-empty"><Film size={34} strokeWidth={1.4} aria-hidden="true" /><h3>还没有成片</h3><p>可以先打开本地视频验证播放。</p><Button size="2" variant="soft" onClick={() => fileInputRef.current?.click()}><FolderOpen size={16} />打开音视频</Button></div>}
                    </Tabs.Content>
                    <Tabs.Content value="audio">
                      {preview?.kind === 'audio' ? <div className="audio-preview"><Headphones size={32} strokeWidth={1.4} aria-hidden="true" /><h3>{preview.name}</h3><audio key={preview.url} src={preview.url} controls preload="metadata" aria-label={`本地音频预览：${preview.name}`} onError={() => setPreviewError('这个文件无法在当前浏览器播放，请选择可解码的音频文件。')} /><Badge color="gray">当前会话预览</Badge></div>
                        : <EmptyResult icon="delivery" title="独立音轨尚未交付">旁白和完整混音将分别显示。上传预览文件不会被标成生成的作品包。</EmptyResult>}
                    </Tabs.Content>
                    <Tabs.Content value="text"><EmptyResult icon="delivery" title="还没有文本交付">批准剧本、实际音频转写、字幕及来源会分别显示。</EmptyResult></Tabs.Content>
                  </Tabs.Root>
                  {previewError ? <Callout.Root color="red" role="alert"><Callout.Icon><Info size={16} /></Callout.Icon><Callout.Text>{previewError}</Callout.Text></Callout.Root> : null}
                  {preview ? <p className="preview-notice">此文件仅在当前浏览器会话中预览，尚未导入安装实例。刷新后请重新打开。</p> : null}
                  <div className="delivery-actions"><Button disabled>导出作品包</Button><Button disabled variant="soft">授权引用</Button><Button color="gray" variant="ghost" onClick={() => fileInputRef.current?.click()}><Upload size={15} />打开其他音视频</Button></div>
                </section> : null}
              </> : null}

              {activePage === 'assets' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">素材库</span><h2>让已有资料进入创作</h2><p>文字、图片、音频和视频由安装实例保存，记录来源与使用范围。</p></div><EmptyResult icon="plan" title="实例素材库尚未连接">已选文件可以进行当前会话预览。真实导入功能会通过实例受控接口提供。</EmptyResult><Button variant="soft" onClick={() => fileInputRef.current?.click()}><FolderOpen size={16} />打开音视频预览</Button></section> : null}
              {activePage === 'tasks' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">任务中心</span><h2>创作任务都在这里</h2><p>桌面、API与MCP发起的任务使用同一份执行记录。</p></div><EmptyResult icon="production" title="尚未连接任务记录">连接引擎后可读取真实等待、失败、恢复与结果待核实状态；不会用页面定时器模拟进度。</EmptyResult></section> : null}
              {activePage === 'settings' ? <section className="result-panel"><div className="stage-heading"><span className="section-kicker">设置</span><h2>使用你自己的能力</h2><p>本地工具免产品注册。自有模型和官方服务是可选能力来源。</p></div><div className="settings-row"><ShieldCheck size={21} strokeWidth={1.6} /><div><h3>本地工具模式</h3><p>本机草稿可离线编辑。实例项目与凭证接口正在接入。</p></div><Badge color="teal">免注册</Badge></div><div className="settings-row"><Sparkles size={21} strokeWidth={1.6} /><div><h3>模型与资源</h3><p>在实例配置中保存凭证与授权路由；此页面不会读取本机密钥文件。</p></div><Badge color="gray">待接入</Badge></div><div className="settings-row"><FolderOpen size={21} strokeWidth={1.6} /><div><h3>数据目录</h3><p>项目、素材与成片留在安装实例；此探针草稿存于当前浏览器。</p></div></div></section> : null}
            </main>

            {assistantOpen ? <aside id="creative-assistant" className="creative-assistant" aria-label="创作助手">
              <div className="assistant-heading"><h2>创作助手</h2><IconButton size="1" variant="ghost" color="gray" aria-label="关闭创作助手" onClick={() => setAssistantOpen(false)}><X size={17} /></IconButton></div>
              <div className="assistant-empty"><Sparkles size={20} strokeWidth={1.6} aria-hidden="true" /><p>创作开始后，这里显示已执行任务、待审核事项和指导范围。</p></div>
              <label className="field-label" htmlFor="creative-feedback">指导意见</label><TextArea id="creative-feedback" size="2" value={feedback} placeholder="例如：表达更年轻，只修改第三镜头。" onChange={event => setFeedback(event.target.value)} />
              <Button size="2" disabled className="feedback-submit">提交指导</Button><p className="small-note">等待产物版本及审核接口接入后提交，不会把意见当作扩大授权。</p>
            </aside> : null}
          </div>

          <footer className="probe-footer"><span>Gate0界面探针</span><span>尚未连接制作引擎，未提交模型调用</span><Dialog.Root><Dialog.Trigger><Button size="1" variant="ghost" color="gray"><Info size={13} />运行说明</Button></Dialog.Trigger><Dialog.Content maxWidth="460px"><Dialog.Title>当前运行范围</Dialog.Title><Dialog.Description>这是实际React工作台的Gate0布局与播放探针，制作引擎将在后续接口交接中连接。</Dialog.Description><div className="dialog-copy"><p>输入会保存为当前浏览器的本机草稿。音视频可通过文件选择器预览，刷新后重新打开。</p><p>没有模拟制作进度、成功结果、模型调用或作品包。实例保存、任务恢复和受保护媒体播放仍需接口联通验证。</p></div><Flex justify="end" mt="4"><Dialog.Close><Button>知道了</Button></Dialog.Close></Flex></Dialog.Content></Dialog.Root></footer>
        </div>
        <input ref={fileInputRef} className="visually-hidden" type="file" accept="video/*,audio/*" aria-label="选择本地音视频预览文件" onChange={event => { choosePreview(event.target.files?.[0]); event.currentTarget.value = ''; }} />
      </div>
    </Theme>
  );
}
