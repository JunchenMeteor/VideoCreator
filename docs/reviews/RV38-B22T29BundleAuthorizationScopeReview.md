# RV38：B22/T29 授权原件项目范围有限独立关闭评审

结论：**FINAL；RV34-P01 / P2 在固定 B22 strict/pure 与 T29 实际隔离服务的原件消费范围内关闭（CLOSED_FIXED_B22_ORIGIN_SCOPE_CONSUMPTION）。** 本轮没有发现该窄修复的新阻断。不代表完整 foreign import、完整 Bundle、真实 Owner/安装/许可权源、RuntimeBinding、ASR 精度、Gate 或 R1/R2 通过；这些仍缺独立实际证据。

## 1 固定身份与实际读取边界

B22 唯一普通源码根：`G:/开发测试/Codex/VideoCreatorImplementation/Backend/PortableAuthorizationScope-B22/SourceCopies/`。T29 唯一普通副本根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T29BundleAuthorization/`；全部路径按正式 Manifest 的 copy 字段消费，未猜相对正文位置。

| 正式输入 | SHA256 |
| --- | --- |
| B22Handoff.md | c70d03b484ed98f1cbd7c8cd6f1ac65068ebf880d70520a25a488ebaa4effa7b |
| B22Handoff.json | 475cfacc628a2355249b45795e03944db73bd74300f6dbcdb122176ba5708d8d |
| B22Interfaces.md | aafa2226fc0ffb71a38817a540d4651ab17ed1138b4a751660045f04b706d181 |
| B22 SourceSnapshot.json | 2991d74fc2015a8f44297cbbd29888aee14989a015f5cad3fa97a65bb502257b |
| B22 AcceptedSourceChanges.diff | 625b91fa3105cd3d9f13cfd203ea10cb00fd0415c701c89515e541623e8aba09 |
| T29Handoff.md | 27be060fd2fe6c4a00dc2c6887222c4d25eff2a05e9c3ce4725c164e6a1129a5 |
| T29Handoff.json | 034bea85df71cd42ff0764078e7df498188a28a9b430c63ab40e5f5b41049b1b |
| T29HandoffSnapshot.json | 919b7f85ea7a3405bf846c213b6ac49c549e38d74f700b4134350e00850209e5 |
| T29OrdinaryManifest.json | 5c5090b5c74bff4650a885f30b9b7b8a581ab5112b4258dce5ac1d9b49b47106 |
| T29TerminalReceipt.json | daab70423b12fa5013b370927a6b8feeab6bb867a13789722caf38705fc1619f |
| 原 RV34 正式报告 | def42d898601d2fa3dac3da5efe93debb6469c7801d08f7e9c12ee22d77ccc00 |

B22 的47份源、T29的111份普通副本和上述11份正式输入，共169 pins，SHA/size无不匹配；全部47份 T29 Backend source 与 B22 对应普通源逐项相符。末次169项无变化。只核固定普通副本、相关完整方法、原 raw/JSON/XML；没有全文审计47源全部正文，也没有读 B23、I32、A24 或其它当前生产/WIP。

## 2 RV34-P01 的源码关闭依据

以下相对于 B22 `SourceCopies/services/engine/src/video_creator/`：

- `domain/production_authorization.py`，SHA `73f89e3e038c496eec1678ffb6ec3132bf5f42145bb55aa79ae975dd58d8720a`，ProductionAuthorizationDocument349–365，新增357行 `owner_action.project_ids != policy.project_ids`，连同350–353的同instance和356的同owner，等价原 ProductionPolicyRecord190–198 的完整有序三元关系。
- `application/bundle_authorization.py`，SHA `edd2739ba12e1527e0a5b05f69512458814e2a835d6f9f29e9560ca5b83d936d`，validate_portable_authorization27–68，55–63直接比较 `(action.instance_id, action.owner_subject, action.project_ids)` 与 policy 同三元组。不是交集、set相等或只覆盖Manifest一个项目。
- 固定 `application/bundles.py`，SHA `8d7b8f73ffd5ed260a8e263d9a58ddfa3690f5d33c69cda713f21544d2628df5`，validate_text151–189仍把 strict Document 解析错误映射为 bundle_text_invalid/422；stage_material732–749在写入前调用strict解析；_import_documents1760–1779按真实role/path/MIME dispatch；_parse_import1838–1839及 _validate_import_relations1844–1847仍调用纯origin关系。

既有local current145–173仍核同instance/Production/Run/request、原immutable admission ledger、实际current policy/action、当前fence plan和ready receipt。foreign不能把portable字节变成本机执行许可。未为修复造current=True、安装记录、grant或fake人审，未增加未批准的时间/registry因果规则。固定diff只列上述两个局部hunk；本轮不重新执行/apply diff或回填旧B20/B21证据。

## 3 独立实际证据：拒绝确实触达消费者

实际批唯一8730c5/session16820→2696fd，原tool自然0。原Stderr.bin SHA `96c64b43fa92be30f989dd7e3902ba66e7d3d44163cfb7e0fe98872c6fecaabd` 记录9组、28.675秒、OK；JUnit SHA `55d5568dbfbe66f4f1fc47ef1ee82b990dc37bc824607c529b2a892a38c84013` 实际9 testcase/0 failure/error/skip，没有time属性，耗时来自原stderr。wrapper36736/creation134359770249053091与Probe31820/creation134359770262904689留存真实退出0、forced=false、lifecycle_errors=[]；不是marker、PID消失或owner摘要代exit。Review没有重跑。

固定 ProbeT29.py SHA `212fb6777d1f799dfd0f01c4b8669f390335a5d86a8abd9205c2730abab6927d` 54–74及 OriginFixtureT29.py SHA `1a4d230a062e751b08934a6bd87d906807f60d87a3442f48375730fc36d5f631` 79–94以真实Engine/issuer产生的原材料为基准，仅改变Owner动作项目范围并更新action ref、原件bytes和Manifest artifact SHA/size。实际原件为：

| 变异 | 原byte文件SHA256 | 实际范围 |
| --- | --- | --- |
| RehashedScopeMutation1.json | b43ed7cb6455ad3444e19fe21679ea04d729dea7df4619ffeb412921f8e796a8 | 外部项目 |
| RehashedScopeMutation2.json | f5b2560e4564050e550dc98e6a7858d8fc091c3c72ad6a55a73f588afe908bbb | 空范围 |
| RehashedScopeMutation3.json | 65afa024b41897946b01c2f5e2a2c65109a91ee38b7c75e6b36ca66144bbe87e | 原项目加额外项目 |

每份实际触达四入口：strict validate_text→bundle_text_invalid/422；typed pure→production_authorization_scope_conflict/422；private _import_documents→bundle_text_invalid/422；stage_material→bundle_text_invalid/422。Events.json SHA `94bbf5b4ac4a39cc755b5a54183571fac347391c7fdc26571fb12e83f42738e2` 逐项保留12个顺序一致的scope拒绝，case绿不是未达断言。typed负例使用model_copy明确绕过strict构造，只为了独立验证pure入口，未用这个对象取得许可。

Review仅用标准库解析既有副本，独立重算三原件canonical LF bytes、嵌套Owner-action SHA与不变policy SHA，并在内存还原原project/ref：三份均还原到同一个原ready材料SHA/size且完整原件相同。此为既有字节关联分析，不是再次执行Pydantic、产品或Test。原stage/read_material实际断言原bytes保持；Scope末层SQLite行仍两项ready/一项prepared，无新发布或导入。

合法原件由真实Engine.commit_creative_revision、issuer.production_admission/authorization_document和Bundle.prepare/stage/read生成；strict/pure、窄文本分派阳性确实运行。FixtureInstallationAuthority只对自制Registration/Resource/Runtime fixture逐文件核hash；synthetic principal和公开dummy credential只支持机制，不能授真实安装/Owner或法律资格。没有shadow BundleService、手写ApprovalRef、SQL伪造published或恒True媒体/精度/权源validator。

## 4 覆盖和明确未覆盖

ActualMethodCounts.json SHA `622dc5569785246194463336c42bed3eca4d286f7c4eb5a3dfe8c8ac5b6b1dfd` 用sys.setprofile对冻结源实际call计数，独立核原方法及测试调用链：strict62、pure8、authorization_document8、stage8、_import_documents4、local_current4、_validate_import_relations1、approval_refs1、publish1、publication_scope拒绝1、selection1。未出现的verify/import_bundle/_finalize_bundle_current为0。

150原event中实际10隔离实例（含foreign收件者）、29拒绝、3即时SQLite快照和10末层BundleRows；16个保存文件与event路径→ordinary映射、SHA及JSON值全一致。3即时快照均Run running、0 Operations/Steps；原件/foreign fence1、人审释放后重取fence2。全部末层无published、imports_count=0，8原件case仅两ready文本/一prepared revision，foreign与人审case没有Bundle revision。不是完整ledger制作或final writer证据。

人审阳性确实经wait_for_review/submit_decision/acquire_run/approval_refs，核同Run/target/key/decision SHA；scope撤销确实拒旧local doc且原bytes不改。坏kind/path/MIME、immutable409及等长度ready文件篡改422实际触达。private两文本dispatch不是完整foreign导入；唯一_import_relations故意停在import_incomplete/422。selection只扩视频→authorization→plan依赖；没有实际grant/export许可阳性。唯一publish是无verify cache的坏token409，未触达最终writer。

8输出/17固定附件结构carrier的其它媒体与文本是明示NOT-REGISTERED/NOT-STAGED dummy字节，未解码/ASR/独立标注或听看。完整verify cache→同writer final fact+publish、真cache跨thread/context/fence、unknown/not-settled与事务rollback、政策替换后的同Run新prepare、完整foreign import、projection全依赖grant及licensed再分发、完整human script/quality和policy-only复制消费者这七类Pending仍缺实际作品/资源/真实权源或故障接口。CompleteConsumersT29.py虽有具体驱动，实际批未调用，不将函数存在授launch或通过。

原完整标准、default8/maxN/200ms/MM05不降；Owner-action时间/registry因果仍只是原RV34 inspection。原T26 NOTPASS、T27机制范围、T28独立闭合及自动审查拒绝分别保持；RV35-I01仅收到新append-only计数说明，旧冻结不改。本轮不重审旧T27 maps、不代人类允许拒绝源或native接线。

## 5 输入、终态与后续资格

原T29观察1289 records、3577 record唯一路径、3589 actual before/after路径；Review解析原保存maps，完全相等，全部record路径包含在实际观察中，三口径不混。没有再次对共享runtime/current生产取hash。自身169 pins末核无变化，47 B22/Test源成对一致；固定reader/tool全终态、live=[]、freeze=false。

自己的FactsCheck/Snapshot/InputPins/SourceAfter/Handoff集中在 `G:/开发测试/Codex/VideoCreatorImplementation/Review/BundleAuthorizationScope-RV38/`。工具宽读278fc1/f38999/57012f有截断，必要源码方法分别有界补读，不声称截断内容全审；T29原误猜路径及宽读问题仍为工具过程错误，不洗成产品红。Review没有产品import、测试/DB/解码/native/ASR/model/provider/key/fee/network/install/apply。实际测试及安装/许可/完整Bundle验证仍归Test/各实现owner/独立Acceptance；本关闭不授RuntimeBinding或Gate。完整R1三OS独立验收后连续R2、数据安装实例持有、五步前台保持。
