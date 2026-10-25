# RV20 — B11/W11/I23 固定源码分片评审

**SOURCE_REVIEW_ONLY / FINAL。发现4项静态接缝缺陷：2项P1、2项P2，均未实跑。实际Binding、测试准入、运行/安装/收费/发布及产品通过全部未批准。** 本轮不读T18/I22 WIP、不要求其停写，不签Gate/R1/precision authority。原68 planned标准、RV19局部关闭、原红绿和全目标R1三OS→连续R2保持。

## 固定输入及独立身份核验

| 固定材料 | SHA-256 |
| --- | --- |
| B11 Handoff Markdown | fd80f1825b96d633958447be99bf07b199294daecb58ba1ffe2d517ee88fdd52 |
| B11 Handoff JSON | 4feed82acfc5abaf7f35fe9540fe8c1330cc910835f15fd7f1e96fe878de30a1 |
| B11 SourceSnapshot | b7480629f8cb74d4d6f8783996bd96afbf46d995e6375413e35c01081776cba7 |
| B11 ServiceConsumption | c45213959bbcc7d92c35d6e7e18d7fe0583754aabfc2ed68bbc2da0e348aa982 |
| W11 Handoff Markdown | 43686593e0f8683c7c034b8dca1abb2c42a7d80a58ea1c2444f8d2198b3a58cf |
| W11 Handoff JSON | df244a1cb4f4554103d4642aa42910ac330cb71351c41aca5f720828e4aa9644 |
| W11 SourceSnapshot | 7cea7d612e0ab27e105aba4070c4e47d62ea2e417d37b7f94d33eecdf17262bd |
| W11 FactoryConsumption | f46176340b97d11c45c35be79d0dba8d89e936861e28c4b9b08d60a4c5ad6189 |
| I23 Handoff Markdown | f972a8e2d4bc10818513c66f40e28ccaeae8badb329aa716050499dac9329b65 |
| I23 Handoff JSON | 712593ece1cd28e7794786fefc083929b97f4af4fafb5e052fe5094ddde8a3e8 |
| I23 ResourceFreeze | 6736985e1af011e1a1697df221ace1a514223ceffad1e76fcef05680e5d53162 |
| I23 DistributionState | cb917b718a1ba9bb7343be6526cdd1a3425f60f30e9863f4f593ca270dbee781 |
| I23 ResourceManifest | 75a6c4445dd829f65662414cec785040bece2493d2f62de5d22ea2abb6727fb3 |
| I23 RuntimeFileManifest | dd8b9d764ee208cf4ef3a05fb9e75b48ec458068a3c35d00392f33836c6bd649 |

已独立核B11 15生产文件与15正文副本、31支撑身份、W11五文件与五副本，全部匹配正式身份。I23五份Code与W11匹配；索引实际解析为4633条、990451215逻辑字节。没有独立重哈希全部4633实际资源，也没有调用loader或证明完整engine闭包。全部固定源码正文、文档及每份完整SHA保存在自身RV20Snapshot，不借根核验代替本轮核验。

关键代码固定SHA：W11 bundle_producer fe1153c3608626429d7ef8e202f8640f4a62e6354823cb0566c29f3d5cac42c1；bundle_v03 93d4ed63287bf92f7213ee4a8586c3928f871c17beae15d8ddc1398dd2580e09；B11 bundles fa4e26de0833bb4bee4cb3e41a38e0cd955beb1bc85db8de54812689f4b0ca69；evidence 47c265be2425ce26ba1688f0e8b90514e1982741353a278c04ea65ed3bee6942；contracts 1e71f1cc42c4a1acf7444134ad5b29b08a9ddce6fabebd1a0fe4d1637594d25a。

## RV20-P01 — 合法无本片参考被runtime source_gaps挡住（P1，Media，OPEN）

源码：bundle_v03.py:173、190；[bundle_producer.py:279](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:279)；[bundles.py:1536](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/application/bundles.py:1536)。这些路径均指上述固定身份；后续新源不能倒填本结论。

触发：显式0.3 qualified_method_runtime_v1、真实有效方法资格、完整成功settled ASR、全部runtime检查通过，合法没有本片独立reference。finish_v03_evidence每次无条件把“本片没有独立P95，除非提供reference”写入WorkAlignmentValidationReport.source_gaps（190行）；即使提供reference亦如此。produce_bundle先调用verify_alignment_evidence（279–282），后端_validate_work_runtime只要source_gaps非空就在1536–1537抛work_validation_incomplete。

