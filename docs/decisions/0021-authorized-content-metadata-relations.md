# ADR 0021：授权内容与窄元数据的唯一关系

日期：2026-10-08。状态：**架构准入，待 Backend 实现、Integration 生成与独立运行验证**。本决策增补 ADR0019 的保存/媒体事实来源；不证明 native ready、真实权利许可、精度或三 OS 发行通过。

## 1 固定事实与选择

A18 仅读取 B13/B14 固定普通副本和 I25 固定生成契约，未读取 B12 活跃生产源、动态 import 或运行产品。I24 SourceGap 与 Backend Reply 分别固定为 `b097b8e7973719929df3acddd98da9fee09f918c700fd30197957d183cdf5c6c`、`86176dff394151362eb6d3e2dfd036d8847b68f6ef370e9032fa9a210e27ddef`。

已存在的 AssetRecord、受保护 Manifest 200 原字节、ExportAccepted ready 记录和本机 ImportReceipt 是事实来源，但不能构成六类内容通用的宿主前验接口：

- content-only grant 不保证 `bundle.read`/整份 Manifest 可读，不能以扩大 grant、忽略 403 或读全部索引来补 leaf metadata。
- `import_get` 现为 `bundle.read + playback`；不能假定它可在 derivative/export 等原 purpose 下返回 metadata。
- export 的原 purpose 在 journal 中，旧 ExportAccepted 未公开该字段；Manifest/Ref 未提供独立完整文件 byte size。
- B13 app 明确写入 quoted 实际 Asset/ContentHandle SHA256 ETag。只有这六个具体 handler 的声明能建立 digest 关系，不能把任意 HTTP ETag 当 SHA。

**选择：新增一个窄 DTO 与六个一一对应的受保护 metadata GET。**它们共用 Backend 的当前内容解析/授权与实际完整文件事实，不新增 grant、不返回整份 Manifest、不产生新的保存票据。不采用宿主为取得 metadata 而预下载完整 Manifest 的替代路线。

## 2 唯一公开模型与六个入口

Backend 唯一定义 `DeliveryContentMetadata`，独立 `schema_kind="delivery_content_metadata"`、`schema_version="0.1.0-candidate"`，拒绝额外字段。它不是 BundleManifest、ImportReceipt、License/Precision report 的 union；Bundle 原 0.2/0.3 schema、旧默认请求、幂等输入、Accepted/Receipt 字节语义保持。

200 DTO 只包含以下共同字段：

| 字段 | 含义 |
|---|---|
| `schema_kind` / `schema_version` | 上述固定身份；不得依 HTTP Content-Type 猜 schema |
| `local_instance_id` | 当前受信连接的实际安装实例 |
| `locator` | 下表受限 discriminator union；只含本次内容与版本选择所需身份 |
| `state` | literal `ready`；不是 queued/building 的占位 metadata |
| `sha256` | 当前实际完整原文件 SHA256，小写 64 hex |
| `size` | 当前实际完整原文件非负整数 byte 数；宿主直接精确解析整数，不经 renderer 的浮点数认证 |
| `media_type` | 内容 resolver 的实际 MIME；Manifest 为 application/json，archive 为 application/zip |
| `purpose_binding` | discriminator：`installation_owner`（无 UsePurpose）、`content_request`（实际有效 UsePurpose）、`export_journal`（原 journal UsePurpose） |
| `checked_at_us` | 实例时钟的实际授权/完整性核查时间，微秒整数 |
| `authorization_expires_at_us` | 本次实际成功授权路径已知最早到期边界；无时间到期边界才为 null，null 不表示撤销无效或永久授权 |

无需导出 principal secret、grant body、签名能力、私有文件路径或下载 URL。metadata 是当前受保护事实快照，不是可脱离实例使用的 capability。无法落实授权路径/时效事实时保持不可用，不能将未知到期时间冒称无期限。

六个新增路径均为当前内容路径追加 `/metadata`，GET，无 body、Range 或条件请求。真实 operation_id 从 Backend 实际 APIRoute/OpenAPI 唯一产生；表内旧 operation_id 是已存在事实，不猜新 operation_id 的 FastAPI 后缀。

