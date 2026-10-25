# T16：0.3自动对齐证据及完整包候选标准

gate0-v03-alignment-bundle-evidence-v1，candidate revision1，待独立Review；not_ready_for_execution。本轮只有静态签名/依赖与Test-owned适配候选，没有产品import/launch、API/ASR/MCP或B9读取冻结。原RV17准的0.2标准/38计划/原红绿和副本不动；这是ADR0015/0016明确的新版本，不默改旧strict。

## 版本和三scope

仅显式0.3.0-candidate请求进入新分派，由可信安装/项目一次policy预授权解析固定策略/ref并写RequestRevision/hash，普通目标资料后续可自动完成；缺版本和旧key仍原0.2/default/hash。改变版本/policy不得借同key放行，缺配置waiting_user/alignment_required，不猜通用approved。新自动路径是本轮R1要求，不推R2。旧strict每片参考与新合格方法runtime策略不同，二者不偷偷换。

capability_benchmark评价固定实际方法和条件；work_runtime_validation保存该片真实音轨/ASR/全部units/sample-PTS/mapping/subtitles/frames/来源rights/执行身份和policy资格；per_work_reference_measurement仅有该片独立参考时测量。无本片参考status=not_measured且N、P95、reference_ref、measurement_report_locator全部null、不造空报告文件。基准P95/ASRconfidence/模型一致不得填本片数字；可以“方法通过独立基准、本片核验通过”取得新自动release，不能声称本片误差实测200ms。

所有真正语句测量和基准仍采用RV16/RV17数学：每unit=max起/终点绝对误差，完整不同unit数N，nearest-rank ceil(95N/100)，P95<=200000us；先核所有原条目/strict ID/range/长度/唯一性和独立集合后建映射，不采样挑好段或去重。10unit仅一端300ms可区别错误2N20/P95=0与正确N10/P95300000失败。旧错误报告原字节保留却禁止新release复用，需新更正report/revision，不改原费用/历史审计。词资格另批准，不冒语句指标。

## 资格、材料和导入

可信qualification固定实际tool/model/resource/config/device/compute/OS/arch和语言/输入/transform范围，真实独立基准/听审裁决/issuer审批及有效期；snapshot approved、自产hash/恒True或payload不能授信。执行前及publish同writer事务重核registry revoke/expiry/fence/cancel，竞争有明确线性先后；旧token不跨run/preparation，旧声明/备份不能复活已知撤销，费用事实不倒退。两表schema5事务迁移与一致备份/旧程序拒5另验，不降user_version。

MaterialAllocation先持久ID/journal，重启同ID，不包含未来SHA/size/decoded/validated，不是ready Receipt。只用ordinary有效lease和本run/slot；旧fence/核实grant/异run拒。strict有真实参考时先分配report locator→固定AlignmentSHA→一次不可变真实report/Receipt→WorkValidation→Quality→Manifest，不建hash环或覆写占位。无参考自动路径不留measurement附件。各schema_kind只用后端唯一公开/私有模型，实际0.3未发布处pending，不自建DTO。

默认八输出及固定附件/主音轨/ASR/字幕/帧/语义RAG/原来源/许可/权限/原子发布/恢复均沿旧38项完整要求。完整包增加policy/qualification/runtime报告和按许可选择的benchmark文档；embedded_full_report必须真实完整报告，provenance_reference只保原报告SHA及来源/限制，不充benchmark或新资格，不造URL/默认带出不授权语料。artifact依赖无环且完整/projection闭包严格。import保origin原byte/IDs/hash，初始origin_snapshot_only，本地registry另核才能recognized_locally，仍不能继承另一OS/resource执行资格；作品读/文本索引与资格/厂商账号独立。

## 新场景及业务适配候选

旧38逐项原值planned/not_run保留；下表20个0.3场景链接旧需求，全部尚未产品执行。

