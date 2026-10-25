# ADR0078：已发布 contracts 的生成 provenance 由正式快照降级为 repository

状态：RECORDED_FACT_AND_RELEASE_GATE，2026-10-25。只记录实测事实、影响分级与发布前条件；不改构建工具、不改 contracts 产物、不改迁移。与 ADR0077 的 dev 宿主无关，故另开一份短 ADR（编号顺延 0077→0078），不回写 ADR0077。

## 1 事实（实测，commit `c3e70ae`，2026-10-25T15:36:17+08:00）

集成用正式生成入口重生成 `packages/contracts/`（commit `c3e70ae10747525780957271760d6a46256be0a5`，`regen: refresh published contracts after media_diagnosis capability`），产物 provenance 从"正式快照"变成"仓库直读"：

| 项 | 重生成前（`c3e70ae^`） | 重生成后（`c3e70ae`） |
| --- | --- | --- |
| `generation.manifest.json` 的 `source_mode` | `formal_ordinary_snapshot` | `repository` |
| 同文件 `source_snapshot` | `{path: G:/…/Codex/VideoCreatorImplementation/Integration/GoalReceiptContractsPreparation/GenerationInputs/SourceSnapshot.json, bytes: 78258, sha256: 3f00303896c7aed7bfdf45771e75304ef967ab51eff49cb23ba5ca0c6d5f68da}` | `null` |
| 同文件 `sources` 项数 | 106（含迁移 `0001`–`0011` 共 11 个） | 68（含迁移 `0001`–`0005` 共 5 个） |
| `export.sources.json` 的 `source_mode` | `formal_ordinary_snapshot` | `repository` |
| 同文件 `snapshot_source_identity` / `audited_read_identity` | 102 / 1145 | 0 / 0 |
| 同文件 `engine_source_reads` | 36 | 59 |
| 同文件 `loaded_native_file_identity` / `native_file_observation_performed` | 0 / false | 61 / true（改从仓库 `.venv` 运行后默认平台观测） |

产物本体差异**只有**一处语义变化：

- `packages/contracts/openapi.json` **未变**，SHA256 `e1f4011cbd16e9524c80696a070cf948f1459978d55530ae2b02dec16cc6e270`（该 commit 的 `--stat` 不含此文件，当前哈希亦相同）。
- `packages/contracts/schemas.json` 的 **168 个 schema 名不变**；逐名为比后仅 `CapabilityRoute` 与 `ExecutionPermit` 变化，二者都是在 `Capability` 枚举末尾追加 `media_diagnosis`（`schemas.json` 第 10118/12760 行附近的枚举）。该枚举由更早的 `823991e`（`git log -S media_diagnosis`）加入 domain，本次重生成只是把它发布出来。
- `packages/api-client/src/schema.d.ts` 的 6 行变化即同一枚举。

**为什么降级**：仓库里没有生成 `SourceSnapshot.json` 的工具，正式快照模式无法从本仓库复现。实测只有消费端：`tools/build/GenerateContracts.mjs:9-26` 接受 `--source-snapshot <绝对路径>`，`tools/build/ExportContracts.py:190-193` 在拿到 snapshot identity 时才写 `formal_ordinary_snapshot`；生产该快照输入的脚本不在仓库内（原快照位于仓库外的 `Codex/…/Integration/GoalReceiptContractsPreparation/GenerationInputs/`）。无参调用走 repository 分支：不启用导出器的隔离/审计参数，因此 `snapshot_source_identity` 与 `audited_read_identity` 都为 0。

**repository 分支还带一处构建工具的过期常量**：`tools/build/GenerateContracts.mjs:60` 的 repository 分支把迁移清单写死为 `0001_ledger`–`0005_alignment_admissions`，而仓库现有 `0006`–`0011`。因此新 manifest 的 `sources` 少了 6 个真实存在的迁移文件——这是**清单不完整**，不是 schema 变化。

## 2 影响

- **属证据降级，不影响运行时行为**：`openapi.json` 未变、168 个 schema 名未变、枚举追加是已发布的真实 domain 变化；API/SDK 的 HTTP 面与 schema 名集合都不受影响。
- **可审计性被削弱**：`generation.manifest.json` 不再绑定"生成输入快照"，`export.sources.json` 不再有 snapshot identity 与 audited read identity 列表；再加上 repository 分支写死的迁移清单，读者**无法仅凭已发布产物重建本次生成的完整输入集**（至少缺 `0006`–`0011` 六个迁移）。
- 该削弱只影响"生成输入 provenance"这一环，不改变"`current_backend_source_bound: true`"和导出器自身读取到的 engine 源哈希；后者仍在 `sources`/`engine_source_reads` 中可见。

## 3 判断：P2（发布前必须解决，不阻断本地开发与运行）

定级 P2 而非可接受，理由：发布包必须能自证"契约由哪一套输入生成"。当前状态可以支撑继续开发、测试与本地验证，但**不能支撑 Preview/生产晋升的发布证据**——发布时若被问"这批契约绑定的是哪份生成输入"，已发布产物答不出来，且清单本身已知不完整。它不阻断运行时，也不构成安全/授权缺口，所以不是 P1。

发布前必须完成下列之一（缺一不可）：

1. **首选**：补上生成 `SourceSnapshot.json` 的工具（或把仓库外的 `GenerationInputs` 快照制作过程纳入仓库可复现脚本），用 `--source-snapshot` 重生成，使 `source_mode` 回到 `formal_ordinary_snapshot` 且 `source_snapshot` 非 null。
2. **次选**：由用户明确书面接受 repository provenance，**且**先修 `tools/build/GenerateContracts.mjs:60` 的写死迁移清单（纳入 `0006`–`0011`）并重生成，使 manifest 源清单至少完整。只做接受、不修清单，不算解决——那等于接受一份已知不完整的闭包。

在 1 或 2 完成前：

- 任何评审、验收、交接不得把 `generation.manifest.json` 当作"生成输入已正式快照绑定"的证据；引用时必须写明 `source_mode: repository`、`source_snapshot: null`。
- 不得用"`openapi.json` 哈希未变"替代 provenance 结论：那是产物身份，不是输入身份。
- 不得为了凑快照而手写/复制 `SourceSnapshot.json` 或伪造其 `bytes`/`sha256`；缺工具就保留缺件。

## 4 边界与后续

- 本 ADR 只做记录与门禁，不改 `tools/build/*`、`packages/contracts/*`、`packages/api-client/*` 或迁移（分属集成/后端白名单）。修 `GenerateContracts.mjs:60` 与补快照工具由集成执行，重生成后另交精确提交与证据。
- 恢复正式快照后，本 ADR 追加"已恢复"实测（新 commit、新 `source_mode`/`source_snapshot`、`openapi.json` 与新 `schemas.json` 哈希、168 名不变）即可关闭，不必新开 ADR。
- 证据来源：`git show c3e70ae^`/`c3e70ae` 的 `packages/contracts/generation.manifest.json`、`packages/contracts/export.sources.json`、`schemas.json` 逐名比；`sha256sum packages/contracts/openapi.json`；`tools/build/GenerateContracts.mjs:9-26,60`；`tools/build/ExportContracts.py:190-193`。未运行任何生成入口，未改任何产物。