| 现内容 operation_id | 新 GET 路径 | `locator` 与同内容授权 |
|---|---|---|
| `asset_content_api_v1_assets__asset_id__content_get` | `/api/v1/assets/{asset_id}/content/metadata` | `kind=asset, asset_id`；原 installation owner 与该 Asset；不新增 purpose 参数 |
| `bundle_get_api_v1_bundles__revision_id__manifest_get` | `/api/v1/bundles/{revision_id}/manifest/metadata` | `kind=bundle_manifest, bundle_ref`；同 `bundle.read`、有效 purpose、整份 Manifest 原权限 |
| `bundle_content_api_v1_bundles__revision_id__artifacts__artifact_id__content_get` | `/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content/metadata` | `kind=bundle_artifact, bundle_ref, artifact_id`；同 `bundle.content`、有效 purpose、仅选中 leaf 的当前 grant/rights |
| `bundle_export_content_api_v1_bundle_exports__export_id__content_get` | `/api/v1/bundle-exports/{export_id}/content/metadata` | `kind=export_archive, export_id, source, input_sha256, delivery_profile, artifact_ids`；原 journal owner/registration、bundle.export、原 purpose、selection 与完整权利闭包 |
| `bundle_import_manifest_api_v1_bundle_imports__import_id__manifest_get` | `/api/v1/bundle-imports/{import_id}/manifest/metadata` | `kind=import_manifest, import_id, origin_bundle_ref`；同本机 import scope、bundle.read、有效 purpose、整份原 Manifest 权利 |
| `bundle_import_content_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_get` | `/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content/metadata` | `kind=import_artifact, import_id, origin_bundle_ref, artifact_id`；同本机 import scope、bundle.content、有效 purpose、仅该原索引及本机映射 |

BundleRef 原类型原样复用。本地 bundle locator 的 BundleRef.instance_id 必须等于 local_instance_id。export.source 为严格二选一：`kind=local_bundle, bundle_ref` 或 `kind=local_import, import_id, origin_bundle_ref`。`artifact_ids` 是 journal 原 request 的选择，full 时保原空选择语义；闭包由原 export 服务真实重核，宿主不根据这些 ID 拼 archive。不得把 import-origin BundleRef 重命名为本机 BundleRef。

Bundle/import 四个 purpose query 与对应内容入口的 UsePurpose/default 完全相同；native 以实际 OpenAPI 默认解析 omitted purpose，不能自行另设默认。Asset/export metadata 无 purpose query；export 返回 journal 原值，不接受借 query 换用途。native 拒绝未声明参数，Backend 新 metadata 入口对试图覆盖原 journal purpose 的请求明确拒绝。

## 3 事实生成与权限边界

metadata 与内容入口使用同一实际授权解析结果/真实内容 resolver。Backend 可提取共享私有解析接口，不能写第二套较宽的 permission 逻辑。每次 metadata 读取应完成本次 actor/registration/project、grant 当前状态、原 purpose、rights/许可、ready 状态和文件实际大小/SHA 检查，之后由实际内容 handle 与原 journal/receipt/index 生成 DTO。Asset 也必须把 record 与实际文件大小/SHA 对上，不能只复制数据库 SHA 或客户端探测结果。

leaf 的唯一 artifact selector 在 Backend：原不可变 Manifest 中按精确 artifact_id 选一个，拒绝不存在或重复；仅核该 leaf 所需许可闭包。不得为 leaf metadata 调用需要整份 `get_manifest` 权限的公开读取入口，也不披露其他 artifacts、文本、RAG、全部许可文件、工作台状态或语义内容。bundle.read、allow_semantic_text 的原边界保持。

Import 必须核本机 ready receipt/import row、当前 instance/owner/project/purpose、本机 mapping 与原文件身份。metadata 不依赖 playback-only 的 import_get；receipt/index_state 不替代本次内容读取许可。origin_bundle_ref 只作不可变来源溯源；旧外部 ref、SHA、schema 或 URL 都不能当本机授权 ticket、可信 issuer 或精度 qualification。

Export 必须核原 registration/owner、原 request purpose/profile/selection/input SHA、当前 scope 与权利、原 ready archive 的 SHA/size。queued/building/failed 都不能返回 ready metadata；旧 status 路径继续用于观察，不改成提交新 export。跨用途的新创作/分发仍走明确请求及原服务授权；物理保存本次已授权原 bytes 本身不改变其 UsePurpose，也不授后续 commercial_use/redistribution。