| 编号 | 旧case链接 | 类别 | 判据与当前绑定 |
| --- | --- | --- | --- |
| V03-01 | T15-01,T15-29,T15-37 | explicit_version_and_fixed_request | 只有显式0.3请求可由可信预授权policy解析并固定进Revision/hash；缺版本仍0.2 strict，旧key按存储版本比原hash，同key换版本/policy409，不自动更正旧包；未来实际request resolver/HTTP/MCP；0.3唯一DTO与overload待固定 |
| V03-02 | T15-09,T15-10,T15-11 | three_scopes_and_null | capability_benchmark/work_runtime_validation/per_work_reference_measurement不得互充；无本片reference则not_measured，N/P95/ref/locator全null，没有测量文件，不把benchmark数字填本片；未来实际独立模型解析与verify_alignment_evidence；目前仅纯谓词 |
| V03-03 | T15-10,T15-13,T15-25 | qualification_execution_identity | 实际method/tool/model/resource/config/device/compute/OS/arch/语言/输入/transform完全在获批范围；未知范围不代表无限，int8回退/GPU/跨OS/漂移不继承；真实Operation/ASR/resource查回及registry匹配；资格/资源真实审批pending |
| V03-04 | T15-21,T15-23,T15-24 | trusted_registry_and_authority | policy/qualification/authority必须可信issuer/审批/corpus/method；普通payload/owner字符串/恒True/本地hash或自产approved不能install或授权；新EvidenceRegistry install/resolve/verify端口实际签名pending；仅真实批准资格可做positive |
| V03-05 | T15-23,T15-25,T15-28 | revocation_release_same_writer | 执行前与publish同writer事务内再核expiry/revoke/fence/cancel；撤销先入writer必阻发布，发布先提交保不可变历史，旧token不跨run/preparation；真实独立进程同步闩锁/read-only journal；不是fake snapshot、假钟或SQL修业务 |
| V03-06 | T15-23,T15-25,T15-38 | durable_revision_replay_backup | registry跨重启持久，重复同identity异正文拒、旧声明/撤销回放不复活；一致备份恢复后不得忽略已知撤销/费用；不要求产品账号；实际admission/revocation日志及墙钟，可信更新渠道pending，秘密配置不入包 |
| V03-07 | T15-10,T15-11 | max_endpoint_N_true_service | 0.2strict和新真正测量/benchmark都按每unit=max两端/N/nearest-rank且<=200000us；10unit仅一端300ms须拒错误2N20/P95=0报告；当前数学pure sanity可执行；真实BundleService/新registry反证另批，不借owner静态缺口计产品红 |
| V03-08 | T15-10,T15-11 | all_units_before_mapping | 全量原Alignment/reference/report严格ID/每range/数量/集合一一对应，重复坏先好后/同值/缺项/额外/乱序/空N全部核；未准sampling不得缩集合；旧RV17原fixture不改；新schema parser/service独立运行待final |
| V03-09 | T15-03,T15-27,T15-29 | persistent_material_allocation | material_allocation重启同preparation/artifact同material ID；Allocation无SHA/size/decoded/validated或未来ready证据，旧materials仅ready Receipt；B10提议私有接口尚无实现；不能猜ID/从SQL拿slot/先stage占位再改 |
| V03-10 | T15-25,T15-27,T15-29 | allocation_lease_and_owner | ordinary lease当前fence、run/request/slot归属每write/finish核；旧fence/异run/异slot/核实grant拒，固定原journal和字节不变；新allocation+actualMaterial journal/read-only观测；不是核实grant扩大普通写权 |
| V03-11 | T15-03,T15-10,T15-27 | acyclic_strict_material_assembly | 分配无hash report locator→AlignmentSHA→真report/Receipt→WorkValidation→Quality→Manifest，无循环、无假hash/placeholder覆写；report严格JSON和原音轨/参考完整绑定；严格路径真实参考pending，阶段return/bytehash/journal精确观察，不拿合成reference做产品positive |
| V03-12 | T15-09,T15-15,T15-18 | qualified_without_per_work_reference | 合格方法加实际全量runtime checks可发布新策略，无逐片必选人标；Alignment仍有not_measured/null，WorkValidation引已完成四版本，Quality不反引循环；当前无资格/真实基准不能发布；真正默认自动创作属R1必做，不挪R2 |
| V03-13 | T15-10,T15-20 | old_invalid_2N_reports | 旧2N不符criterion禁止新release，历史原字节不覆写；更正产生新report/revision/corrected_from与原因，不改原request/费用；实际旧0.2新release及更正链接口pending，既有历史包可用性另记 |
| V03-14 | T15-24,T15-30,T15-31 | benchmark_export_binding | embedded_full_report与provenance_reference按许可；reference Material记录原reportSHA和身份且reference_only，不冒完整基准/本地资格，不造URL，原音频/标注不默认导出；新schema_kind method_benchmark_reference实际唯一DTO pending；真实许可/报告pending |
| V03-15 | T15-03,T15-30,T15-31 | full_and_projection_closure | policy/qualification/workvalidation/quality及所选benchmark文档全索引/闭包无悬挂环；projection独立manifest依赖许可闭合；不可导出不默删自称完整；真实publish材料再export，不能SQL造published来准备权限positive |
| V03-16 | T15-34,T15-35 | origin_snapshot_and_local_recognition | import保持origin原byte/ID/hash，初始origin_snapshot_only；本地registry另认同才recognized_locally，仍不授不同OS/resource新资格；原作品读/索引与方法准入独立；真实第二实例包；0.3import trust字段和唯一DTO未发布，拒foreign grant/authority继承 |
| V03-17 | T15-27,T15-38 | schema4_to5_transaction_and_rollback | schema5两表同writer事务迁移，失败回滚，旧五表/预算/Operation/JSON保留；旧schema4码拒5；SQLite/WAL/引用材料/公开信任身份一致备份，不降user_version；真实迁移程序/0005未发布，不执行新migration；不会用SQL修改业务求绿 |
| V03-18 | T15-21,T15-22,T15-36,T15-37 | real_transports_and_once_command | 一次目标资料触发完整自动流程，HTTP/MCP断开持续；服务/真正HTTP/真实MCP宿主通信分别证明，payload主体拒，Range304分页授权在前；HttpAdapter仅调用自己loopback已启动API；MCP factory/SDK handler不是真host，实际argv与finalhost未发布 |
| V03-19 | T15-06,T15-13,T15-17,T15-18 | runtime_whole_material_checks | 真实主音轨/完整ASR/全部unit/gaps/samplePTS变换/字幕/帧/语义/源稿差异/来源rights/默认8和附件全核，不信media.passed；W10有限owner真ASR/材料及strict blocker不继承独立绿；0.3producer尚未实现，真实全作品待验证 |
| V03-20 | T15-19,T15-38 | independent_benchmark_and_scope_limits | 方法独立基准、人听标注/裁决/authority必须审批；MM05>=30题60作品precision>=90%并reportrecall/refusal，全拒答不达标，词资格/跨OS/AV/R1R2另验；所有真实基准/资格/fullBundle/MM05/视听/机器尚pending，纯数据sanity不授资格 |

