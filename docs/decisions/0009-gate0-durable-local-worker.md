# ADR 0009：Gate0本地持久Worker与审核实验准入

2026-10-08；批准以下最小实验接口方向及版本，不声称实现/技术冻结。永久架构不实施、测试、操作产品进程、读key或收费，不读取/修改I9宿主WIP。范围为G0-REVIEW/G0-LEDGER危险前提及后台持有局部实验，不扩通用调度平台或R2。

## 已有事实和缺口

EngineService已有acquire_run/heartbeat/recover、fence/attempt、Step固定输入及结果、Operation先prepare/claim再副作用、版本化review/decision去重。waiting_user清worker_id/lease；反馈创建同Production新Run，预算/修订计数共享。Assets先fsync/replace文件再事务入库，但生成产物未绑定lease/fence。API health目前只返回create_app的worker_connected配置布尔；生产无独立Worker或执行终态入口。CreativeCrew先读域revision再补Step；FlowFeedbackProbe是synthetic CrewFlow pending实验，crash_child的“Step后未Flow”窗口尚无真实checkpoint。因此不能把旧机制绿/API关闭绿视为真实持久后台执行。

## 本轮固定范围

内部实验workflow版本 `gate0-local-render-v1`，只能由可信CLI/配置选择，不让模型/HTTP给模块、回调、路径或shell。输入复用当前ProductionRequest、固定request_revision和本人已有合法Asset；已有目标/脚本/三镜头资料及有限本地模板可作标明来源的实验夹具，不能标模型自主创作。总费用0、owned_local路线、无vault/key/外传/供应商调用。至少以实际FFmpeg产生有声媒体，并按真实decoder入库；不是写个假MP4或只计事件。

先测持久Step产物和quality审核等待、跨进程反馈与恢复。当前没有完整固定Bundle提交端口，**本实验不新增或伪造Production succeeded**；已产生的video/audio Asset和Step可成功，Run在真实waiting_user等既有状态保持。完整请求全部输出/Bundle/导出引用完成后才能另准业务终态；实验完成不等于G0-REVIEW全部创作/unattended质量或R1通过，不改变原标准。

## 最小受控接口与唯一owner

后端维护唯一Pydantic/domain与application/CLI/infrastructure及必要迁移；以下内部契约标识v1候选，Agent/媒体只消费，不复制Schema或直接写账本SQL：

| 接缝 | 最小语义 |
| --- | --- |
| ExecutionBinding | run/production/request_revision、workflow_version、固定输入Asset ID/hash及资源manifest hash；执行前持久固定，同Run不同绑定409；无任意绝对路径/秘密 |
| WorkerInvocation | 可信 `worker --data-dir <本实例> --workflow gate0-local-render-v1`；可限定run/最大运行窗口，固定profile白名单；独立OS进程，单执行槽，不能默默随serve启paid Worker |
| Worker存在事实 | 本实例worker_id/profile和持久heartbeat；建议5秒心跳/15秒过期，run租约30秒并5秒续；失败粘性，idle或waiting_user仍可证明进程活但不占Run执行槽。API默认false保持，增加内部动态读取接缝；禁止静态设true当后台就绪 |
| Run/审核读取与释放 | 复用acquire/begin/read/complete/wait/submit_decision；补受控读取固定revision已接受decision及必要安全释放租约端口。approve后不重复同一审核；旧版本409/重复键同输入复用、异输入冲突；原话/约束和最多2轮不变 |
| commit_generated_step | 当前lease+step_key/input_hash、已验证受控暂存候选、固定result；昂贵渲染/解码/文件提交在短事务外，最终Asset元数据关联和Step事务内再次校验fence/input/owner。stale lease不能链接结果或改Step/Operation；仅检查一次后延迟提交不合格 |
| Workflow checkpoint | Agent/媒体持有本候选真实CrewFlow状态及版本，限定DataDir/WorkflowState；恢复先读业务Step/Operation/revision/decision事实，再补Flow推进。backend绑定不等于Flow完成；不建多框架通用层、不直接读LG旧checkpoint |

无需新增HTTP受理/审核路由，沿用现API及ErrorEnvelope/固定状态；health仍同一InstanceHealth形状，bool必须来自新鲜持有事实/资源就绪而非配置意图。内部新增模型/接口由后端给精确源hash，若公开Schema实际变化须回交架构和集成生成，不手写SDK。建议值是本有限实验边界，owner若有具体约束须先交偏差，不能静默放大。