因此实际可合法未测的per-work scope被当作未完成runtime gap，所有本factory生成的0.3报告均不能过这道校验。与是否真实存在资格/参考无关；这是源码必经条件推演，**不是已运行产品失败**。当前P01挡在后续终验之前，P02—P04仍是各自独立的下游结构缺口。

Media修复：把“不声称本片P95”的准确限制留在对应PrecisionAssessment/方法说明；WorkValidation.source_gaps仅保真正尚未解决的runtime证据缺项。不得清空真实缺资源/检查失败或借benchmark伪造测量。Test未来固定新源后分别验证合法无参考、合法实参考及真正runtime gap仍拒；本轮不执行这些测试。

## RV20-P02 — 真实权利完备仍因quality固定not_measured拒绝（P1，Media，OPEN）

源码：[bundle_producer.py:200](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:200)–204，bundle_v03.py:165–167、217–222；[bundles.py:1819](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/application/bundles.py:1819)–1836。

触发：在P01等前置条件可通过的场景，具有实际匹配的Owner审核权利声明或真实可信rights authority/许可闭包。Producer仍把rights固定为not_measured；finish_v03_evidence只将alignment设verified，最终quality保留未测rights。后端1819–1821先要求七项检查（含rights）都verified，否则bundle_quality_incomplete；实际rights_authority/Owner声明核验在1822之后。于是当前工厂无法仅靠提供真实完备权利资料形成可释放quality，后端也不会修改已定稿不可变报告。

Media应按真实权利核验事实、原批准版本与许可文件来源生成quality的状态及引用，不凭模型/自产callback翻为True。现有user_asserted可消费真实审批和完全相等原声明；licensed/owned若媒体端尚无合法核验事实读取，应由Backend另交普通当前lease下受控权利证据端口。Backend最终expiry/原批准/许可/authority守卫保持，root与Review不代签权利。单纯降低七检查门或预填verified不算修复。

## RV20-P03 — correction读取原件后未进入新交付闭包（P2，Media，OPEN）

源码：bundle_v03.py:92–93、106–115、150–152、202–213；[bundle_producer.py:241](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:241)–256；[bundles.py:400](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/application/bundles.py:400)–418、1181–1202。

触发：调用者交真实可读、同owner/project的CorrectionOriginRef及reason，全部reference/原件身份合法。prepare_v03_evidence调用correction_origin取得原byte后将返回值丢弃；documents/slots/receipts没有历史precision report。source_documents仅准audit_summary，不能隐含携precision_evaluation原件。完整artifact构造仅索引四媒体和现有documents的receipts，measurement依赖也只有reference/transcript，不含origin.artifact_id。

后端_correction_closure要求旧报告真实索引material、精确文件SHA/typed旧grammar和report→origin forward依赖（1188–1195）；故修订分支仍correction_origin_unavailable。这是读过完整artifact构造后的静态推演，未执行修订包。

Media需保取得的不可变原byte，以新交付Allocation/stage/Receipt索引原artifact_id及正确版本grammar，measurement显式保forward依赖/许可来源，完整文件SHA与内部记录身份不改。原material_id是源定位，不要求复用为新交付material；不能改旧报告、让未知普通payload选择旧grammar或删Backend闭包校验。Backend当前真实源读取/类型/同主体及文件完整性守卫保留。

## RV20-P04 — 有到期权利时RAG未携有效期（P2，Media，OPEN）

源码：[bundle_producer.py:196](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/workflows/bundle_producer.py:196)–199；[bundles.py:1816](G:/开发测试/Projects/VideoCreator/services/engine/src/video_creator/application/bundles.py:1816)–1818。

触发：使用实际获准、尚未过期且expires_at_us为未来时间的right。所有自产speech RagChunk只填rights_ref，valid_until_us沿DTO默认为None；后端要求期限存在且不晚于父权利expires_at_us，因而rag_rights_invalid。尚未实跑；此问题不涉及永久权利，也不授Portal延长权利。

Media按实际所引用权利有效期填写不晚于它的chunk有效期，保源权利ID、实际使用目的/取得限制；未知许可继续阻断，不能删expires_at_us或放宽Backend门。Test未来核有期限/永久/已过期/超父期限四分支。

