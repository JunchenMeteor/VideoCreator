# ADR0022：内容读取的许可闭包与当前授权有效期

2026-10-08。状态：**架构准入，Backend 实施与独立验证待完成**。增补 ADR0021；不批准真实权利 authority、许可证、metadata/API/native 运行或 Gate0/R1/R2 通过。保持完整 R1 后连续 R2、实例持有数据与原五步/质量门。

## 1 固定事实与明确范围

已核 B16 SourceGap `73eedd84f984bd122c43d927ddc4ce04e152faded451e0aff93e30f22cb276b8`、Snapshot `43609265959106c3cbbb15925a4336a5809293a1726921b0b2fb38de3804b45e`、Handoff `bf9919442cac164b68e5f984299a1967eb75dc77fcac15221a6d05e83df9fe1b`。只读四个完整相干 before 普通副本的必要调用链及已停写阶段材料，未读活生产源、import 或运行。

旧 `_visible` 对活跃 grant 使用 any 匹配，但不返回选中的路径，不比对 row/body expiry；`_rights` 只核直接选中的 RightSnapshot。whole Manifest 原两次 `_visible` 最终要求一个允许全部 artifacts 和 semantic 的 grant。leaf 只经 bundle.content，不要求 whole Manifest。import 为本机 owner/project/principal scope，不借外国 origin grant；export 已另核原 request 和实际 selection 的许可闭包。

B16 当前仅 DTO/六 metadata 路径/声明阶段代码停写，五 Bundle metadata 仍 `delivery_metadata_facts_unavailable(503)`；阶段 Ruff/AST0 不构成导出或运行。该临时守卫必须在本轮由真实 resolver 替换，不能永久用503/null占位成品。

本决策限定**既有内容读取与相应 metadata 的事实解析**。不改旧 Bundle/Ref/Accepted/Receipt/请求默认、DB5、幂等输入或已发布原字节；不顺带重写 grant 创建、发布 authority、制作/取消或外部平台权限。

## 2 两个集合、两种使用语义

共享 resolver 必须明确区分：

- **对外目标集合 T**：本请求真正返回的 leaf、整份 Manifest 所披露的全部 artifacts，或原 export journal 的实际可移植 selection。请求 operation/purpose、grant 覆盖和 semantic 披露范围只按这一实际对外集合及原 scope 判定。
- **内部必要闭包 V**：从 T 出发，在同一实际不可变 Manifest 内遍历 `dependency_artifact_ids`、每个节点 right 的 `license_document_artifact_ids`，继续其必要依赖与许可引用。用于验证内容的原索引/来源许可与有效期，不因服务读取就对调用方披露这些节点。

leaf 请求 T 只有该 artifact。许可正文或依赖未在 T，不要求调用方另有它们的公开 grant、bundle.read、allow_semantic_text 或下载权；不返回它们的 metadata/正文/路径。Backend 以服务内部受控定位核 V，不能借公开 whole-Manifest/get_manifest 端口获取 leaf 事实。

**请求 UsePurpose 只直接施加于对外 T 中实际被使用/披露的 artifacts。**对 V\T 的内部核验不把 leaf 的 playback/standalone_audio/rag_index 等逐项强塞给许可文件自己的 permitted_uses。许可文本允许 export/redistribution 而不允许 playback，不能仅因此拒绝视频 playback；这不证明调用方可导出许可正文。若该依赖本身被另一个内容请求选中或已进入 export selection，就作为那个请求的对外 T，核自己的实际 UsePurpose/公开 scope。

内部节点的 RightSnapshot 必须是完整合法的原索引声明，范围/用途非空、身份与原发布事实一致，其**有效期**与必要限制仍约束当前必要闭包；不能因 proof-only 跳过 not-started/expiry。current leaf 的声明不能延长任何必要许可/来源的时间边界，符合 ADR0020 的有效许可依赖交集。内部核验不是新的创作、复制或再分发；制作/复制端仍按 ADR0020 核真实 derivative/export/redistribution 等用途及当前声明，不由读取端补授权。

不从许可 free text、roles、文件扩展、哈希或模型解释推断新许可用途/时间。当前读取以原合法 published Manifest 的固定声明、当前已有受信授权事实及真实本机文件为依据；其范围未知/声明冲突须拒绝或明确缺事实，不能推为无限。合法历史 owned/licensed 包的读取**不新增 prepared authority 准入门**，不因缺新前置 adapter 将旧读取永久锁503；读取事实不宣称重新独立认证法律所有权。

## 3 内部闭包的实际完整性与范围

V 的每个节点须核：唯一 artifact/right identity、原 Manifest/ref/SHA、实际受控 Asset 或 ready Material/导入 mapping、完整文件 hash/size/MIME 与原索引相等。许可引用必须落到实际 `roles=(license,)`、受控 Material、固定 license/text/plain grammar 的原节点；对其正文只做已规定 grammar/实际字节核验，不用字符串自证权利。

