# ADR 0011：原副作用唯一与完整恢复的分阶段证据

2026-10-08；批准版本化判据方向，测试角色成文并经RV13独立批准固定版本后才运行。架构不写标准/测试/生产，不执行产品或测试，不读B7 WIP，不锁实现写入，费用key0。本裁定不关闭RV11-P01或签Gate0。

## 固定来源与变更性质

T14AssertionConflict.md SHA `4d1e9a17a0d88bd8bb02630e7d8e013a408cd48edbc19cf15bf13923a1229764`、JSON SHA `e06326d920c25bf66ffeec3dbb616daac0ff60a915af5decdaa235f7e3ca01e0`实际匹配。原完整test副本 SHA `03966d95f336c6f14cff14ac7653aaaba26317a9f9eb1963d371cb7c40bf2a52`、W6历史消费副本 SHA `173c9a474821e87cb1ac19d8717b48a9b71a0417e3fa1e24983b37940be25581`均实读；RV12报告SHA `977068677151216997103a649c6527f8da13816fcab00129983f8a71fdab2672`固定只读。未用B7/W7未来实现倒推期待。

原第47行要求最终全Run operations=1/generated_attempts=1，48行又要求同Run完整quality waiting_user。中断在shot1成功文件尚未观察；原固定流程还有shot2、shot3及compose，各自正常不同step/input/dedupe。因此最终全表仍1与完整quality同时成立不可满足。不能停做后续镜头来迎合1，也不能只扩大计数而失去原副作用唯一保护。

**这确实改变旧字面最终计数所处阶段，是版本化验收用例变更；不是无影响文本修正，也不是原字面所有断言原样通过。** 产品G0-LEDGER的幂等/旧fence/unknown不盲重交和G0-REVIEW等待目标不降低。原测试及T13原产品红、三次夹具/观察红、补观察绿全部保留固定源/收据，不能新绿覆盖。

## 本窄case的三个观察点

范围只原新建的 `gate0-local-render-v1` 首Run、单输入音频、3镜头、无feedback/approve，杀点固定local-shot-1 finish_output实际成功后/原Operation观察前。私有核实版本沿0010；数值不外推其他driver/多输出杀点或所有视频路线。

| 阶段 | 必须保留的实际证据 |
| --- | --- |
| K 杀前与墙钟到期 | 原1 Operation submitting/unsettled、1精确allocation/staging ready、无partial、原文件path/hash/size/mtime；原PID/创建身份及真kill、墙钟越lease；输入/资源/binding身份固定 |
| R 原核实结束、正常尚未执行 | 原1 Operation/1 allocation仍各唯一；原id/run/step/input/dedupe/route/created identity及allocation身份/原allocation_fence不变，原Op有完整实际decoder证据后succeeded+settled、原路线confirmed_no_charge/0；文件path/hash/size/mtime与K相同。核实期间render/allocation/Asset/Step提交新增量均0，不把杀前已有shot1生成、plan Step或输入Asset计为0总量。实际专用结束返回后撤核实grant、Run queued/worker=null/lease0，再正常领新fence |
| N 新正常执行至quality等待 | 同Run/binding/Flow UUID；5 succeeded Step、4 succeeded+settled Operation、5生成allocation，按step分组；原shot1 Op/dedupe/allocation仍一份，原文件仍同K、原shot1 render增量0。新正常fence下只shot2/shot3/compose合法增加；真实媒体/Asset+Step/Flow对应、quality waiting_user与lease0/worker=null |

R可用有限只观察同步闩：包装真实专用结束核实端口，**先调用原方法实际成功返回**再在正常调度之前暂停；读只读DB/文件及即时OS身份，保存后有界释放。不能替原方法返回、改业务SQL/status/clock、阻止权限守卫/心跳、提前跑normal、伪造marker/解码或由测试代执行恢复；闩不代状态转换，queued/撤租约必须来自真实后端。闩超时/观察失败保原退出及清理，不把没有抓到R当通过。不要求增加产品通用测试API或改生产代码来迎合计数；固定端口名/测试包装源码随测试版本纳入冻结。

N使用原生产正常路径；原shot1从已结清证据提交Asset+Step是正常权限行为，不能在R提前做。staging ready→imported/asset_id登记、Step新执行fence等是后续合法可变字段，不能误要求整行永远不变；原身份/输入/归属、原Operation观察及完成文件不得覆盖。新正常fence必须大于核实fence，不能用同grant跨阶段。取消/paused/失lease等负向情形按0010保持，不能强推N。

## 固定分组与不重生成

首Run quality前：local-plan为plain succeeded Step、0Op/0allocation；local-shot-1/2/3各1 settled render Op/1 video allocation；local-compose为1 settled render Op、video+mixed两allocation。共5Step/4Op/5allocation；该隔离case5新输出Asset加原音频共6，但核心按原Run/Step输出关联核查，不能把其他任务全库总数混入。quality revision和审核等待不加媒体Op；此时不包含local-review-approved或任何Bundle/Production succeeded。

不重生成至少同时核：原Operation/目标allocation唯一、固定input/dedupe、K/R/N文件hash+size+mtime、真实固定renderer目标调用记录。计数应区分生成(render_shot/compose)与FFmpeg版本/解码调用，不能把实际核实decoder称render。R期间所有生成新增量0；N原shot1生成增量0，其余三合法Step各一次生成；杀前shot1真实生成总量仍1。记录真实函数原调用而不mock产物；只有“Operation总数没增”或文件hash相同不足以证明没有重render。原没有穷尽调用记录的历史样本保持其有限结论，不补造日志。

## 版本与审批链

测试owner可据本方向编写独立 `gate0-local-recovery-phased-evidence-v1` 判据/新T14命名用例，并将原断言→K/R/N的意义、精确版本/hash/回滚/未测限制成文。原03966测试字节保留不覆盖。**RV13先独立核此新标准/fixture版本，没有固定批准hash前不运行新基线**；测试 owner实际核并冻结最终B7/W7源/资源后再执行，不读取WIP构造隐含期待或锁实现写入。

旧fence拒绝、重复同证据幂等/异证据冲突、partial/缺损/篡改保持unknown、不新claim/预算重置、取消不复活、多输出完整全集、成功Op但Step/Flow窗口以及所有原安全反例继续各自新固定批，不能由本case绿外推。RV再复审修复与证据，AV按自身标准验收；架构不代评审标准、不代验收，不把退出0/计数/日志当真实恢复。

本轮只有设计裁定及正式交接，实施/测试/标准/进程/key/费用均0。完整Gate0→R1独立验收→连续R2及产品内正式API/MCP商用要求不缩；本地模板媒体仍非自主创作/完整作品。FINAL释放，不等未来实现和测试。
