# RV27 — I27 固定契约生成切片独立审查

结论：**PASS_LIMITED_CONTRACT_GENERATION_SLICE**。本轮未发现阻断该固定生成切片的问题。仅支持 B18 固定普通源经唯一 Backend CLI 导出、OpenAPI 派生 SDK/native 声明和实际 SDK strict/noEmit 编译；不批准 RuntimeBinding、HTTP/权限/媒体/原生运行、完整依赖资格、Gate 或 R1/R2。ASR corrected proposal 不在本轮范围，仍不具执行准入。

## 固定身份与审查范围

- 任务卡 `docs/task-board/RV27.md`：`2bad448a0a15ca4e49fa31362f891f612c1ba294b7fc368fd76f5c086af9f486`；仓库规则：`6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`。
- I27GeneratedFreeze：`883abfb7c432d09fe529b3a48a71b4102d2d338b45cc071b488adf5838a341d9`；Handoff MD：`f07e414cfdbc8722b6672fca1b2308be15ab1eab816ee64983c894857ce4672b`；JSON：`8befe9990199bb2f614aad7cf58a02ef249439c54d536193f7acaa2dbab94498`。
- B18SourceSnapshot：`ebd4e141107345275ddd4dd10cd322254a6062aba6b78efc95afa59263e2c858`。逐一核 37 B18 普通源、21 I27 普通源/输出/过程副本、正式收据/踪迹、11 旧工具与输出保留项，以及 trace 绑定的两份 TypeScript 工具源码。共 93 pins，SHA/大小匹配，审查前后变化 0。未读 B17/W15/I28 活源。
- 所有源码、八输出和证据的完整路径/SHA 在自有 `RV27InputPins.json`；完整 Freeze/交接、必要已审正文及三轮收据固定在 `RV27Snapshot.json`。本轮只读解析与比较，没有运行生成工具、产品或测试。

## 可支持的生成链