本地 bundle 用当前已发布 preparation/items/Asset 的受控身份；import 用本机 ready receipt/import row、原 immutable Manifest 与本机映射，不将源 material/asset ID 当本机路径。许可存在但本机映射未落完整时503明确待修复；原索引缺项/坏 grammar/坏字节/冲突为422，不用缺新authority503掩盖确定损坏。

遍历 rights→license 和 artifact→dependency 的**联合有向图**；校验原列表重复/冲突后才建 map，区分 visiting/visited，共享 DAG 核一次且保留所有入边限制。缺引用、自指或真实许可/依赖循环拒422，不截断、不无限找“许可的许可”。终端是实际固定合法声明及无后继必要依赖的节点，不能凭自引用文档自授 licensed/owned。仅原 artifact-dependency DAG 校验不能替代联合闭包检查。

不把修订祖先的32/256/逻辑字节上限套给普通 Bundle 读取；V 受实际 Manifest 的有限节点/既有实例资源规则控制，流式 hash、只存必要 facts，不将整包载入内存。不得为绕坏依赖而返回不完整闭包，也不暗加新业务大小上限砍成片能力。

**明确兼容变化**：原先虽 direct leaf 可读、但必要依赖/许可已经损坏、未生效或到期的路径，现在必须失败；这是批准的完整性/有效期修复。合法、完整且有效的依赖仅 permitted_uses 与 leaf 不同，仍可作内部证明，不新增公开 grant。修复只影响当前使用状态，不改历史 bytes/hash/已合法导出物；等待修复/取得真实新许可后按明确新声明处理，不自动重生成或收费。

## 4 替代 grant、row/body 与期限

批准保留“**存在一个当前完整匹配路径即可使用**”。拒绝把所有 grant 的 expiry 取最小，拒绝将多个 grant 的 artifact_ids/purposes/semantic 位合并成任何单独 grant 都不覆盖的权限。

非 owner 的实际候选须同时满足：同当前 published preparation、recipient/project/ref、active row、当前 operation/purpose/对外 T 与 semantic 全覆盖；严格解析 body 并核 row.id=body.grant_id、recipient、原 BundleRef/project、expiry 完全一致，row 未撤销且 body 不伪造活跃，created_at/expiry 合法。不用 body 的较晚 expiry 延长 row，不忽略 body 的较早 expiry。DB 为当前撤销事实；不能把 revoke 返回体替原未修改 journal body。

不一致/坏 body 不构成候选，也不补 null；保内部损坏原因。存在另一条完整、有效、一致候选时仍可用它，不让一条坏/已撤销/较短候选取消原 any 行为；不存在任何有效路径时，普通无范围/到期/撤销维持403，证据损坏导致无法确认则422。只在实际已准入当前事实服务未配置/不可取得时503，不以503掩明确用途拒绝。

**选择规则：在所有完整有效候选中选 expiry 最晚的单个 grant，平手按 grant_id 升序。**同一次 selector 的 registration 与必要 right 边界为共同限制，因此这是有效边界最长的一条实际路径。内部保 grant_id/body SHA/row identity，不公开 grant正文或使 grant_id 成为 ticket。earliest-expiry 提案未批准。

每个目标/内部必要节点的 RightSnapshot 在核查时满足 `valid_from_us <= now < expires_at_us`（存在边界时）；null 表示合法声明确实未设该时间边界。实际 registration、chosen grant 与 V 中必要 rights 的所有已知截止做 min，得到：

`authorization_expires_at_us = min(current registration expiry, chosen grant expiry, effective V rights expiries)`

无 grant 的真实 owner/import scope 不虚构 grant；registration 若有限仍须计入。所有适用边界确定且均无时间到期边界，才返回 null；未知、不一致、不可核事实不能成为 null。有效期只代表当前已成功路径的已知时间上界，不是永久许可、全球法律认证或冻结撤销。checked_at 时该非null期限必须严格在未来。

后续 request/Range/保存前重核均**重新枚举选择**。旧 chosen grant 撤销/过期而另一完整匹配 grant 仍有效时，允许在当前重新核验后换路径；不是缓存原 grant、扩大授权或盲重交。共同 right/registration 到期时所有路径都失效。

whole Manifest 用一次明确 `T=全部原 artifacts, semantic=true, operation=bundle.read` 的成功路径替代旧两次 grant 检查，最终必须一条 grant 覆盖全部。它保旧第二次更强约束，不将每 leaf 不同 grant 拼成整包。export 继续原 request/journal/实际 selection 与旧两步要求：完整覆盖其原公开 closure、full 的 semantic 和原内容语义检查均保；内部 V 检查不能代替 export 对被携带许可正文的公开 grant/用途检查。

## 5 一套私有 facts 与实际最终检查

Backend 唯一定义受限私有 resolved-content facts，内容 handler 和 metadata handler 消费同一 resolver 结果；不是 bool callback，不给调用方填“已授权”字段。必要 facts 包含：

