# Goal Receipt 契约生成准备独立评审

结论：固定版本在 SOURCE/DATA 准备范围内未发现新的阻断问题。此结论不授予生成执行权限，也不证明导出、类型检查、安装、Owner、HTTP/MCP、native 或完整 R1/R2 通过。实际生成须另经统筹准入，由原 Integration 保持唯一执行与进程归属。

## 固定输入与独立核查

任务卡 `GoalReceiptGenerationPreparationReview.md` SHA `a4a0bc577c394c57ce28c2279880fbfc338d4bdd1ad041f1e511b6148cf9159f`。正式根为 `G:/开发测试/Codex/VideoCreatorImplementation/Integration/GoalReceiptContractsPreparation/FormalStageRevisionTwo/`；该根实际冻结文件名是 `Freeze.json`。

| 文件 | SHA-256 |
| --- | --- |
| Handoff.md | 3fd8d878aad9a219faba9a71ce5def3fbf8a92cb9064cd08111e4fe9eea2523c |
| Handoff.json | ea092251aefedd3401b2ffc1a6ec88bdb12bdc469b19ae5d2772482cea5df0a5 |
| Freeze.json | 0add15ae8a31bfa7da9206f82ea65e3135f5f029532425d5cc7d01527390bdc2 |
| OrdinaryIndex.json | 7514cc03042f5c963d44efc32a3abd0f9990c9cfc8c1c9a521986c6773e9b681 |
| GenerationPlan.json（正式根的上级） | 5cb0a804a931d0a8c9f8a4c3b9c4b71bbc8e87ff6fa08e00497910c62e39bb5c |
| RunGoalReceiptGenerationRoundOne.ps1（上级） | 3d297a7b8ac08f3539ff569577f56c8c8df1092dc3eb55803b76d3a2f1c64e03 |

独立重算索引 146 普通件大小与 SHA，无差异。生成快照 `GenerationInputs/SourceSnapshot.json` 的 source_map 为 102，逐 relative path/size/SHA 对应原 Backend 固定索引 `0bbbd04a5014b0b512ed64d077b9058d80abfb24bb7178a68541ef7936adbd5e`，无新增、缺失或身份差异。Node hook 的两条子进程 executable/argv 与 Plan 逐值相等；367 模块及 30 resolution package metadata 均在 Plan 输入中，大小/SHA 一致。另有限重算 Node、Python 基础程序、venv launcher、pyvenv.cfg、TS 原生 executable 共五件，与 Plan 一致。

本轮没有重新扫描或重算全 6909 环境输入、1270 pyc、192 物理目录的全部成员；这些是原准备记录和未来 runner 的检查范围，不冒充本轮实际 import 覆盖。最终有限输入数量和前后结果以自有 `InputSnapshot.json` / `InputAfter.json` 为准。

## 入口与源码链

唯一拟入口是 PowerShell 7 `-NoProfile -NonInteractive -File <准备根>/RunGoalReceiptGenerationRoundOne.ps1 -PlanSha256 5cb0a804...`。runner 9–15 在创建输出前核 Plan SHA、固定 scope、全部 candidate pins、八个原输出身份、exclusive 新输出不存在及输出父链非 reparse；只允许八个已声明 Integration 输出与独占 GenerationRoundOne。它不回滚或覆盖原失败批。

runner 24–25 创建明确 executable、cwd、ArgumentList，并清空继承环境后只设 Plan 九项变量。Generate 使用 Node 导入固定 TraceGoalReceiptImports，再执行既有 GenerateContracts 的 `--source-snapshot` 和 `--skip-native-file-observation` 分支；子 Python 为 `-I -S -B -X utf8 ExportContracts.py ... --source-snapshot ... --dependency-root ... --skip-native-file-observation`。下一子 Node 使用固定 GenerateOpenApiTypes 对显式 OpenAPI 对象转换，代码 9–15 拒绝非 `#/` 的外部引用；不走 CLI 配置查找。随后才调用固定 TS 7.0.2 原生 tsc.exe 严格 noEmit，且 typeRoots 为新批 EmptyTypeRoots。这里未执行任何命令。

固定 ExportContracts.py SHA `bafe8b5b926d4cf1ceaa522eb7295c438ed0d403a46763c0f76bfb9115d92ac4`：39–65 约束隔离参数、固定依赖根、快照路径与原件身份；106–140 的 SourceLoader 从冻结普通正文 compile，拒绝未知 engine 模块，不退回热源码；117–122 明确拒绝 media/providers/workflows。80–103 审计普通 Python open 与 common socket/spawn 调用；142–196 生成实际读取、loaded dependency identities、102 source after、changed/denied 和 native-observation 状态。