commit_generated_step沿用原complete_step的“关联Operation均成功且已结清”守卫。本地driver在Asset登记前只把已验证文件manifest/hash写入Operation.result_json，不填不存在的result_asset_ids；之后由持有效lease的后端事务登记Asset并提交Step。unknown先按原Operation核实，不因新增端口旁路settlement。若实现确需合并Observation与Asset事务，后端先交精确细化，不由媒体直接写SQL。

Agent/媒体唯一实现workflows/media内本地三镜头有限计划/实际渲染与Flow恢复，调用后端端口，使用现FFmpegRuntime/受控参数，不让模型给filters/argv。执行中后端持租约续期；失去fence只中止本attempt可取消的本地渲染、不取消Production，不提交过期结果。等待审核返回挂起结果并释放lease/执行槽，不阻塞线程等人；同worker应能领取第二个独立任务。interactive/unattended共用本地Step，unattended按持久固定策略校验继续而非手填中间产物，但只是免费确定性机制实验，不能标真实模型无人创作通过。

## 文件、未知受理和恢复

输入Asset/资源哈希、attempt输出临时文件归属及Operation dedupe键先固定；输出仅本实例受控暂存，文件完成/校验后才能提交。文件落盘未DB时，新lease只能依据持久归属/输入hash及真实解码认领，不能扫描任意目录或将.partial当成功；旧lease落盘文件不获得提交权。DB/Step成功未Flow时复用相同Asset/结果hash补推进，不重新render/生成。损坏/缺失对象维持明确错误，无伪decoded/静默覆盖。

submitting但external_id未落库仍unknown/needs_reconciliation；即便本次免费，也不将通用恢复改成盲重交。真实免费loopback测试上游可持久保存同键受理/结果再断线，区分实际HTTP受理与合成业务；不代表付费供应商幂等/账单已证。已有OperationExecutor未知观察/预留与原Run对账保持；本地已完成渲染只能在核固定输入/归属/输出证据后按原Operation核实，不能凭费用0清unknown。没有证据就等待核实。

## 真后台持有与实验入口

集成在自身实验目录准备可信父监督器和独立DataDir/资源manifest，只spawn既有API与新Worker两个分别持有的进程；API/UI客户端断开或明确关闭API不收回Worker。后台ack必须先有真实worker创建身份、同instance/version/资源核验、可读新鲜heartbeat，再允许实验展示“由监督器继续”；只记录PID/打印ready不足。监督器继续活着是本实验信任前提，不能外推父硬崩溃、Tauri托盘/JobObject或生产服务安装。不得改I9宿主、重启旧实例或无范围kill。

Worker有界运行窗口和单槽、不引入Redis/队列平台；停领新Run后有限收尾当前可取消本地attempt并释放自己的资源，保留未知Operation/原账本，下次按lease恢复。父/客户端退出不是Production取消。观察Run lease、Worker heartbeat、真实渲染子进程及最终文件，分别记事实；API marker和host清理不等于Worker或费用完成。

## 下游实验与完成界限

后端先交内部端口/绑定/动态health/生成提交精确源→Agent媒体本候选Flow和实际render→集成真实独立父/API/Worker实验→测试开发独立固定批→RV/AV分别评审验收。测试只由测试角色写：同键双提交/双Worker并发与旧fence、审核释放槽再执行第二任务、跨进程旧/重复/异键反馈和第3镜头局部修订/未影响Asset哈希、HTTP断开及API关闭后Worker继续、worker失联health过期、真实kill四窗口（提交前/受理ID未存/文件未DB/Step未Flow）、真实checkpoint恢复不重做、合法与坏媒体/资源缺失、未知不重交。注入业务可模拟，文件/事务/OS进程/FFmpeg和Flow窗口必须真实，分层记录，不降低既有标准。

新源和迁移只用于隔离实验实例，保留原版本/失败。需迁移时后端新增明确版本及兼容检查、集成做可信备份；旧代码不能直接打开较新schema，不能称删新表即可回滚。未得固定源/完整证据不释放测试冻结或签整体Gate。ADR0003付费三轮已尽不重开；R2、模型自主协作、公平唯一框架裁决、完整Bundle/三OS和商业仍按原缺口推进。架构交接完FINAL，不等待实现。

执行排程：后端B6可立即只读准备；T11相关生产读取批真实终态并由统筹解除冻结前，不修改其API/domain/application等依赖源。架构接口批准不解除正在进行的独立源冻结；之后每批绑定新源hash。
