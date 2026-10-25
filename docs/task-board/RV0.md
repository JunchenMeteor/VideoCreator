# RV0 独立评审任务卡（待分派）

永久角色integration_review，仅只读实施源、测试、原始规格、架构与标准；可写docs/reviews及Codex/VideoCreatorImplementation/Review。不得修实现/测试/降低标准/兼任最终验收。全目标R1后连续R2。

先审候选验收标准：T0Handoff.json、GATE0/ACCEPTANCE/TRACEABILITY/BASELINE、COMMANDS及证据工具，核对当前01—11来源hash、21FR/24AC/11MM/8CM、FR05/10增强及FR17R2、FR18排除、R2保留R1回归，不把工具13项当产品通过。标准可在实验前冻结审查，技术栈冻结仍需所有Gate0实验及独立验收，不混淆。

再读B0/W0/I0/I1/F0实际交接和精确commit/build/schema，仅评已有实现，未实施仍not_run。关注领域/租约fencing/稳定Operation/unknown费用及禁止盲重交、Flow与业务两库窗口、自然语言反馈不能扩大批准、公共Pydantic唯一源与生成SDK、媒体真实播放/对齐、当前依赖约束与平台真实性。

关键已发现实际行为：CrewAI1.15.23自定义BaseLLM.call也有自动rate-limit重试（最多3次，含异常链/消息分类）；核对W0受控Observation与B0账本确实阻止不确定付费请求重新提交/角色更换重置预算，不能只注释max_retries=0。非阻塞HumanFeedbackProvider/persist独立进程机制probe成功，但不足证明完整账本恢复。

资源与外部动作：.ssh相关密钥源不可输出任何文件内容，不复制源到repo/Codex/deps；测试API全团队总上限CNY20，两key不叠加；专用生成媒体未配、mac/Linux无实测、支付/发布/签名未获必要条件。不得读取真实密钥用于审查，安全检查使用不泄漏的fake fixture或代码审查，实际调用由受控引擎授权。

输出分项问题、严重性、触发与证据、归属/修复建议；问题交原角色，自己不改。通过评审只表示所审范围，无组件/OS/商业证据不能写整个Gate0/R1/R2通过。最终由独立AV0验收，统筹不能代签。