tests/bundle/t16_business_adapter.py对B9已签BundleService十三个方法保原typed arguments/返回/异常，用真正服务类型及guarded lazy import；HTTP实际urllib请求仅已准自己的127.0.0.1 origin，禁代理/redirect/覆盖认证。没有构造伪Asset/报告/公开DTO、SQLpublished或恒True authority。MCP候选只在未来实际host/executable/argv/source固定时用SDK ClientSession真实stdio通信；现有create_mcp_server factory/SDK handler不算宿主，当前host绑定缺失。

t16_guard.py要求未来Review+root运行准入、完整生产/测试正文预存及hash、资源身份/自己实例/费用0；当前未调用。t16_assertions.py为测试期望，与生产模型无关。实际fixture bootstrap、0.3 DTO提取、registry/Allocation接口、真实authority安装、最终producer/迁移/API派发和MCP宿主尚待固定。现有适配函数存在不是20或38项已可执行业务用例，更不是服务/API/MCP业务通过。

## 准备命令和执行前提

实际可执行准备入口tools/testing/t16_prepare.py只AST和6项自己plain-data sanity，无服务适配实例化/HTTP/MCP/DB/ASR调用。实际退出/原日志另记COMMANDS，合成字典不注册资格、不当独立语料。本轮不会调用t16_guard/ServiceAdapter/HttpAdapter或real_mcp_session。

未来产品拟命令/依赖在T16PlannedCommands.json与T16SignatureDependencies.json。未发布命令和唯一DTO的binding显式pending，不虚构一个pytest/CLI已存在入口或借intent/presence计通过。实际运行需独立标准/adapter审批+统筹另准最终全源/资源；launch之前保存真实生产/测试正文及全依赖before-after，漂移不launch，失败原句柄/raw/PIDCreation/heartbeat/lease墙钟/真实清理保留。旧T14正文缺口不补。

缺真实独立语料/听审裁决、method/authority审批、单片qualified完整包、MM05至少30题60作品人工标签、AV/词资格/跨OS机器和许可都pending。它们不阻本轮准备，但不能用本sanity或owner W10 ASR/严格blocker替代。MM05precision>=90%且recall/refusal报告、全拒答不能过，精确来源版本100%保留。费用/key/private实例读取0；只Test路径，无生产/依赖/锁/SDK写。标准和候选停写交Review，Gate0→独立R1→连续R2范围不缩，不自关产品问题。Rollback仅未执行Test候选，新旧历史及产品事实不改。
