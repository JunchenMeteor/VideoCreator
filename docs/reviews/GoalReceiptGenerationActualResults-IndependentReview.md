# GoalReceipt 契约生成实际结果：独立限定评审

结论：**LIMITED_ACTUAL_GENERATION_AND_TYPES_SUPPORTED**。固定本批的唯一 schema exporter、GenerateContracts 与 strict TS7 noEmit 实际结果、原进程/字节流、产物来源及 legacy JSON 数学语义有有限支持，未发现新的确认 P1/P2。该结论不是新运行授权、RuntimeBinding、真实 SQL/HTTP/MCP/Owner/native 安装或 R1/R2 验收通过。所有旧失败、部分输出和未测范围保持。

## 输入版本与独立核对

任务卡 SHA-256 `5ca173468e8cb6ead1595c5806ff8a7d9e796367c5bd3b0dddedce5b51c03097`。正式根为 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/GoalReceiptContractsPreparation/ExecutionFormalStage`；其 Handoff.md `019b73f089e96a9e71f7abda8c097717c2d2f308f83e4377e0ac931fac8bd009`、Handoff.json `62eff4aff4e062bab52ad07dc31e1af942261a5d73d0cf9eb649d77da158249c`、Freeze.json `3ee338e05b1c32f016c8d4d338406891014ef10c98b9e47557d122984611f0cb`、ToolTerminal.json `0783b117462aeccd7a42e1086ae356a04eeab17fa01c987bae2a8d3ef8f142a8` 均按原完整字节核身份。

OrdinaryIndex 共 139 件：8 新产物、7 原执行材料、2 Node trace、12 固定准备材料、8 旧产物基线、102 固定 Backend 普通源。全部大小/SHA 独立核对，无差异。另读取四份原已冻结 generator/exporter 普通源码，逐件与本批 Plan 的原工具身份相同；没有读取后端 ADR0049 热源或用当前源码回填旧运行。

末次有限输入核验为 **156 个唯一文件，changes=[]**。完整 before/after 的 6909 条运行收据由评审独立逐完整 path/bytes/SHA 比较：两侧各 6909 唯一路径、无重复、差异为空。该解析没有重新扫描或重新执行 6909 个环境文件；它支持原收据的完整比较，不扩成全机或 OS 资格证明。原 physical membership 表包含 192 个选择根；原 runner 的真实递归成员比较记录 `physical_membership_changes=[]`。没有独立保存每个根的第二份全部成员清单，故本评审不冒称重新审计每个 OS 文件系统观察。

## 原真实命令与生命周期

原唯一批次 exec `ef10f8` / session `13080` 由原 owner 观察至 `003094` 自然退出 0，再正式 true AgentFINAL；未生成第二批或重跑旧失败。实际原 CommandReceipt SHA-256 为 `8c5f109c5904b59b847ba0a1bae93e530492e916a53eef1083b87e247d039fa3`，固定普通副本与原身份一致。

| 原命令 | 原 PID / creation UTC | 终态与字节流 |
| --- | --- | --- |
| Node GenerateContracts，带固定 source snapshot 和 skip-native-file-observation | 38764 / 2026-10-10T09:32:46.0847173Z | 自然 0，stdout/stderr 原 BaseStream 双 EOF；stdout 原 60B JSON 记 schema_count 168，stderr 0B |
| strict TS7 noEmit，入口 packages/api-client/src/index.ts | 15936 / 2026-10-10T09:32:51.7182237Z | 自然 0，双 EOF；stdout/stderr 各 0B |

两个原 Process 的 owner_errors 均空，timeout_sticky=false、force=false，原整体 actual_exit=0。生成期限为 900 秒、类型检查期限为 180 秒；完整固定 runner 第 32–61 行在每个成功 Start 后保原 Process/创建时间/原两流，等待原自然终态与 CopyToAsync EOF，超时/观察错误锁存并阻断后续命令。它不靠 marker、输出存在或后来的返回洗绿，也没有在本次触发杀进程/重启。其期限是持续观察并锁存失败，不宣称任意阻塞路径会在期限内被硬中断。

原 Node hook 记录两个合法同步子调用：Python PID 26492 的唯一 ExportContracts.py、Node PID 22064 的 object OpenAPI generator，两者 status=0、signal/error=null，完整 executable/argv 与固定 allowed_children 一致。此处只支持 spawnSync 实际返回；没有各 nested child 独立 creation/Job、独立两流或所有后代 OS 隔离证据，不能扩成原子 Job 或整进程树验收。

## 唯一来源、trace 与版本

实际 GenerateContracts 使用 `--source-snapshot` 分支，不是 hand-authored schema 或 `--export-inputs` 替代分支。固定工具身份：GenerateContracts.mjs `7939b24b33d24970dc6626849d767a0b2b8ec0cb424218f2c4ff6536543a08af`；ExportContracts.py `bafe8b5b926d4cf1ceaa522eb7295c438ed0d403a46763c0f76bfb9115d92ac4`；GenerateNativeContracts.mjs `1f6d48ed6983f136deb14ac2b2a53239b8f5effe684e21e2ee65950661cf3887`；GenerateOpenApiTypes.mjs `ee3c4c0430478d3eefbcdcb44d707f219b943576e642b1280b8ddcd2ffcef60b`。四者当前 Plan 与原普通副本字节一致。

Exporter 原第 39–75 行绑定完整 102 源 snapshot、固定普通目录及每件 bytes/SHA；第 106–139 行将实际产品模块编译定位到这些原副本，拒绝 media/provider/workflow 和未列模块；第 199–205 行只运行原 `video_creator.cli.main export-contracts` 并在 finally 保存真实 trace。原 CLI 第 81–114 行使用 schema-only ExportEngine/ExportDatabase、原 create_app OpenAPI 与唯一 Pydantic 模型，再用 TypeAdapter 导出原 Association union，没有构造真实 EngineService/数据库或执行 lifespan。SDK 类型生成器使用官方 openapi-typescript 7.13.0 的 object API，固定本地对象且仅允许内部 `$ref`，没有另外维护模型。

独立逐字段 trace 比较结果：

- 102 snapshot 条目各 before_export/after_export 与固定 source_map 完整身份相同，changed 均 false；36 个实际载入 Engine source 的 before_source_read/after_export 同样一致。
- 1145 audited read identity、464 loaded environment identity，合并去重仍为 1145；每个实际完整路径/bytes/SHA 均在本 Plan 中，无未准入或身份差异。denied_runtime_imports=[]、source_changes=false、snapshot_source_changes=false。
- 两 Node trace 分别为 359/2 个实际模块；逐模块 bytes/SHA 与固定 module pins 一致，denied=[]，两 child 的范围与返回符合原准入。hook 的 load 前后检查、常见 spawn/network/dlopen 限制只属于该工具内存/模块观察边界，不是任意文件系统或 syscall 沙箱。
- native_file_observation_performed=false，native mode 明确 **not_observed**。正常工具 native 扩展/DLL 加载不因这一批成为产品 OS/native 资格。

固定 Backend index 为 `0bbbd04a5014b0b512ed64d077b9058d80abfb24bb7178a68541ef7936adbd5e`。实际 generation manifest 7 个输出 SHA 与真实新产物一致，106 个 sources 对应 102 原 Backend 源及 4 个工具；current_backend_source_bound 指源关联，native_runtime_ready 仍 false。API 版本 0.1.0、contract 0.3.0-candidate 与旧版一致。

## 新 DTO 与完整 legacy 数学语义

比较器仅用标准库解析原固定 JSON：数字采用 Decimal 精确值、布尔与数字类型分开、拒重复键和非有限数、对象键顺序忽略、数组顺序保持；没有以两侧同浮点舍入求绿。完整结果见本过程 `ExactJsonComparison.json`。

| 完整原范围 | 新范围 | 独立结果 |
| --- | --- | --- |
| schemas 162 | 168 | 原 162 无字段/数组/类型/精确数值差异；新增 QueryV1、AcceptedV1、PendingV1、DeniedV1、AbsentV1、AssociationV1 |
| OpenAPI paths 41，components 101 | paths 42，components 106 | 原路径、components、安全/版本不变；新增一个 POST 与五个组件，union 第六项在 schemas 独立导出 |
| native operations 44 | 45 | 原 44 operation/原 components 完整无差异；新增 lookup；operation_count 44→45 合理，openapi_sha256 与实际新 OpenAPI 字节相同 |

本轮没有在上述原范围发现精确数字值或数字 token 表述变化。原 ProjectGoalInput、ProjectGoalAccepted 与 `create_project_goal` 原路径/语义声明保持。新路径为 `POST /api/v1/project-goals/receipt-lookup`，operationId `lookup_project_goal_receipt`；200 四状态 union 与 Query 恰好四个 required closed 字段（format、expected_instance_id、idempotency_key、goal），additionalProperties=false。

固定原 `domain/daily_project_authorization.py` 第 300–371 行显示严格 Query/Association、原 Goal parser 与原 32MiB 边界、state discriminator。Accepted 继续关联原 ProjectGoalAccepted 与实际 ProductionAccepted，原 validator 检查 instance/Goal 及 Project/Production/Run 交叉字段；Denied 必需 reason_code 与正整数 resolved_at_us；Pending/Absent 不虚构 acceptance。canonicalization_id 是 `project-goal-pydantic-json-v1`，不是前端 JSON.stringify bodyHash 的同义词。JSON Schema/TS 类型不能表达全部模型 validator、权限和 SQL 历史校验，类型可编译不证明这些已经在真实调用中执行。

原 API 第 230–237 行使用该唯一 Query/Association，委托原 Bundle lookup 并设置 no-store；生成 transport 保留 current principal、production.read/playback、非 mutation、automatic_http_retry=false、真实权限边界与“无单独 raw HTTP cap”的明确声明，不将 IDs 当授权票据。

纯字面量解析（不执行 JS/SDK）进一步确认：routes.generated.ts 的 45 项与实际 OpenAPI 所有 method/path/operationId/MIME 完整相同，原 44 没有删除或值变；native.routes.generated.ts 六个实际 const（manifest SHA、版本、transport、constraints、components、routes）逐项与实际 manifest 相等。Native 的 106 components 与实际 OpenAPI 完全相同。schema.d.ts 的 Query 四 required 字段、200 四状态 union、Accepted 的原 receipt 引用与 Denied 原字段真实存在。strict TS0 只覆盖该实际 index.ts 类型入口，未执行消费者或 Frontend。

## 八个真实产物身份

以下均核固定普通副本；8 件均 UTF-8 无 BOM、LF。完整 SHA 保留于 OrdinaryInputs/InputSnapshot，不读当前未来热产物。

| 产物 | bytes | SHA-256 |
| --- | ---: | --- |
| openapi.json | 596277 | e1f4011cbd16e9524c80696a070cf948f1459978d55530ae2b02dec16cc6e270 |
| schemas.json | 1024228 | 9ec1bf40aedf6cbde96bdc5584ffc9c140c44e8cbc9c10f3c2089605b29e7001 |
| export.sources.json | 726082 | a27f81b71ae23f93bf379c1d3723e3ab46ed54862db782e9856e8d72650fcf1c |
| NativeRouteManifest.json | 574488 | dda0e91565aecbbbbc9f278b7a8549d66479d57176375435385e1c5b5c3e7f3c |
| generation.manifest.json | 16163 | 113f4dde5ac0ac2a9af58de17f3f97479b4e519300d8e93eb4e7645703507b64 |
| schema.d.ts | 363270 | d20e700ce75189157869e0c505e27b604958f5a0a0830af39802646b32b8ab1f |
| routes.generated.ts | 37333 | a25a29ec1ea8215cb87ad4432916110d1fdfa60ce39d8f7a1725eabaaf08dd87 |
| native.routes.generated.ts | 533854 | ab689160ae1efc9df3b8951feafff76b3f83709f834f9a34c07f7a59468ccc5d |

## 历史、限制与终态交接

原 I44/I62 的 child 0/overall 1、原准备失败、部分候选与 material 门禁三次失败均不改写。新的生成 0 不能用来关闭 GRRP-P01 的独立 Test19 入口问题、真实合法 accepted/pending/history NOT_READY、旧 native/Owner/安装/媒体或 R1/R2 门禁。

本评审自己查 `SourceFreeze.json` 不存在，准确文件名由该唯一正式根确定为 `Freeze.json`；保存 LocatorError，不当产品失败。自己输出完整索引时截断，按原数据独立核 139 件并定向补语义；另有 `e86c40/1` 展示用 Query 名漏 V1、`46445d/1` 将 nested snapshot identity 误作 direct 字段，均保存原失败并以精确结构有限补读，不重跑产品。SDK 字面量初始对 native const 名的推测不正确，原 preliminary 保存；随后按实际 GenerateNativeContracts 第 43–48 行六名称核实，均相等。这些是评审派生/展示错误，不是原 Generate/TS 结果变化。

真实 SQL/HTTP/MCP Goal association、合法 authority/floor/原 intent/body/key 与 unknown恢复、具体 native consumer/Owner/human、安装、ASR/媒体/精度、多模态三 OS 完整产品都未由本批验证。没有费用、网络、模型、密钥或新产品进程执行。完整 R1 独立验收后连续完整 R2 的目标不缩减。

过程证据固定在 `G:/开发测试/Codex/VideoCreatorImplementation/Review/GoalReceiptGenerationActualResults`。后续实际 SDK/UI 消费与 Test19 是分开的门；本评审仅交有限生成/类型/字节来源支持。最终工具终态与读者释放由 FinalHandoff/FinalizerTerminal 及实际终态消息记录，不以报告存在证明尚未返回的工具结束。
