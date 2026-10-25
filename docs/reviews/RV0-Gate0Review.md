# RV0 Gate0阶段独立评审

日期：2026-10-07。永久角色：integration_review，仅评审；不修实现/测试/标准，不兼验收。范围是T0候选标准、稳定B1/W0、T1已交证据及I1候选checkpoint；W1/I2中间态不在本次实现评审范围。

## 结论与冻结边界

**标准覆盖与证据规则通过本次独立评审，可由标准唯一owner与架构据此冻结独立的标准版本；生产技术栈、整个Gate0及R1/R2均不可宣布通过。** 本报告不修改BASELINE的freeze_status，也不是AV0验收签字。

01—11当前原始字节SHA256全部匹配BASELINE。21 FR、24 AC、11 MM、8 CM无漏项；FR05/FR10增强及FR17保留R2，FR18排除本次；所有R1项继续列入R2回归。Gate0有11项，R1有51项、R2有63项。候选标准区分真实/模拟/检查、必需项skip0、成本unknown、制作与发布授权、真实作品/安装/支付/发布及来源/时码，不以设置入口或旧素材替代生成。

可冻结：范围编号/阶段矩阵、原始规格hash、真实与模拟判定、权限/预算/恢复规则、作品包必要项、反作弊与独立验收要求。标准owner应固化本报告与RV0Snapshot的版本/hash，保留T0旧版及历次失败；后续COMMANDS新增执行历史不得倒填成旧实验的已测commit。

尚不能声称已冻结验证：具体供应商/高级R2能力、各OS最低支持矩阵、媒体对齐/检索的测量方法及待Gate0验证指标、最终生产编排/打包方案。这些是仍需测量或裁决的附件，不能因标准版本冻结就变成通过；变更必须新版本独立评审，不能降低门槛消除已有失败。

13项是证据工具自身单测；56项是生产机制及非付费上游注入测试。均不能折算为真实模型协作、成片、三OS安装或商业集成通过。validate_evidence.py只验证记录结构/hash，输出明确external_behavior_verified=false；这项边界正确。

## 精确代码与证据范围

- I1 commit `6a6fb8d6f32049e645bde6ff03f35f18b5df6fd4`：42文件，B1 17/F0 3/I1 22。42个commit blob与manifest SHA256全匹配，评审时working tree对应42文件也匹配。该commit不含W0/W1/T1/A0/统筹文档，不能作为全产品可复现冻结点。
- B1：17源/迁移SHA256全部匹配；候选公开Schema0.1.0、DBv2。SDK manifest三项公开Pydantic/API/CLI源与生成输出匹配该checkpoint。未据生成类型数认定HTTP/MCP创作闭环。
- W0：7生产源SHA256仍匹配交接；没有纳入上述commit，按working tree/hash评。历史三轮中真实委派0，guardrail拒绝正确；第2轮构造失败调用0。历史spent0.077518/reserved0为最高价格usage计算，非实收账单；后续W1费用不能沿用该历史余额当当前总账。
- T1 stable：实际Receipt exit0、XML56/failed0/error0/skip0、80.308秒，stdout SHA256匹配，before/after source_changes=0。原29pass/2fail证据保留，原两失败名称准确；取消unknown核实入口和同长度资产篡改经B1修复后稳定测试为绿。此为证据审阅，本角色未复跑，独立验收仍由AV0执行。
- T1 final：69主测试含13工具自测，另7子测试；新增kimi.py产生source_changes1，不计整源冻结。当前与stable相比有测试/工具格式变化，已按交接单独列明；稳定旧结果不倒填给未测新源码。
- I1：LangGraph隔离导入、ASR模型加载不是实际对照/转写；FFmpeg/ffprobe/font不可用、VS bootstrap签名有效但未安装、Rust待验证、macOS/Linux未测；支付/发布未获必要条件。F0只是本地草稿工作台，真实Engine/媒体连接由后续F1验证。

## 阻断问题

### RV0-P1-01：ReAct回合失控，真实响应中的Action未执行