expiry 是该成功授权路径的限制，不能延长 grants 或 rights。metadata 读取、内容请求及每次媒体 Range 请求均重新授权；撤销/过期后不因宿主已缓存 metadata、私有媒体 URI 或曾得 200 而继续放行。宿主在保存原子提交前再取同一 metadata，确认权限仍在、身份/版本/SHA/size 一致；失败只清理本次 owned partial，不能修改账本或重新生成作品。服务端检查与文件读取间仍需原 bytes 完整校验；本 ADR 不声称消除所有并发撤销的墙钟窗口。

## 4 唯一声明 grammar 与可信宿主消费

在六个实际内容 operation 的 `x-engine-transport` 上新增可选字段 `delivery_metadata`。原 `engine-http-transport-v1-candidate` 保留；新消费者只启用明确认识的新关系格式，未知/缺关系令 save/media 诚实不可用，不能退回 renderer 自报。

`delivery_metadata` 的唯一 grammar 为：

- `format="authorized-content-relation-v1-candidate"`；`metadata_operation_id` 为本次实际 OpenAPI 中唯一 GET；`metadata_schema_ref` 为其 200 所用的 DeliveryContentMetadata schema 引用。
- `path_bindings`：metadata 参数名 → 当前内容参数名的闭集映射，必须为相同命名的实际声明 ID；`query_bindings` 同理，只允许表中四个入口的有效 purpose。使用对应真实参数的默认值，不允许 URL、任意 JSON 路径、模板表达式、wildcard 或程序执行。
- `purpose_rule` 仅 `installation_owner` / `same_content_request` / `original_export_journal`，与 DTO.purpose_binding/内容声明严格一致。
- `response_binding` 固定 `kind=single_delivery_content_metadata`、上述 schema_kind/version；事实只取 DTO 根 sha256/size/media_type/locator/local_instance_id/purpose_binding，不遍历 arbitrary array 找看似匹配文件。
- `content_integrity` 固定 `digest_header=ETag, digest_encoding=quoted_sha256, complete_size_header=Content-Length, complete_status=200, partial_status=206, partial_total_header=Content-Range`。仅 Backend 对六个实际 handler 写明 quoted 完整 SHA 的源码关系并实现后生效。不得把通用项目 revision ETag、弱 ETag 或 mtime/hash ETag 认证为文件 SHA。

metadata operation 自身声明同原内容 authorization mode/domain_operations/purpose semantics 和 JSON DTO/ErrorEnvelope，无临时匿名 token/header。Backend 唯一维护 Python public models、routes、权限与 transport 声明；Integration 从同一次实际 OpenAPI、export.sources、generation manifest 生成 SDK/NativeRouteManifest/Rust 消费数据，校验 operation/schema/参数唯一性及绑定闭合。不得手写第二张 route/metadata/permission 映射表。新字段可选保证旧生成契约可被识别；不能把 I25 原 31 operations/Manifest SHA 当新关系已经存在。

Rust 的可信起点仍是 ADR0019：已校验子进程 ready、实际当前 instance/session generation、固定 loopback 及源守卫，Bearer 留宿主内部。renderer 的 delivery_ref 只选择实际 operation/受限 IDs；renderer 的 SHA、size、mime、任意 URL、外部 origin 身份不得成为事实。宿主验证 metadata 的 kind/local identity/完整版本与本次请求一致，再自行使用同一 content operation、原 purpose 和当前 principal。metadata 的 URI/ref 不能越过 native allowlist/source/capability guard，也不能作为网页下载票据外传。

完整保存使用未消费 response、无 Range/条件请求的 200，要求 quoted SHA、完整 Content-Length、实际 body length 与 metadata 一致，并流式计算完整 SHA 后原子提交。若传输缺/错 digest 或完整 length，拒绝本次 save；不能信 MIME 文件扩展、generic ETag 或另一个请求的 body。完整保存不接受 206/304；206 的 Content-Length 仅 segment 长度，Content-Range.total 须等于 metadata.size，304 无 body 不能证明完整性。未新增 HEAD、asset 304 或跨源 redirect 支持。

