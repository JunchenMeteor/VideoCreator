# Backend120 三项修复独立源码复审

结论：SOURCE_REVIEW_FINAL。原 B120-P01/P02/P03 的精确源码反例在本停止版本可标 CLOSED_SOURCE_STATIC_ONLY；不关闭 runtime、SQL、合法作品或整个 current/初始对齐目标。新增 B120R-P01 为 P2 / OPEN / Backend：真实不同 ASR/CTC 方法的合法 WorkValidation 仍受继承 ASR-only gate 阻断。此处没有运行产品、Pydantic、SQLite、ASR/CTC、模型或测试。

## 固定版本

任务卡 SHA `71463ce782ce515dc2289ea9cdd69a27e1d34b3681b1dcd517526e1291abcf9f`。三套完整停止普通源各120件，按实际 source_map/ordinary_copy 核身份，分别为：原120索引 `7022d167fe0ef30a05aba3972dacd1be012d440c6f9a98e543e0d5669e167660`；P01/P02阶段索引 `91d8aab600d9b05d3e0a080eb8ccaa4aaaaa078e64aa9428fca85db17ed0eac9`；最终P03索引 `124c951d82c25f000bc9541117a6938b8c872ee321588fff2e0b7028236cb6fd`。两个阶段完整diff全文已读，并用自有stdlib从全部前后源重建，逐字相同：7135B / `6e8cdc3c21be88ccbb8a781fa8e703114df7be5a558cf5b4ae0c72be69d4d2d1`；6031B / `2e61a05066f78a995c9ff5517dd76929d630f9609acdf12806a81f3ca4900121`。

阶段一只改 current_final_evidence_recovery.py 和 registered_alignment.py，118件字节相同。阶段二只改 registered_alignment.py，119件字节相同。最终两个唯一变更文件 SHA 为 recovery `605ea20c9b2491ed780c24e67089620be98fcc0c938eb48ee0e97c047f384434`、registered alignment `95971adaf4116791c67423af217b6409167dd24f0d3c9ad017dc38c510832ca6`。原120三个 Finding/正式报告保留，不将修订回填旧身份。

完整审读变化方法与必要共享前后事务/令牌/发布/原实际结果上下文；未将109 AST或作者列表当运行验收。仅补充停止 Media38 bundle_v03.py 与新的 STOPPED_SOURCE_GAP 交接：后者三普通copy与本最终120对应源大小/SHA逐项一致，非热 Media 或运行证据。该补充单独记录InputSupplement，不改原InputBefore。角色候选§1–5及被拒intersection不属本卡。

## 原三项独立裁定

### B120-P01：CLOSED_SOURCE_STATIC_ONLY

最终 `_alignment_sources` 194–285 先通过原 settled ASR/context完整text/language/audio/ordered utterance和word范围校验，226–230确保原transcript方法并对initial prediction方法相等；275–276对initial每一预测单位与对应原ASR范围严格相等。全单位ID/order、时钟、实际Masters/ASR文件/source guard保持。不是比较自有SHA代替原来源。

独立AST核实际三处调用：register_initial_alignment 692明确 initial=True；common _alignment_preflight 345转发原持久分支 initial；prepare_affected_alignment 752明确 initial=False。没有默认省略mode。初始登记/重读均落同检查；affected原合法CTC时间/方法差异不会被初始条件误强制回ASR。原类型/schema/semantic/mapping/真实登记、权限与源快照仍在原链。

关闭仅针对“自有prediction时间可改而没有原ASR比较”的源码反例。合法初始/replay/字词差异拒绝、actual affected兼容及真实资格未运行；不能据此声明实际初始制作成功。

### B120-P02：CLOSED_SOURCE_STATIC_ONLY

最终 recovery 225–236以独立 `_NO_NEW_ASSEMBLY`默认，并仅允许 observed原None + explicitly supplied exact str + actual等该str 的首次binding例外。默认文本→None、文本→不同、None→未明确授权新文本均拒；显式None也不是例外。原相同值（含双None）不误拒。observed已有文本不能借参数替换。READY measurement原三列source仍同connection比较。

persist 264–296先验证完整真实context/correction来源与rights，writer前279无例外；只有289真正INSERT后的292允许该已验证canonical body，原immutable冲突拒、current binding、issuer/origin前后门保留。正常verify 1320/1329和publish 1408/1451仍用默认精确snapshot，verification原pair token 1338、publish 1372–1376重读相等。异常仍由原transaction rollback传播；没有改SQL/交易吞异常或临时清预算。

因此原text→None漏洞闭合为源码等级；原B118 source-present author/measurement比较支持保持。正常SQL、并发writer、rollback实际Rows、恢复/发布均未执行，不能从分支分析认实际数据库通过。

### B120-P03：原完整对象相等反例 CLOSED_SOURCE_STATIC_ONLY；完整闭环保OPEN