固定 CLI main.py SHA `482d87de04e9fe54fa2b4ced7a65110116a3964eb8007fbae2f8de3983bb9e39`，81–114/177–178 是唯一 schema export。ExportEngine 提供内存 instance_id/db.data_dir；这条分支没有调用 EngineService、真实 Database、Owner 或 lifespan。实际 create_app 会构造 BundleService/AssetService 等内存 schema 对象，不能描述为完全“不构造任何 service”。已读构造链：app.py 82–92/105–113，bundles.py 249–271，assets.py 20–22，bundle_authorization.py 109–111；这些直接构造只保存配置、内存集合/锁和未启动的 thread 槽，没有打开 DB、解码、收费或启动 Worker。源码判断不代替运行观察。

固定 TraceGoalReceiptImports.mjs SHA `305d27b2118990e4e15a5afcc07211f8ccdc2e7199883e410f48b0111c31f116`，20–29 只允许两条同步 child 及参数；34–47 对 admitted file module 读取前后 hash/size 验证，记录 loader source。原 GenerateContracts.mjs 24–45 保持 closed childEnv、shell:false、继承双字节通道和子 status 非零拒绝；snapshot 分支只有固定 Python 和对象 types 生成器。NativeContracts 5–50 根据唯一 OpenAPI/transport 声明派生 manifest/TS、验证版本/operation count/authorization declarations，写候选数据而不授管理或安装权限。

## 失败、进程与结果边界

runner 33–61 在成功 Start 后始终保留同一个 Process，记录 PID/creation、并行复制原 BaseStream；owner 捕获错误后仍尝试取得双流，等待原 process 自然终态，再等待两流真实 EOF。ExitCode、owner 错误、超时粘性或缺流都会阻止后续 command。未见 kill、重启、重交、失败后第二次启动同一业务。尚没有本轮实际 child/EOF 的运行证据。

900s/180s 是失败粘性观察窗口，不是硬终止窗口：43–44/51 在超时后继续等原 Process/EOF。如果进程或 stream 永不结束，runner 会继续等待。这个明确边界继续 OPEN；本报告不把它说成有界自然终止，亦不新增 kill 授权。

runner 63–90 检查 Python actual trace 的 source_mode/102、source drift、denied imports、native observation=false、actual observed read 的 pin，以及唯一 Goal schema/POST operation、ReceiptQuery 四必填项、Association 四分支与 NativeManifest OpenAPI SHA。97–115 最后再核 candidate input bytes/SHA 和 physical directory membership；漂移、读取失败或目录成员变化锁存 overall 1，保存部分八输出。NodeImports 原件被 pin 保留；这不等于它的全部内部事件已由 runner 作独立 OS 验收。

实际执行后仍须独立读取原 receipt、export.sources、Node trace、原 raw、实际生成 DTO/SDK 与两 child 终态，再决定其真实支持范围。未来 trace 不是本轮已观察事实。common API/loader audit、固定文件 hash 和 ordinary source 不提供 syscall sandbox、Windows Job、全后代或全 DLL 加载证明；跳过 native file observation 也不能当 native qualification。原 schema 表达和代码生成不授实际 Goal 接受/未知恢复、SQL/WAL 并发、HTTP/MCP、Owner、权限/预算、媒体/ASR 或三 OS 资格。

## 历史、自己的错误和交接

原 I44/I62 overall 1 保留。原 metadata assembly `5e44fc1` 和 finalizer `5f5a4e/1` 失败不可替换为新成功；FinalizationFailureReceipt SHA `84f13370d793f38f5c98fa646a068c16b018bc6b641850f224415bcb9e723ebe` 明确原 comma-plus 数组拼接错误、部分 outputs 保留、新 namespace 修正，Plan 未改且 export 未执行。PreparationReceipt 自然 0 只支持 PowerShell data preparation。Formal freeze 对 actual finalizer return 明确依赖 owner 后续工具终态，不用文件存在证明原进程结束。

本角色 `21c524/1` 猜 SourceFreeze.json 路径失败，随后按实际 Freeze.json 定位；OwnLocatorError.json 保留，非产品红。`4190cb` 和 `2bfa42` 输出截断保存于 OwnOutputLimits.json；必要完整内容由定向读取/已落普通清单补足，不声明截断输出已全文消费。`892150` 初始派生统计错误使用不存在 list key 把 source_count 写为 0，SourcePreparationFactsInitial.json 保原记录；`07d2ed` 按实际 source_map 独立逐项修正为 102，无输入变化，非真实缺源或测试失败。

未发现本轮新增的 P1/P2 阻断 finding。只支持上述精确冻结 preparation 的源码/数据一致性；原运行失败、未测事项和 R1→R2 总目标不变。审查不代审批或原 Integration 执行。自身报告/过程为唯一写入范围；末次工具自然终态与读者释放由正式 FinalHandoff/FinalizerTerminal 单独记录。
