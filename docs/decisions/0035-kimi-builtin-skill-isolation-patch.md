# ADR0035：Kimi builtin skills的三文件受控修订

2026-10-10，A32。**批准G01最小vendor差异设计，不代表运行隔离/安装或服务权通过。** 固定SDK0.0.6 commit `ed4be6be5280d02191da88bbafb3f828dcd33d72`；CLI1.45.0 commit `92ce7ca53fb6edce2eb295304e7a5ce207f7062c`，Kosong0.53.0。24必要源码经I55 OrdinaryIndex精确映射逐项bytes/SHA匹配；来源/普通路径见Architecture/KimiBuiltinIsolation-A32/InputPins.json。未安装/import/运行SDK、账号/费/联网；被拒AuthSessions不读。主Engine唯一编排、ADR0034、完整R1→R2与I53默认启动继续。

## 为什么必须修，以及准确调用点

固定CLI `soul/agent.py:229` 的 `Runtime.create`调用`skill.resolve_skills_roots`（**不是app.py直接调用**）；`skills_dirs`非空时替代用户/项目发现，config extras仍另加、plugins仍另加；`skill/__init__.py:286`在local/acp无条件追加builtin目录。随后同Runtime用这些roots discover/index/格式化系统prompt，并派生外部skills_dirs，因此事后只清一个list或过滤提示词不完整。SDK把空skills_dirs转None，不能靠空list禁发现。

已读固定24文件内仅此resolver分支使用get_builtin_skills_dir；本轮没有完整CLI全树，不能把有限库存推成全包无其它旁路。Integration构建前须对精确完整CLI源树/资源的builtin-discovery引用做有限清单，额外入口若存在交接而不擅自删掉或扩补丁。builtin技能是模型指令/可发现资源，不自身等于工具执行授权；隔离要求仍排除未经准入指令与资源路径。

## 唯一最小差异（Integration负责实现）

| 上游文件及固定原身份 | 允许改动 |
| --- | --- |
| `src/kimi_cli/config.py` SHA `77802fce6b65addf061e1607e04de0646ffa06d1d4c38d807a4cff6635a791c9`；blob `451f4681000aaeede5d80c88d12c95042138bc43` | Config增加`include_builtin_skills`：严格bool，默认True；Pydantic使用严格布尔字段，字符串、整数0/1、null均拒，不能由truthiness强转 |
| `src/kimi_cli/skill/__init__.py` SHA `887dfc32fd076ef1a6b0d1beeadc26f6c8db2ca7b253227bd6881afdbcbb36f8`；blob `67e35052263dd5bdf0650594692e6c56066b7257` | resolver增加同名keyword-only参数默认True；直接调用也只接真实bool，非法类型在任何发现前拒。仅使builtin分支要求参数True且原_supports成立；不改user/project/extra/plugin顺序、backend识别、索引或资源路径，不移除_builtin函数/模块/skills包 |
| `src/kimi_cli/soul/agent.py` SHA `47d4d2cada5bc00e3330c46f03cf4f91d020316323395ff2251d0176ac33500a`；blob `a208e08796a5dd2f516f1ffff6d0b046b20cdd13` | Runtime.create调用resolver时显式透传`config.include_builtin_skills`；其后的discover/index/prompt/skills_dirs统一使用同结果，不在旁边补第二套过滤 |

上述是三个生产源码文件，SDK Session签名不修、app/config发现链不偷偷改、无全局monkeypatch/伪KAOS名称/替Path.home。SDK现Session.create/resume可透传真实CLI Config实例，产品factory须每次创建/恢复明确`include_builtin_skills=False`；upstream普通CLI/未给该字段的其它使用保持True兼容。产品不公开“重新开启默认技能”按钮或任务参数，不永久删除技能能力：合法媒体能力仍通过已准typed shim/可审固定产品技能进入外层Engine。

产品必须核受控patch/runtime身份与Config实际字段的严格schema存在，然后核实例属性**is False**；原CLI未知字段可能忽略，不能只把False传给未修版本冒成功。运行后完整skills catalog、system prompt技能段/外部roots与工具catalog必须核来源全集相符；声明值不代实际发现验证。旧无patch会话不得按本profile继续付费prompt；显式告知原runtime/策略不相干，保会话和unknown账本，不create同id截断、不清收费或迁底层。

## 三文件之外仍必须成立

vendor参数仅关builtin追加，不关plugins或网络。产品仍使用：无extend固定agent、tools与allowed_tools精确guarded shim、subagents={}；`mcp_configs=[]`；显式Config hooks=[]/telemetry=False/yolo=False等I55边界；非空skills_dirs指受控私有空目录，extra_skill_dirs=[]；private KIMI_SHARE_DIR，其plugins不存在。loader在显式agent工具之外会追加plugin工具，故目录“不存在”只是当时事实：宿主须保护私有父目录membership和来源，启动/current复核，不允许model/tool向该根写入。若插件目录被创建/替换/符号链接或root变化，拒admission而非扫描未知工具。显式技能空目录也必须实际存在且受guard，不能失踪后回退用户发现。

