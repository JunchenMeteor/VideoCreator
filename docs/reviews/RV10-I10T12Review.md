# RV10 — I10 / T12 晚到异常来源有限复审

阶段 FINAL。永久独立评审只读最终普通副本、正式交接和必要原红；未执行或重跑测试，未读B6/W6 WIP，未改实现/标准。仅在下述固定源码及源绑定VM机制范围关闭RV9-P01与RV7-P01的对应缺口，不宣称真实Windows信号、产品host exit或新后端整入口通过。

## 输入身份

T12Handoff.json SHA `5a9a2e6ecac60b85da1ba08dd2e5f1bd078344f1ea718dd7939d5d250daff71b`；MD SHA `a4ccadd059a5ad61281dabbd93f7fc867c09f5e9cae6fce1e47dbeb5e479ac43`；24副本manifest SHA `675da1a824ce3d1f14f80fd0703c76b9ff5e853e316fdd977d5fe9c875337adf`。三者实读与统筹正式SHA一致。

24份普通副本逐份hash均与copy_sha256及声明的original_sha256一致。固定源码读T12Evidence021—024的真实副本，没有用当前工作树替换被测身份：

| 固定源 | SHA256 |
| --- | --- |
| tools/build/DevRuntime.mjs | 7971e2c4d209e6a52d602e469d5180306cfcfb642a838c1a172d547bba957e0c |
| packaging/RuntimeContract.md | c956421f2097a26d6742474df5c4339672820c425b821987b2c82792d4a70ff6 |
| tools/build/EngineProcess.mjs | 3b6716f93e05122a718e41d4bfbbcf330d706be3b4412f271816729c08eed076 |
| apps/workbench/vite.config.ts | c5cf940ca7aba73896e70ae37a4fd0177fd1d1d0e16370e972c35047d8ff6932 |

I10SourceFreeze实读SHA `e02a9b206eb35e64e2021c0e6d001fa55a02d3034dfd3382fe08f3846179c6f6`，与T12实际before/after一致；I10Handoff SHA `3fb8720b9648ae100095312a77514182628b1de36d128e12782c1746cc06e8ea`。冻结仅四宿主源，不含并发后端业务，不是整个产品冻结。I10 owner两场景11检查不替独立T12。

## 原子结果与运行身份

T12MechanismRoundOne的JUnit实际9 case、0failure/error/skip；正式记录Node与UTF8包装均exit0，总耗时0.5039524s，无continuing session。CommandReceipt实际Node退出0，argv/时间与正式交接一致，stdout/stderr SHA与普通副本匹配；8个显式源及all_source before/after和范围外变化均0，完整map与handoff一致。

- CommandReceipt SHA：`60a38fab837945987bb190f6d1f00f1653c087f5ec620615456778b042e7ddde`。
- JUnit SHA：`5bdcb1dead545028add157f6f4ac6c5e6acf7b96753687fe1ba4eb7587336fc0`。
- Stdout SHA：`5fc83e81a1ec0455cd119b2b906565456dc2c80e8f88eed9ea925ebd19c3c441`。

实际命令为`C:/Program Files/nodejs/node.exe --test --test-concurrency=1`加spec/JUnit两个reporter，执行`tests/gate0/t12_stop_source_mechanism.test.mjs`。完整argv、开始08:59:36.771144+08:00/结束08:59:37.391212+08:00、source maps保存在RV10Handoff.json。包装exit来源为T12正式终态记录，Node exit来自原子CommandReceipt，两层不混为一种证据。

RuntimeInputsBefore/After单列**实际process.execPath** `C:\Program Files\nodejs\node.exe`，二进制前后SHA均 `9a4eb5f1c29c6a2e93852ead46b999e284a6a5ca8bab4d4e241d587d025a52de`；SourceFreeze前后均e02a…c6f6。T12测试before/after读取实际Node二进制并断言一致，未拿shell解析的版本号代替身份。该新增身份只支持本批，不能倒填原T11未独立freeze的Node工具链。

## RV9-P01 / RV7-P01 — P2，源码与VM机制局部关闭

