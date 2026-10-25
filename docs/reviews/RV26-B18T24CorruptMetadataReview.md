# RV26：B18 / T24 存储 JSON 损坏接缝独立复审

状态：FINAL。**RV25-P01 在固定 B18 版本的存储 JSON 类型/UTF-8、候选选择和损坏错误分类窄范围关闭。**这不证明 HTTP500修复已由HTTP请求验证，也不批准 published/imported Bundle、合法权利、完整授权/文件链、native、RuntimeBinding、Gate0/R1/R2。

Review 只读固定普通源/原始证据，未运行产品、测试、SQL、ASR、模型、网络、密钥或收费，未读取 B17/W15/Integration 当前WIP。完整R1三OS独立验收后连续R2目标不变。RV26卡仍有历史“当前未分派”，本轮依统筹直接新分派执行；状态同步归统筹。

## 精确版本与证据

| 对象 | SHA-256 |
| --- | --- |
| 原RV25-P01 Finding | 3cdd687e626a120d4445064b88cf7dcfed9873b3cf01d5a33729ef13ffa790d1 |
| B16 helper原件 | 166e08bcfd1aeccce0d8711d5e0e62dfd890c0dc367bf241363b4cb8f462cf42 |
| B18 helper固定修订 | fe8f9049a02002ea4a7a110d400cb2891e8486235cba235581dda43b13eedc5e |
| B18Handoff.md | 3d94a7d079336eb1825a865eb563a6c204cc7d66ac500f162dd0714a2233572d |
| B18Handoff.json | aa7db891649da4498459e5c1f7ea49cff2672eb7fe62f1f8385b47c362a345ac |
| B18SourceSnapshot.json | ebd4e141107345275ddd4dd10cd322254a6062aba6b78efc95afa59263e2c858 |
| B18Exact.diff | 057623967d0e9b5235c56a168576dd6320cf8193eb70c46c7567c2ae897fdb19 |
| T24Handoff.md / json | a2f7af0404374f2b2ec6db931c0e2b730411a5cfc8e2a3f97fe0f4ac1067a552 / 4f78cc32935e4898b39e680b7136b1554cc8aa3376752865909378056af10757 |
| T24FinalSnapshot | 34161101fee14b4a9cf88996c1cfcb74a632962e6c0e9d6d5dea4da68f17d751 |
| T24OrdinaryCopyManifest | 34a3dedc33b349e3ac12ed81d74b36600d7c23644a1f21c309a64ed9db8aeeae |
| Boundary CommandReceipt | 8720260a9389ddbd318846fc12626fb474b70936ef0f716ae17ffd601ce73efd |

B18 37正式ordinary源、T24 139ordinary副本及显式映射的1232原预运行依赖/解释器归档逐文件身份匹配。1232为233依赖+999解释器；不把归档计数当1232运行用例。1311实际前后输入记录SHA均为f5c32cc7d893dec38e8cc196d49f57e12ad5cb70ee53b2abdf14308d2e26f529、字段数均1311，变化为空。全部路径/完整SHA在 [RV26InputPins.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/CorruptMetadata-RV26/RV26InputPins.json)，相干原件和事实在Snapshot/Facts；没有用现活生产源补旧身份。

## 修复为何足以关闭原窄问题

固定 [B18普通源 _json 67–75](G:/开发测试/Codex/VideoCreatorImplementation/Backend/CorruptMetadataBoundary-B18/FinalSourceCopies/services/engine/src/video_creator/application/delivery_metadata.py:67)只新增非str→EngineError bundle_text_invalid422，以及显式strict UTF-8编码/UnicodeError→同类错误；之后仍调用原strict_json。Review对T24的B16/B18完整helper正文执行精确文本差异比对，只有这段改变，候选选择、权限、scope、原目的、API/DTO/DB没有跟着改。

因此原_grant对EngineError的damaged候选处理可到达：坏BLOB不再作为bytes.encode AttributeError跳出整个遍历；完整有效替代仍选最长expiry单条，平手ID升序，没有权限并集。无有效替代仍bundle_grant_invalid422。_manifest、import _node和export _scope原catch分别保持bundle_integrity_failed422、import_binding_invalid422、export_integrity_failed422。没有宽捕所有Exception、修SQL行/原body、补null或变更grant资格。

仅这类已返回为Python值的存储 JSON gate和具体调用分支得到支持；不外推DB驱动读层异常、任意损坏数据库恢复、完整文件/row/grant竞态或HTTP错误映射均已验证。

## 独立测试实际做了什么

固定 [ProbeT24.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T24CorruptMetadata/TestAndPins/ProbeT24.py:60)，SHA19104cf4e409350f1dba1832ec967c8d904241168e5177c556935610f0201027：60–82从预运行普通原件加载完整DeliveryResolver类、真实contracts/domain/error模块和实际Pydantic2.12.5/core2.41.5；并没有执行完整_resolve主链。