归属：W1 Agent/媒体；独立反例归T2。触发：W0第3轮两个真实已结算Operation均在一个completion内输出3个Action、模型自写3个Observation和Final Answer。RV0以sqlite mode=ro/query_only读取仅这两个公开自造科普响应，内容SHA256/标记偏移见RV0ReActEvidence.json，未读取vault或密钥。

证据：ControlledTextLLM（workflows/controlled_llm.py:53—58）声明native tools=False、stop=False；DeepSeekTextDriver（providers/deepseek.py:58—75）payload不发送stop/tools。锁版CrewAI1.15.23 agents/parser.py:95—101一见Final Answer即返回AgentFinish，先于Action分支103，因此这些Action根本没执行。锁版executor:340—350选择ReAct路径；经理任务creative.py:139—155强调最终JSON，不能代替单轮Action协议。实际两响应均存在Action/Observation/Final，故不是“首prompt缺工具”。

修法：保留账本边界，在受控适配器约束单轮Action/最终答案互斥、Observation只由真实工具回填；若保留ReAct则验证有效stop及回合处理，若改原生tool_calls须完整处理工具Schema、消息/结果/幂等/费用，不能只把supports_function_calling改True。先免费复放现有响应、混合Action/Final及虚构Observation反例，禁止收费盲试或硬调用delegate冒充模型协作。

### RV0-P1-02：委派guardrail正证据不足，可把尝试/问答/失败当完成

归属：W1；反例归T2。creative.py:25—36只看delegations>=2及processed_by_agents包含洞察师/编剧。锁版tools/tool_usage.py:598—608在tool.invoke（622）之前计数，Ask question也计delegation；task.py:1148—1152直接把传入coworker加入集合。base_agent_tools.py:112—123在子任务异常时返回错误字符串。两次尝试、AskQuestion或子任务执行失败也可能满足守卫，未证明专业成果成功或被最终方案消费。当前真实0失败仍成立。

修法：用执行后的专业子任务成功记录（真实角色/任务/输出hash/Operation关联），区分delegate/ask、attempt/completion、失败/成功，最终方案可回查所消费产物。免费反例覆盖两次AskQuestion、失败错误串、只有角色名、产物未被使用；固定Action注入只能计协议故障测试，不能计真实自主协作。

### RV0-P1-03：首次并发初始化可把DBv2降回v1并重复ALTER

归属：B2后端；反例归T2。**这是确定源码交错推演，尚未实跑；本报告不把它写成实测失败。** database.py:27—33先读user_version=0，在writer lock外executescript(0001)。0001_ledger.sql:62无条件user_version=1；只有后续0002阶段35—40在BEGIN IMMEDIATE内复查。

触发序列：A、B都读0；A完成0001/0002成为v2；B随后执行0001把已含cancellation_requested的数据库标回v1；B的0002再ALTER同列报duplicate column，可能留下v1版本与v2结构不一致，后续启动也失败。56项中的并发用例不证明此首次初始化交错已覆盖。

修法：从初始创建开始统一迁移writer锁，在锁内重读版本、原子迁移并提交正确版本；留意sqlite executescript隐式提交，不能仅在外层加一个看似事务。T2用非付费两进程/明确屏障固定交错，并验证中断恢复、v1→v2保留Operation与预留费用；不删除原ValidationInstance。

## 改正、未读与下一责任

接受T1展示名→delegate_work_to_coworker注册名纠正，原错误断言和失败保留，标准未降低。W0 delegation_tool_in_prompt只匹配带空格显示名，是不可靠诊断字段，W1应按实际注册协议记录，不能作为工具不存在/成功的证据。

私有pytest实例ManagerPrompt.txt直读返回EPERM，本轮不改权限，不能说已直读该artifact；按锁版源码、T1测试及交接判断纠正合理。完整prompt复核需T2提供无秘密公共拷贝及原/副本hash。实际Round3响应已通过只读账本独立定位上述协议问题。

阶段移交：T0/架构可冻结已评标准范围及证据规则；W1处理P1-01/02，B2处理P1-03，T2独立反例并保持旧覆盖；F1消费固定SDK、I2处理实际媒体/构建资源。RV0随后复审精确新源/证据，AV0独立验收。统筹只汇总，不能代签。