原c45路径在入口锁lifecycleFailed后直接复用stopping；cleanup Promise已settled时，原closure不再执行exitCode设置，晚到SIGTERM回调仍可留下字段0。I10固定Dev与RV9保存的c45全文逐字比较，唯一新增生产行在当前DevRuntime:47：

```js
if (lifecycleFailed) process.exitCode = 1;
```

它位于来源异常更新之后、`if (stopping) return stopping`之前。因此每次异常来源回调到达都立即锁非零，不依赖旧cleanup closure重跑。来源策略、可信control成功条件与原samePromise保持；并未重发停止帧或重复调用API/Vite清理。

独立T12晚到SIGTERM收据T12Evidence007（SHA `d8f032bd36ed8c747e168a3a401e42558c23c2db581ec00f950e45ca2e910939`）绑定真实源码块[2272,5363)、块SHA `853537d0bf9aa528b56b82ab7d7c8c82f74f7c86c21b861dc9cbc3aa7c2abc84`：control→settle时字段0，后SIGTERM字段1，lifecycleFailed=true、samePromise=true、API/Vite各一次调用。新增settled后SIGINT亦字段1。合法control-only对照字段0、无lifecycleFailed、synthetic controlled，并各一次清理。

首次SIGINT/SIGTERM、合法帧/异常两种先后、pending阶段child failure及late阶段共8个异常机制加1个合法对照均通过。由此可关闭RV9-P01及其延续的RV7-P01在**已列源码分支/VM字段机制**上的缺口，无新增该层阻断发现。原reader静态局部关闭保持；未把旧I9/T11真实入口结果归入新I10完整入口。

late收据中先前已发controlled清理日志原样保留，随后exitCode字段变1；它证明先前日志不能代替最终真实宿主退出。该模拟字段变化并不证明新源宿主实际close1，也不能把control-only字段0当真实产品正常退出。

## 原红及断言未降低

原T11测试仍SHA `a9d4b140503256ba403fbd6cf6c0e85ea50b0a68049b95a7f275507b25b03422`，保留c45硬pin。原红Stdout仍 `aa1c5a46131855b430266246a7526a6c07eec2f0a0e5cbea0bc2990301a80812`，XML仍 `d2f8712e7340f47e2450e05ff0fbf831dd9d70e3262229c688b7a652f7732424`；原0≠expected1/Node1不改成旧源通过。

新T12是新命名文件，SHA `31789729ef8241b5f4e4427612f49c6e43378aeb0b8c906c5d1ab3f51ba89b6e`，严格pin7971。旧新五项核心断言逐字保留：单API调用、单Vite调用、samePromise、lifecycleFailed=true、异常exitCode字段必须1。只替换被测新身份、补运行身份记录和新增late SIGINT/合法对照，不扩大期望取得绿；旧七种scenario包含于新范围。

测试实际运行固定源码stop声明和注册signal callbacks的VM块，使用真实cleanupRuntimeChildren与synthetic资源/process/日志；**OS signal发送0，实际产品进程0**。测试名“BeforeHostExit”描述模拟时序条件，不能拿这个名字宣称真实Windows生命周期复现或端口/后代清理。

## 未测与交接边界

真实Windows OS SIGINT/SIGTERM触发/handler可达及late时序、真实Node host close与OS资源、完整合法/预缓冲/defaultoff/EOF/file接缝需B6稳定后以精确整合身份另测；本批未消费B6/W6 WIP。新backend/SDK结果不在8scope内，不能拼成混合版本整产品绿。

原T11/I9/I7/旧候选的失败、工具链或缺失日志不倒填。本轮不重审100副本、旧18/83或媒体，不签TTY/native/Worker/JobObject/新包/三OS、作品视听/自主编排/Bundle-RAG、商业/支付/发布与Gate0→R1独立验收→连续R2通过。局部P2机制关闭不降低这些实际验收门槛。

报告 `docs/reviews/RV10-I10T12Review.md`；过程/身份/断言核对 `G:/开发测试/Codex/VideoCreatorImplementation/Review/RV10Handoff.json`。全部读取实际终态，之后不再读取当前宿主源；可交下游整合并释放本评审槽。测试运行/费用/key/产品进程操作/源、测试、标准改动/构建部署均0，只写评审白名单。安全require_escalated读取，无F解锁或ACL变化。