最终initial gate 433–484先读原成功settled Op+committed Step/实际JSON及immutable source；原完整transcript和methods恰原source+唯一actual CTC保持。463重核完整记录SHA。若Alignment原对象不相同，469–475仅准相同精确Alignment家族且ActualTranscriptDocumentV03/BundleManifestV03，precision.status=measured，并要求完整JSON排除恰precision/content_sha256后的所有字段相同。原边界顺序、音频、ID、方法、时钟绑定均不能借measurement改写；旧/未登记路径不造此派生权限。

486–511对实际prepared receipts和当前bundle_items逐artifact核完整identity、ready、schema/MIME/size/SHA；读取实际原文件 bytes并再核size/SHA，typed解析后还须同READY transcript。476–483调用原完整_v03_documents，保原qualification/runtime、benchmark来源、实际参考report、完整N/P95/200000us、独立listener/arbitration/许可和registry来源门；没有写 measured 指标、没往推理输入加gold，也没给getter授authority。原CTC result 853–854仍严格not_measured/P95null。

新增source第四成员为同查询完整ordered8列：material_id/artifact_id/relative_path/sha256/size/media_type/schema_kind/status。material rows的SQL快照在writer 531–536与同connection重读比较；初始registration/原Op/完整Step前三source成员仍比较。verify 1313获取、1321/1330前后校验，token 1341保持原完整source；publish 1377–1381与token相等、1409/1452前后校验。原Asset材料写入的material_id为空，不误纳该snapshot。未测file/OS攻击、数据库并发；不能把八列相等认所有TOCTOU原子安全。

完整原对象相等错误已被精确派生支路替换，旧反例源码闭合。但其full verifier中的CTC实际执行来源仍有下列继承接缝，故合法独立测量/完整成包没有通过证据。不是删掉原测量门后获得绿。

## 新 B120R-P01 — ASR-only runtime gate

P2 / OPEN / Backend / SOURCE_STATIC。正式Finding：本过程Finding-B120R-P01.md，原SHA `07acfa0d625dc6a9874fbd6db547bafbcb11ccbb880592262d822fb9f20ff386`；精确consumer行补充单另存，不覆盖原件。

最终固定bundles.py SHA `6e8be51a3349192508888c773134c15e37783ba117bf85a421ff256beaaaa46f`，三版字节不变。实际函数是 `_validate_work_runtime` 2372–2432，非Media说明中的泛称_verify_work_validation。新派生门483→_verify_v03_documents2517→该方法：2416–2428仅在同run成功settled Observation满足 `matches_actual_asr`及raw.runtime的execution/device/compute/model全等WorkReport时设runtime_match。145–164的predicate明确需kind=actual_transcript、原text/segments/整数时码。否则2429–2431以work_execution_identity_missing/409拒。

精确合法触发：原ASR A和独立已登记CTC B（B不在原assembly.methods，registered method gate 429保证新方法非原ASR），WorkReport/qualification真实绑定CTC B，原CTC输出保持其真实generated JSON/request/execution/preparation事实，未伪造ASR kind/segments。即使operation_ids同时保留两原成功Op，ASR虽匹配原文本却不能匹配B runtime；CTC虽属于B却不匹配ASR predicate。runtime_match仍false，在独立参考数学门前被拒。这里不宣称所有组合模型/方法都失败，也没有实跑阳性实例或反例。

修复归Backend：独立保原真实ASR来源，另接原registered CTC request/成功settled Op/committed Step/单JSON文件与实际Alignment、完整执行identity；不能复制ASR runtime改method、伪装ASR输出、信caller字段、跳过qualification/source或放宽precision。独立Test日后需不同真实方法合法阳性及错Op/错method/伪来源负例，不能据本评审自授运行。

## 保护、证据等级与未测

本次两完整diff重建与逐方法AST显示：阶段一只改变上述source检查四方法和pair writer；阶段二只改变initial manifest gate/writer并新增materials reader。原_result_facts/_commit_alignment/_read_alignment、注册资格/请求grammar/canonical、实际第九method、权限/fence/取消、原预算unknown账本、原child/counter、公私Schema、Engine/Worker/executor/ASR journal/plan_repair_service均受完整原字节或函数保护。原bundles v03、legacy双authority函数/callers和阈值也字节未变；不等于本轮实际执行过两authority。新直接调用现有v03验证链没有读到回调initial gate的直接递归调用；不作未知第三方callback安全或运行保证。

b03009/0规则卡全文；ccf698/0两正式交接/接口；e476e4/0三版身份+完整两diff；9f751b/451aaa/f013f6/e7d0cc均自然0，完整必要source段/原v03/材料快照/停止Gap已读；93b5b0/0仅自有stdlib diff/AST/pin，不重跑作者工具或测试。此轮没有定位失败、原live重启或环境扫描。原120失败/截断/停止Finding、原各阶段owner失败和旧测试红完整保留。

三个具体源码修复支持与新增来源缺口分列；真实DB/rollback/并发、合法权限/issuer/native资源注册、实际ASR/CTC/完整method观察、原两独立authority、音视频看听、API/MCP、安装三平台与商业均NOT_RUN。本轮不能授第四原目标、RuntimeBinding、发行、Gate或R1/R2完成。完整R1验收后连续R2目标保持。
