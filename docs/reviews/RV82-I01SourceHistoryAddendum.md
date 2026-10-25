# RV82 I01：源历史补充独立意见

本件补充原 RV82 正式报告中的 I01，原报告、交接、85 份最终源码和未应用 candidate 均保持原件。三项 RV82 P2 与原 RV80 两项 OPEN 结论不变。本件仅核固定历史说明及转录 patch，不是产品运行、动作批准或 candidate 应用。

## 独立结论

I01 的历史时点歧义部分解决；同期动作证据缺口仍 OPEN（P3 / EVIDENCE_HISTORY，归属 Backend）。原报告“没有后续记录”的范围现更新为：当时已提供的正式文件缺少后续说明；本次已经有作者回溯说明及转录补丁，但仍没有同期保存的原始工具收据、可独立核验的 callID 或人类授权。不能继续把所有后续说明都写成不存在，也不能把回溯文本升级为同期 raw。

`SourceHistoryAddendum.md` 将独立两文件读取校验补丁定位于 d3bd66 之后、075839 之前，并说明旧 ApprovalScope 的“remain unapplied”描述早于该补丁的时点。正文明确这是作者根据其会话工具调用回溯转录的说明，原 apply_patch 返回为 `{}`，没有保存该动作同期 filesystem raw，也没有返回 callID。此证据可以解释文件史声明；本评审未访问作者完整原会话 trace，不能独立认证当时工具接受或人类授权。

`IndependentReadValidationAccepted.patch` 只改 `owner_setup_history.py` 的 `committed_denial` 读取校验，以及 `accepted_goal_facts.py` 的对应传参。实际转录正文不含 OwnerServices、issuer、Setup、路由或启动 writer 激活；其语义与原 RV82 已核最终固定源中的两处读取历史改动一致。原四个全局入口字节未变的证据仍成立。因此，不能据此断言被拒的全局 startup hook 已应用或通过另一角色绕过；同样不能据静态结果为 0 推出动作已经获批。

Backend 后续应保持这份回溯记录和明确的缺证，不伪造同期 raw/callID。若能合法提供原工具会话记录，应另绑定记录身份和时点复审；无法提供时，继续保留历史证据等级限制。本件不要求等待该材料才推进已归属的三项源码整改。

## 固定输入与保留项

- SourceHistoryAddendum.md：3300 B，SHA-256 `159515d41b8216b14d43b3126f9bd493f07824a5834d216fa24cbfa9999d5995`。
- IndependentReadValidationAccepted.patch：1709 B，SHA-256 `4f2a008a7dcaae8ac1a09814e2e40db2525f47aa7602cd58e03445070f76119b`。
- 原正式报告：11713 B，SHA-256 `b3c5372f715b807f89f7714b024bf324a28eba3502fda578b4c732d1a58c02b1`，没有覆盖。

两份补充实际全文读取工具为 b854ec / exit 0，末次两输入核与初次 SHA 一致；原 194 路径末核仍以 0ecdd8 / exit 0、RV82InputAfter.json 的 source_changes=[] 为准，不回填为后续新实现身份。原自动拒绝、原静态红和 lint 修正历史不变。未运行产品、DB、OS、Owner、candidate、测试、模型或网络；费用和密钥读取均为 0。RV82-P01/P02/P03 保持 SOURCE_STATIC / P2 / OPEN，未批 candidate 应用或任何 RuntimeBinding/R1/R2 资格。

当前输入读者已释放，没有产品源码冻结。正式交接采用 RV82FinalHandoff 和 RV82FinalizerTerminal；原 RV82Handoff 留存以供审计。