普通副本根为 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/IndexedEngine-I27/FinalSourceCopies/Repository/`。`tools/build/GenerateContracts.mjs:23–26,29–46` 先执行唯一 `ExportContracts.py` 包装器，再由 openapi-typescript 生成类型，从实际 `api.paths` 生成 route 表和 native 声明。未另建 Pydantic、URL、授权 scope 表。

`ExportContracts.py:37–73,104–131,195–201` 从 B18 正式清单核普通文件、限定精确 engine 模块/namespace，拒未知 engine 与 Media/providers/workflows，再执行 `video_creator.cli.main export-contracts`。固定 B18 `cli/main.py:71–87,138–139` 只构造静态 ExportEngine/FastAPI schema，不构造运行数据库或凭证实例。生成记录的实际 CLI schema count 是 129。

独立解析全部 37 操作：method/path/operation ID、parameters、header_rules、request_body、responses、security 和完整 `x-engine-transport` 与 native manifest 一致；SDK routes 的请求/响应 media 及全部 operation ID 与同一 OpenAPI 一致，native TS 全部 operation 对象一致，77 个 component 语义一致。八输出固定身份均匹配；contract set `0.3.0-candidate` 与 API info `0.1.0` 保持分开。

OpenAPI SHA `1606ba21d00d75e3e8fe669806cab0fec9b4aeabf14d8883b92a2fa9f27ba8cd`，schemas SHA `1604f3d8f1a4dba13a1f72985e41d1c323b97dca8d841fe913e52e2c4a08565a` 均与 B18 原公开导出一致。native manifest SHA `4d61f00a42b2a7f3a2500374d572d21acc07791cded2f2d9dd2d246a4376e8f5` 与 native TS 常量一致，manifest 内 OpenAPI SHA 正确。生成清单准确保留 `native_runtime_ready=false`。

六组 asset、bundle manifest、bundle artifact、export archive、import manifest、import artifact 的 content→metadata GET 关系完整保留：相同 security 与 authorization、封闭同名 path/query bindings、同一 DeliveryContentMetadata、原 purpose 规则、完整 200 与 206 total 的区别。授权有效期是 required nullable，null 不能变成未知授权成功；声明仍是事实快照，不能代替本轮未运行的实际授权/撤销/提交时校验。

固定 `client.ts:1–24,91–156` 通过生成 RouteKey/operations 与 operation ID 走 generic transport；`native.ts:136–143,196–219` 绑定当前 manifest hash/版本，拒未知 operation，使用私有 host invoke。`client.ts:169–170` 与 `native.ts:315–324` 保留原始响应和仅完整 200 可 save 的边界。这里仅是源码覆盖与声明一致，不是新 native host 运行证明。

## 三批真实记录与失败保留

| 范围 | 原始结果 | 支持范围 |
|---|---|---|
| preparation fcd631 | 自然 1；错误 root TypeScript 路径 | 生成未执行；原收据和脚本保留 |
| 第一批 95c065 / generator PID48292 | 自然 1；Windows `--import` 文件路径被当 `g:` URL | CLI 未执行；原 stdout/stderr/receipt 保留 |
| 第二批 88470c / generator PID50252 | 自然 1；CLI 已导出129/0，finish audit 拒本次 venv interpreter 文件 | 未执行后续 native/TS；原部分输出与错误保留 |
| 第三批 b4022e → 0d8611 / session28449 | generator PID44016 自然0，TypeScript Node PID42104 自然0；无 timeout/force | 唯一固定源生成与 SDK strict/noEmit 编译 |

第三批 CommandReceipt SHA `f41320c590d61613b7800609cacac8d64713025ce9833fdb5a3a0db31058fb1c`。第三实际 stdout 有 CLI129 和 openapi-typescript7.13.0 完成；generator stderr、TypeScript stdout/stderr 均为空。实参为 `--noEmit --strict --allowImportingTsExtensions --target es2022 --module esnext --moduleResolution bundler --lib es2022,dom,dom.iterable packages/api-client/src/index.ts`，没有 skipLibCheck/降断言或产品测试 skip。开始 2026-10-09T01:52:40.906885+08:00，结束 01:52:53.492263+08:00；总记录墙钟 12.585378s。原计划 59 输入与实际 source_after 及 Freeze59 逐值相同，变化 0。

## 明确限制与后续归属

实际 TypeScript 是 7.0.2 Node 代理：trace 绑定 `tsc.js` SHA `cbdfbf11c26ed00dfc073155e316a42d6d6d8a387be61006b82fa9aa93ac572e` 同步 `execFileSync` 原生编译器，捕获非零后设置退出码，故 Node 自然0可支持本次命令编译成功。三模块 Node trace 不记录其原生 tsc.exe 的本次 PID/正文 SHA，不能声称完整执行闭包身份已冻结；这属于限定证据边界，未阻断当前生成切片，也未批准工具分发资格。

导出 trace 的26 engine import/37支持身份、1076 Python open、462环境文件、60加载 native 文件、163 distribution 版本已核计数/来源模式，拒绝数0、源变化0。Python audit 不是任意C/syscall执行前封锁，DLL清单是加载后观察；Node hook 只观察模块 source。`-I -S -B -X utf8` 与固定 dependency root 不等于便携 namespace/DLL资格，ExportSourceGuard 不是 ADR0023 loader。

当前 native manifest 37 条尚未经 Rust/native/HTTP 独立运行；I24旧31 route二进制不继承。媒体/合法published Bundle/grant/V closure、三OS、完整App、ASR原context validator与dispatch、完整Permit/Gate皆待其正式固定切片及独立 Test/Acceptance；Integration 负责后续资源与native接缝，Test/Acceptance负责真实运行与资格证据。本轮没有为其它 OPEN finding 代签关闭。

自身最初 JSON词法比较的 PowerShell 单元素数组展开/空字段null和0.0→0差异已纠正为数组与数值语义比较，原自身过程保留为 `RV27InitialLexicalComparison.json`；未当产品红。全部固定输入读取与工具已终态，reader释放；费用0、key0、网络0、产品/测试运行0、实现/标准修改0。全目标仍完整R1独立验收后连续R2。
