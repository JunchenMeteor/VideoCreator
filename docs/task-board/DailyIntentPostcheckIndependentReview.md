# DailyIntentPostcheckIndependentReview

- 状态：QUEUED，尚未运行；唯一角色：独立评审。
- 目标及顺序：完整R1独立验收后继续R2。本卡仅复核既有DG-WRITER-P01修订，不替代真实DB、Owner、安装资格或阶段验收。
- 输入：Backend/QualifiedIssuerAndWriters/DailyIntentWriterStage/固定ordinary89及五份历史报告；必须读SourceIndex/SourceFreeze/Handoff真实字段和完整相关源码，不读A45正在修改的生产源。
- 固定Handoff.md SHA544671153c3dc0f150197d2d3b3e9d260c10ddff7b9dbe9368cc237917234b2f；SourceFreeze.json SHAa213ebff5d1abc6133d75c48c0ad7a9e22de16a0c4a16db59857489cf1cc4dd2；SourceIndex.json SHAe5c5bf1fc69186f81c01d93e47b7996c1c938409b346eb80adf69342541b8ef4；SourceDiff.patch SHAb25461f4b14e7cbe2958ca4b989bae8b188ffa677e1ed4721c23dbc8954cbf63。
- 先读取当前工作区/仓库规则与卡；记录实际commit/输入完整索引。不得借口Review角色改实现或测试，也不得把热修改源加入冻结结论。
- 检查：daily common postcheck是否覆盖new/replay/equal locator的全部Command及locator写入、是否确在同事务commit之前；同source/sameconnection链与BaseException rollback；保留原期限/ID/幂等/unknown intent文件及预算/floor语义；原DG-P01其余writer结论不可推定扩大。
- 写白名单：docs/reviews/及自身Codex/VideoCreatorImplementation/Review/DailyIntentPostcheck/，实现、测试和标准只读。
- 实际命令：本角色固定读者/独立源比较与语义检查，不执行产品/DB/模型或安装。原始输出完整保留；所有自身工具跟踪到terminal和双EOF，不能把观察超时算终态。
- 产物：独立报告逐项关闭/开放及证据范围，明确SOURCE_STATIC与实际DB/OS分层；InputPins/Handoff/真实terminal及所有读者释放。不能凭一行比较自授完整运行资格。
- 回滚：仅自身报告；下游统筹、Backend、Test、Acceptance；无收费/密钥/外部副作用。