工作目录/全部祖先要实际无未准AGENTS/.git发现，不靠HOME设置推断；SDK日志/本机项目数据的写入目录与只读runtime/技能根分离。闭集env防model/key/baseurl/headers覆盖，sys.path/包实际origin与patch完整资源guard一致。Windows/两POSIX的原资源保护、目录membership及实际peer/lifetime按原ADR，不凭路径SHA或本参数给qualification。

G02 OAuthManager/managed-model后台refresh及其它隐式网络、G03活动prompt/cleanup/后台终态、G04保存yolo/afk/auto-approve/additionaldirs/system_prompt恢复、G05完整依赖/native/artifact、G06真实生成服务/文件取回仍独立pending。离线验证须外部阻断真实网络并观察attempt，不能只相信hooks=[]/telemetry=False就无网络。若G02需要额外source修改，先交具体源差异归架构，不把本ADR当整CLI重构准入。SDK/tool事件仍只观察；唯一shim受理原Owner/current/fence/Operation/预算，付费prompt也先受理，不SDK另起无限agent。

## 许可、构建身份与回滚

I55已得SDK/CLI完整Apache-2.0及NOTICE；本轮实际核§4，允许在满足分发条件下修改，故不因没有官方禁字段长期停G01。Integration保原全文LICENSE、版权/归属和NOTICE；CLI含OpenAI Codex的skill-creator归属，技能未删除不能因禁发现去掉NOTICE。三个修改文件须显著标明由本产品修改及日期/patch ID；新增说明不改原许可、不冒上游或商标背书。SDK源码许可与Code/会员/平台/official后台服务权分别核，Apache不授在线服务权益。

采用项目纳管的确定补丁`KimiBuiltinIsolationV1`：完整原CLI固定tree→校验上述before SHA/blob→仅应用三源差异→记录diff SHA、每after SHA、SDK/CLI/依赖锁、构建命令/producer工具和生成artifact/RECORD/实际load-origin→纳入独立ProviderRuntime及原Held/PreparedLaunch资源闭包。131普通件/24必要源不足以自行拼完整包；必须取得同commit完整build输入及生产依赖/平台许可，tag或官方wheel声明不能自证producer绑定。分发产物明确独立本地build身份，例如CLI `1.45.0+videocreator.1` 的包metadata（这项metadata/version标注不算第四个行为补丁），保上游1.45.0来源，不能把patchedwheel冒官方原SHA；不升级SDK/CLI/Kosong来绕接缝。

回滚按不可原地改的版本包切换，仅回到**已符合本产品隔离要求并独立验证**的完整runtime/patch版本；若没有该旧版，只关闭本Kimi Provider新受理、保local/BYOK其它能力及已有任务取回/核实，不能回退unpatched默认发现恢复生产。已受理Operation/session原版本先终态/核实再回收guard，不能替换仍加载资源或把unknown置0。后续上游若提供官方等价字段，可凭固定源/语义/反例另审替换补丁，不永久维护另一个agent框架。

## 下一角色与必须独立验证

Integration I56仅实施三文件补丁、版本/版权材料和固定来源闭包，交before/after/diff/artifact/运行时消费签名；实际离线import/创建catalog/停止恢复需其明确后续卡，不借本ADR发模型/账号请求。Backend按真实Config字段显式False、原profile/current和会话相干性消费，唯一typed shim不由观察者再执行；Media提供合法submit/query/download/usage/cancel工具合同，不借禁技能丢生成能力、猜官网插件endpoint。Test独立所有测试，Review独立复审，不由架构写实现或期望。

Test必须覆盖：local/acp的default/True保原builtin，False的roots/discovered catalog/index/prompt/外部skills_dirs均无builtin；严格拒字符串/0/1/null；同名用户/项目/extra/plugins样本不因builtin flag误关或重排序（upstream兼容），而产品profile不发现这些样本。SDK空list仍是原反例，非空私有目录才覆盖；插件目录中途创建/替换/链接、额外AGENTS/项目发现、未修CLI吞字段、未知工具/Task/Shell/MCP、恢复旧builtin prompt/saved授权均实际拒或明确不相干。合法单shim正向真实执行一次进入原Operation，流重放/同ID不同参数不重复，越权/预算撤销/断线无未知副作用；三OS真实执行及完整退出/原guard另测。模拟只证协议，不把0模型离线绿称Kimi媒体或official完成。