| 私有事实 | 绑定要求 |
|---|---|
| current principal/scope | 实际 instance/当前 registration scope 快照/subject/project/operation/effective purpose；不是 renderer/context 自报，不虚构现有 registry 未提供的公开 revision 字段 |
| local content identity | 实际 BundleRef 或本机 import/export locator、原 manifest/journal/receipt/selection 身份及完整版本 |
| content handle | 原受控 path、实际完整 SHA/size/MIME，与真实 Asset/ready Material/原索引一致 |
| T / V 与 edges | 对外目标和内部核验范围明确分开；每 right/file/许可 grammar/原 identity 固定，不对外泄露 V |
| successful path | owner/import 或一个一致活跃 grant 的实际 row/body/ref facts；保替代路径重选能力 |
| boundary evidence | registration/grant/必要 rights 的来源/已知截止与“确知无期限”；未知不能混入空集合 |
| final observation | 实际最终 checked_at_us、重新选择的成功路径与 min cutoff |

执行顺序：①核实际 principal、published/import/journal scope 和初始 T/路径；②在 SQLite 长 writer 外解析同一固定 Manifest、遍历 V、检查实际完整文件并流式 hash；③完成 bytes 核验后，用**实际新的时间**重新解析当前 registration、原 scope/journal/ready/version/索引身份、V 有效边界、current grants/revoke，并重新选择成功路径；④只在原 immutable identity 与已核 handle 相同、事实仍有效时返回内容/metadata。checked_at_us 是③的实际最终核查时间，不能用请求开始/第一次授权时间。

最终检查必须针对全部 public T 和同一必要 V，不能仅检查 leaf 或只看 expiry。registration scope 已变化时保原 principal_scope_changed 失败，当前请求不能悄悄采用更宽新注册。grant 替代路径重选不改 actor身份。短最终 DB/registry 读取不 hash整文件/联网/FFmpeg，不把锁持到网络流结束；文件/权利核验不放长SQLite writer。

该顺序不承诺消灭文件或并发撤销墙钟窗口。每次条件请求/Range也先取当前共享事实，随后才304/206；native依ADR0021在完整保存提交前再查 metadata，同identity与permission仍成立才原子提交。已发送 bytes 不回收，不能据缓存metadata/URI继续绕授权，也不因更换grant变成新的制作/导出提交。

不将 closure 校验无差别塞进所有 `_visible` 调用而改变 grant 创建、production等未涉及的路径。后端可提取共享的当前授权/closure/handle helpers，公开内容与五 Bundle metadata 必须落同一真实解析路线；semantic byte读取继续同时核原 bundle.semantic 与 bundle.content，不以metadata代semantic权限。旧 empty-selector 语义由实际调用类型明确映射，不能让空IDs变“无需权利”。

## 6 API兼容、错误与下游

不需改 ADR0021 的 DeliveryContentMetadata kind/version/字段，不需新的公开 dependency metadata/authority/grant接口或迁移。阶段DTO尚需 Backend 真正 import/schema/CLI export 校验；架构不因静态字段看起来一致冻结其运行。

Backend 对当前内容和metadata的依赖缺失/循环/字节坏与 row/body不一致用唯一 ErrorEnvelope 的422；实际用途/时间/当前grant/scope拒绝保403、principal expiry保401、原隐藏/notfound保404、export非ready保409、本机mapping/真实受信事实未就绪才503。具体 error_code 由Backend唯一声明并交完整OpenAPI，保既有垃圾422/传输400/416等兼容；不得用unknown/null、bodyException500或旧expiry替真实检查。独立Test/Review再核公开声明与实现，不在本文批准标准。

1. **Backend 恢复完整 B16**：按本决策实现共享resolver及五Bundlemetadata真实facts，移除占位fallback；实际 CLI export/import/schema 和六唯一relation闭包验证，交全部改源普通副本/完整SHA/actual operation ID/ErrorEnvelope与失败证据。有限owner运行须另按正式任务批准，不从本ADR获得运行/费用授权。
2. **Integration**：Backend full formal 后从唯一同源export生成SDK/NativeRouteManifest/Rust metadata消费；新私有V/选择证据不生成第二套公开接口。到期重取facts，不能在宿主自行再算grant、读取许可文件或给renderer推权限。
3. **TestDevelopment**：独立准备实际判据和受控fixture；包括两替代grant长短/撤销切换、body-row mismatch与有效替代、单grant不能拼权、whole Manifest与leafonly分界、license own用途不同但有效、许可/依赖到期或损坏/循环、bytes核后grant或registration变化、无期限与未知、非playbackimport与原exportpurpose。同时保存原失败和阶段503事实。
4. **Review / Acceptance / Media / Frontend**：各按角色消费正式实现证据。Media不得补自签rights或改变请求用途；Frontend只展示明确权限/可恢复缺项，不把规则变成每作品额外人工表单；评审和验收独立，设计不是通过票。

完整正常路径须在本轮完成，不因真实许可/provider/机器缺项永久停留在stub。此设计并不补实际许可/authority、成片听审、MM03/MM05、三OS或R1/R2验收。全部来源、工具终态及本轮产品/测试/网络/key/费用0由 Architecture/ContentRightsExpiry-A20 的正式snapshot/handoff固定。
