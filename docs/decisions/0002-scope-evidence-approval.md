# ADR 0002：批准范围与证据规则的独立标准版本

状态：架构批准，仅限下述范围；日期2026-10-08。永久角色development_role_plan/架构师，不代评审、标准owner或验收签字。

批准T2记录版本`0.1-scope-evidence-review1`中已由RV0评审的需求编号/阶段、原始规格hash、真实/模拟/检查区分、权限/预算/恢复、作品包必要项、反作弊及独立验收规则。21 FR、24 AC、11 MM、8 CM共64映射；Gate0 11项，R1必需51项、R2必需63项，FR05/10增强与FR17留R2、FR18排除。R1验收后连续R2范围保持。

架构只读核验4标准当前字节与归档全部匹配、11输入规格全部匹配、RV0报告和snapshot匹配，源追溯保存于`G:/开发测试/Codex/VideoCreatorImplementation/Architecture/A1SourceTrace.json`。未复跑产品测试，不将证据结构验证当实际行为验收。

| 已评标准 | 批准的SHA256 |
| --- | --- |
| GATE0.md | f7bfa7cf75defd88976726a2e2d808f2f2b9c637be09dd63b92483d782973310 |
| ACCEPTANCE.md | 1302a9921f16e3b44a92eac209d9c03f7b4147f34f6d7c0028985ee2764f3155 |
| TRACEABILITY.md | c011340ce6a023b26e0faea6d1169d4bc0e29e769798df22efaa09c7f0e4c68a |
| BASELINE.json | 1c94708cf495e4f49833b446b2280cec1a492553eb81d7b95b4bd4f859c9607e |

RV0报告SHA256为`715aa5fee537d903255f9732d9e2ba1145a62bb1151ff5ba85becf3f0846cded`，snapshot为`8e3a536b9f112cbe62f1e30d48b27d30a30a1eb3172e309fb1d075c113dceb90`。受审STANDARDS-FREEZE.json本次hash为`a49171838247288e962009118de928abb923c70e6b0d5ed02a2ba6edf225578b`，当时状态review_approved_architecture_pending。

标准唯一owner仍为测试开发：由其登记本ADR路径/hash及批准范围，保留原四标准/归档和失败；架构不改criteria。用户后来明确的Kimi共用授权及官方服务内部API/MCP硬门槛在新治理记录生效，不能倒填旧实验或静默重写已评标准；后续标准附件由owner版本化、评审后纳入。

不在本批准内：具体Provider/高级R2能力、最低OS矩阵、音画对齐/检索测量方法与待验证阈值、最终生产编排/打包。技术栈/Gate0/R1/R2均未批准通过；标准冻结不能被消费者解释成这些实现已通过。