媒体沿 ADR0019 的有界 Range/backpressure 与每段授权，核同一本机 locator、purpose、完整文件 SHA/size/MIME 关系；不将单 segment 冒称全片 hash 验证。媒体 URI/handle 仅本进程当前 generation，关闭/退出即失效。完整成片、旁白/mix、字幕、文本/RAG 均依各自实际内容；本关系不能代替真实媒体制作、MM03/MM05 或报告许可闭包。

## 5 失败、兼容与交接

新 metadata 用唯一 ErrorEnvelope 明确声明业务失败：401 当前认证无效，403 当前操作/用途/grant 被拒，404 不存在或按原 owner/project 隐藏，409 export_not_ready 等实际阶段，422 原 index/ref/mapping/bytes 完整性失败，503 本机映射/可信事实服务未就绪。非法 DTO/query 继续既有请求验证语义；不要改旧错误状态以凑 native 绿。宿主遇关系/身份/版本不符拒本次 save/media，向用户保真实原因，不盲重提创建/export/import。

本轮 owner：

1. **Backend**：实现上述唯一 DTO/六 GET、共享受限 resolver、purpose/ready/integrity/expiry 事实和 OpenAPI 声明/ErrorEnvelope。交实际 operation_id、源 SHA、普通副本与新 CLI contract export；不得扩大既有权限、抹掉历史失败或读取其他角色 WIP。
2. **Integration**：收到 Backend formal 后再重生同源 SDK/NativeRouteManifest、接 Rust save/media 的 metadata preflight/原 bytes/commit recheck；保持 Bearer 私有和数据流限界。当前 I24 source compile0 不作联调通过。
3. **Frontend**：只消费实际 SDK 的本机 save/media 及错误，保五步体验；不采 renderer SHA 作为授权、不接任意 fs/URL。
4. **TestDevelopment / Review / Acceptance**：各自准备/批准/执行独立判据，覆盖 leaf-only 正向+whole Manifest403、非 playback import、journal 原用途、queued/ready/撤销/到期、跨 instance/origin 身份、wrong MIME/size/hash/206/304、保存重核和真实媒体 seek；这里是验证输入，不代写或批准其 criteria，不以 fixture/编译成功当实际权限或用户验收。

本决策无需 DB schema migration、新框架、额外商业服务或凭证；若实际实现发现确需公开字段偏离，应固定 source gap 再裁定，不能自行换语义。尚缺实际 Backend/SDK/native 端到端、>128MiB/资源约束/撤销竞态/三 OS 证据；商业生成服务、许可证、benchmark/authority 与原 Gate0/R1 验收继续保持未通过。完整 R1 实施验收后连续 R2 的订阅、官方产品内 API/MCP 生成和独立授权发布目标保持。

## 6 固定源追溯

| 普通副本/契约 | SHA256 |
|---|---|
| B13 FinalSourceCopies/app.py：AssetRecord/六内容/quoted SHA header | `c2adbb1d71960675ac0cc2ced5117e6af0b15ac4d453055b5995d1b5f12718bc` |
| B13 FinalSourceCopies/transport_contract.py：原 domain operation/purpose/range grammar | `489967ec2611e8bd1952e003e5da8d37c8b519f41553bb79186e5fcf45040782` |
| B14 FinalSourceCopies/.../application/bundles.py：leaf/manifest/export/import resolver | `824b6d4e7a0813f8254c25986d669a6fa8d09ee1b380880d21a3daa87ba7edd6` |
| B14 FinalSourceCopies/.../domain/contracts.py：旧 Ref/Accepted/Receipt/UsePurpose | `1e71f1cc42c4a1acf7444134ad5b29b08a9ddce6fabebd1a0fe4d1637594d25a` |
| I25 FinalSourceCopies/packages/contracts/NativeRouteManifest.json：原 31 operation 唯一生成事实 | `eafa0b30f5a89d73de23c9d0913620dca8e806b99c063ef8d8311c636caf6146` |
| ADR0019：private token/save/media/source/lifecycle 原边界 | `b35286493eba171bf368f183d069d7ea7dddd867b1d9802000a6d976e79c450c` |

完整绝对路径、task-card/source 文件哈希和本轮工具终态由 Architecture/DeliveryMetadata-A18/A18SourceSnapshot.json 与 A18Handoff.json 固定。