44–57/73–76仅用原AST函数体隔离engine.canonical、engine.digest、bundles.strict_json。两版Events各保存抽取正文和源SHA；Review逐正文比对与完整固定原件相同，且globals为原json/hashlib/BaseModel与原json/math/c/EngineError，没有替换为较宽parser或假的DTO/错误类型。三个支持函数共六次版本核对均匹配。这是透明局部隔离，不构成EngineService/BundleService整体运行。

85–113 FaultDatabase是真SQLite连接/Row与真实SQL查询；表是专用故障候选表，没有published Bundle/preparation/rights/authority。149–167用真实BundleReferenceGrant/BundleRef验证模型、插入故障数据后实际调用_grant，serialize前后相等断言证明selector没有修记录。合法模型候选是故障夹具，不能被命名为真实发布或法律授权正向。

169–189原四方法断言同一源码用于两版，仅main298–301给B16选择这四项；B18运行全部11项。SQL BLOB先/后于有效候选、无替代、manifest损坏的原期望未放宽。附加七项覆盖真实typeof/blob/int/null/text及直接memoryview/bytearray/bool/float、strict JSON/重复/nonfinite/指数溢出/secret/UTF-8、导入坏mapping及缺mapping503、export坏journal及隐藏actor404、expiry/purpose/recipient/latest-ID tie、row/body及DTO坏候选与替代、single完整T及semantic。_manifest/_node/_scope只执行损坏前缀，未跑合法origin/content/registration/asset/closure或ready archive。

## 原红、新绿、退出分层

[原B16 JUnit](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T24CorruptMetadata/Evidence/BoundaryRoundOne/B16/JUnit.xml)，SHA9e3ae8fa77fcdff9f3632c6e53c65f6b25b9699e12b63ddb93041a745fc5fde5：4 tests、0 failure、**4 errors**、0skip。四条原错误正文都明确AttributeError: bytes没有encode。原红保留，不能改写成四断言绿。

[B18 JUnit](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T24CorruptMetadata/Evidence/BoundaryRoundOne/B18/JUnit.xml)，SHA532d7d894b741b1c3b653cc7b4c72ae04ad5ff4e12800c0c0563f96acbee6ca5：11 tests、0 failure/error/skip。原四项加七项均通过。

[RunT24.py](G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T24CorruptMetadata/TestAndPins/RunT24.py:56)，SHA7139ce7a76efccfc1cbec58c24c842dc7ce0b81ea5c7a639b7ba5045baf53c30，真实Popen句柄/creation时间、原stdout/stderr和wait退出分别记录；forced会失败，旧证据目录存在拒盲重跑。实际f1008d/session64632→06ed76：B16 PID47716自然1、B18 PID12504自然0，两者forced=false/terminal=true；Launcher PID25592外层0只表示保留的Before红与After绿符合预期，不能洗成B16 exit0。

层次时间分别为：B16四case合计1.3850374s、子进程wall2.0418267s；B18十一case合计4.3028354s、子进程wall4.9327217s，不把suite与全过程混用。1311固定输入前后无变化。实际physical CPython3.13.16以及-I/-S/-B/-X utf8参数属于本局部测试身份，不授root.venv或完整App闭包资格。

原准备83dc58错用早期B16快照、38f5d0旧解释器junction拒绝及两次猜路径读错误保留；第三准备使用最终055b2abb与物理解释器的新目录，bc57d5→569f71自然0。未把没有产品import的准备失败当产品红。finalizer2bd2cd自然0与普通复制收尾明确在TerminalReceipt单独记录，不覆盖原runtime receipts。

## 关闭与后续边界

RV25-P01的原代码错误及具体损坏分类/替代候选阻断已由固定源窄改、真实局部SQL/DTO测试和原红→新绿支持，**CLOSED_IN_NARROW_STORED_JSON_SELECTOR_CLASSIFICATION_SCOPE**。原HTTP500风险未以真实HTTP请求复现，这里只关闭其原异常来源与上述分支，不为HTTP Envelope或真实Bundle资格签票。

HTTP/API status与Envelope、全Engine/BundleService、current注册/许可/Asset/ready/原Manifest与origin、共同T/V许可闭包和字节后最终时刻、合法publish/import/export archive、native三OS、原68业务、Gate0/R1/R2仍未通过本批。独立Test/Acceptance另按具体固定源码/准入资源执行；现B17/I27/后续ASR不继承本批通过身份。没有新阻断Finding，本报告不修实现/测试/标准。

全部source/证据reader与工具在交接送达时终态，live handles=[]；Review仅写docs/reviews与Review/CorruptMetadata-RV26，UTF-8 LF。正式Handoff包含Report/Snapshot/Facts/InputPins SHA。本有限评审完成即释放，不等待后续运行。