## 本轮可支持的静态机制范围

这不是全源码/全场景通过，仅对已读具体链作如下记录：

- 显式0.3模型和旧版本分派（contracts1317、1594）；无测量N/P95/reference/locator/criterion全null（1323–1343）。新请求固定预授权policy；已有key复用原固定policy，不改旧版本hash（engine162–241），缺准入持久waiting_user。未获准词级降级仍拒。
- Registry空root默认拒；admin按in-process对象身份核，不注册普通API/MCP安装口。安装核完整benchmark/HMAC批准/期限；当前外部撤销floor不允许旧快照倒退（evidence52–183、292–392）。参考许可和HMAC只是声明认证，实际监听/裁决正文、完整单位与独立scope要另核（185–290），本轮未提供真实authority。
- publish在同BEGIN IMMEDIATE中重核policy及参考当前撤销/expiry、普通lease/fence、全部Operation/revision和文件身份（bundles580–627；database156–167）。这是静态调用次序，未验证并发或故障。
- 全segments/words顺序、数量、原text及strict整数时码与成功settled ASR原事实逐项比较（bundles104–123、1497–1556）。Worker实际child记录OS/device/compute/model/resource/config（asr_worker215–239），Driver核其字段/指纹（local_asr219–269）。不由宿主或qualification补造child身份。
- max双端误差、全N、nearest-rank和200000us保留，原列表重复/范围先拒（alignment_math14–50）；Allocation/ready Receipt与无环前向组装分开。Correction闭包本身已强化，媒体缺口见P03。
- Driver仅owned_local/transcription且无secret可执行，cleanup未证实返回unknown（local_asr450–464）；Producer非成功观察在普通lease读取或重交前停止（producer105–110）。未独立跑cancel/unknown/tree处理。
- 新B11固定源现含六consumer完整位置参数签名：content712/semantic_page720/request_export807/export_status864/import_status1066/import_bundle1350。只说明在新fa4e身份中已发布；不倒证旧B9，也不批准活跃T18 adapter绑定/行为。

## I23资源、ADR与准入未测

已读固定ADR0015 869d8943f092c2f169353b2550264d416a61506b58ef02083c3f2b417d6b28ff、0016 a517af8c75e3b58381c895d2069de96216b3b5985b727d840ee9e330ca109a26、0017 31265c04fee71ed285e25f3b941b96eba8cdf56c129ca3d8bd2cc1eda733f992、0019 b35286493eba171bf368f183d069d7ea7dddd867b1d9802000a6d976e79c450c。ADR19替代renderer token/direct-fetch设计；本轮不评活跃Rust/SDK或新Binding，已有native CORS/空窗/owner CLI探针不代表broker/Worker后台完成。

I23仅Windows ASR资源身份候选，Code未含完整领域/服务/factory依赖。Owner声称完整loader在initial/moved只校验索引且自然close0，没有模型加载/转写；本轮未调用loader。W11原首ASR失败、额外唯一identity成功及有限domain/syntax记录是owner观察，不能继承为实际业务Permit/full Bundle/precision authority或新I23资格。新resource/config不能借ed9add96旧配置准入。

发行缺项明确：PyAV23 DLL精确构建/对应源码、CPython基座完整来源与第三方声明、模型原revision/转换、FFmpeg GPL对应源码/NOTICE、CRT具体版本/权利/干净机闭包、EXE/DMG/Linux/三OS仍pending。完整embedded_full_report可信可披露许可端口未定，现只有provenance_reference；不删完整目标。

T18实际标准/前置正文/独立Binding、完整producer/resource/父包及正式factory尚未交本片，运行准入保持pending。真实听审/基准/issuer、local qualification、完整八输出、修订正向、API/MCP/native/三OS/MM05均未验收。四缺陷先交Media原owner；Backend仅负责必要受控权利端口及保留校验，Test独立冻结用例实跑，Review不兼角色。

所有本轮读取终态，无live。Reviewer产品import/测试/解码/网络/安装/fee/key为0。仅读已分派固定源码及过程普通材料，无T18/I22 WIP，无生产freeze。自身路径列表首script误将目录交Get-FileHash而exit1，已纠正并在Snapshot保留工具限制，不是产品红或测试重跑。SOURCE_REVIEW_ONLY正式交接后释放。
