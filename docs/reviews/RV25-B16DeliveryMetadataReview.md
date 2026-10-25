# RV25：B16 交付内容与元数据共享解析独立评审

状态：FINAL，SOURCE_REVIEW_ONLY。一项 P2（RV25-P01）OPEN，归唯一 Backend writer。有限固定源码/声明审查结束；不批准 RuntimeBinding、业务运行、资格、Gate/R1/R2 通过。Review 未运行产品/测试/SQL/ASR/模型，网络/密钥/费用0；未读取未来 B17 或 Integration/Test WIP。完整 R1 三OS独立验收后连续 R2、实例持有数据与五步前台保持。

## 身份与覆盖

37份 B16 FinalSourceCopies、18份固定证据、7份正式文档、2份历史 before 共64输入，开始/结束 SHA 全部一致。完整绝对路径、完整 SHA 与结束比对见 [RV25InputPins.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/DeliveryMetadata-RV25/RV25InputPins.json)。相干正文与证据已保存 [RV25Snapshot.json](G:/开发测试/Codex/VideoCreatorImplementation/Review/DeliveryMetadata-RV25/RV25Snapshot.json)；存档不等于全部37支持源都重新做了语义审计。

| 固定对象 | SHA-256 |
| --- | --- |
| B16Handoff.md | a1f2e95288810de52a5150dde290c348e541fd6d55e7c509741af179230cca2e |
| B16Handoff.json | 290a7038804d85a10d333bf1ce7bb0f68bd3536951c7de214520b5a5516d81bf |
| B16Consumption.md | e3ce590207546afcd2c3f5df7e6c42643c95dbd0790104e507da42cb5fd10f3f |
| B16SourceSnapshot.json | 055b2abbd50a74430954f0cb53c3881c33d00bd643a0fd58356be7e3de4e4a1b |
| application/delivery_metadata.py | 166e08bcfd1aeccce0d8711d5e0e62dfd890c0dc367bf241363b4cb8f462cf42 |
| application/bundles.py | 29dd59c163b3e77eca1ff70b9eef4fedcd286e2b38cd62c4eb66a88a35ff22ab |
| api/app.py | c240e74e05d98b04b0d37b189ef2690767a71e794770dbb38d60155d8f0655dc |
| api/transport_contract.py | 38bbf206fd5d99495d425e8e3a0488e8738554212f11165b736d1cd11caf5a53 |
| domain/contracts.py | 5838b2fde85e2ba752d60a98f017390651c14a4e254a81bc4d02767065287f6a |
| ADR0021 | e1c3b3eca9debdc8c84caf721c3f5dcbe570b3f7d690ff3991dc26ee97605987 |
| ADR0022 | ee035a815b061096ad7241d0aaad63806020b706de09c82eb841145b4ea19549 |

下面源码链接均指 B16 固定普通副本，不能用后续生产修订倒填本批。

## RV25-P01：P2，SQLite 非文本 JSON 事实逃出损坏分类

完整早期问题片：[RV25-P01-Finding.md](G:/开发测试/Codex/VideoCreatorImplementation/Review/DeliveryMetadata-RV25/RV25-P01-Finding.md)，SHA3cdd687e626a120d4445064b88cf7dcfed9873b3cf01d5a33729ef13ffa790d1。静态结论，未实跑 SQL/HTTP500，未构造合法 Bundle/grant 资格。

[DeliveryResolver._json 67–69](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/src/video_creator/application/delivery_metadata.py:67) 直接 value.encode()；_grant116–140遍历全部当前候选，120–132只捕 EngineError/ValueError/TypeError/KeyError。非str的SQLite BLOB以bytes返回，没有encode，因此是未分类AttributeError，而不是damaged候选继续。

固定 [0004_bundles.sql 27–31](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/migrations/0004_bundles.sql:27)，SHA17a6895236819fd13add2fad290ecceaae027e113e36dfcd828d0c097132a6f0，只声明body TEXT NOT NULL，没有STRICT/typeof约束。固定 [Database.connect 149–154](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/src/video_creator/infrastructure/database.py:149)，SHA353b507fc4f95578c9e96773dd6c5b54f8cfa219f3a956e7a69e77783e408031，没有自定义text_factory/类型转换。正常create_grant写canonical文本；本反例限定已损坏/异常旧存储类型，不能说普通API能提交BLOB。

最小触发：真实当前published Bundle及actor/operation/project合法、存在同SQL谓词下一个body为BLOB的坏候选（例如非JSON正文），另有完整合法一致的活跃替代。循环不早退，坏行在有效行前后都能抛出，妨碍ADR0022 44–50批准的any完整候选。无有效替代时，也应以422损坏证据拒绝，而不是无约定异常。

resolve334–335同样不捕AttributeError；[API122–125](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/src/video_creator/api/app.py:122)只将EngineError映射为ErrorEnvelope。由源码可确认异常逃出既定分类；默认HTTP500是待独立复现的影响，不冒称已测500。

相干可达边界分别保留：
- 当前可见published/local-import行的manifest_json存储为BLOB：_manifest78→_json，83和外层均漏分类，原索引损坏不能保证422。
- 已有合法可解析索引及本机导入行的mapping_json为BLOB：_node274→_json，276只捕EngineError；scope.identity存原值不等于类型验证，坏映射不能生成ready metadata。
- journal owner/registration已匹配但request_json为BLOB：_scope200→_json，201漏分类；原用途不能被坏journal异常替换。
这些均不证明可越权读取或产生ready结果。合法历史BLOB/文本兼容是否需要支持，由Backend按原合法事实明确处理；不能靠TEXT affinity自证所有取值均为str。

整改：共享入口显式处理存储类型/原编码/原字节身份，维护严格JSON与损坏错误。坏grant候选记damaged并继续，完整有效替代照常选择；无替代损坏422，manifest/mapping/journal损坏422。不要宽吞所有Exception、补null、忽略原body/hash或改授权/旧数据库记录换绿。Backend修自身白名单；独立Test另批以真实准入范围核BLOB前后顺序、无替代及相关存储边界，本轮不授运行。

## 相干源码安排与剩余运行验证

[DeliveryResolver98–269](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/src/video_creator/application/delivery_metadata.py:98)先核当前_actor、原owner/project隐藏及published本机来源。grant不合并：133要求完整T、purpose和semantic，140选最晚expiry单条，平手grant_id升序；一般解析坏body已设计为damaged后继续，但P01的非文本类型不在该捕获范围。row/body ID、recipient、ref/project、expiry、revoked/created时间均在122–128比较；DB撤销事实优先，不用revoke返回体替原body。

143–187从原列表查重后建立artifact/right索引，显式visiting/visited遍历artifact dependency与right license引用联合图。共享DAG不反复验证，自指/缺引用/联合循环拒422。对外T与内部V分开；250–258只给T施加请求UsePurpose，V全部核有效边界。许可文件作为内部证明不会被强加playback等leaf用途，也不因此公开其节点、grant或路径。非空permitted_uses/合法时间由原RightsSnapshot模型继续约束；读取不新增prepared authority，也不证明法律所有权。

271–320核真实本机ready bundle_items或import映射、AssetRecord SHA/size/MIME及受控路径；许可节点必须roles=(license,)、controlled Material、kind=license/text/plain。322–362流式全hash在短DB连接外，license正文再走原固定validate_text grammar。370再次调用_scope，以真实新clock重新解析当前registration、scope、原row/journal、T/V、rights及当前grants；允许换到另一完整有效替代。371–381校原immutable identity/T/V/edges及ready binding、path/stat；54–59以最终registration/chosen grant/V rights的min生成期限，没有虚构grant。null只在适用声明均已知无期限时产生。仍存在检查后文件或撤销墙钟窗口，不能把这些stat检查称为完全消除并发竞态、持有OS文件句柄或冻结权限。

whole Manifest使用全部artifacts/semantic=true/operation=bundle.read的一个完整grant，不拼leaf权限；leaf走独立facts，不调公开whole-Manifest端口。[BundleService1212–1264](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/src/video_creator/application/bundles.py:1212)分别消费同一个resolver；semantic_page1269–1274仍有原bundle.semantic检查并另调用content的bundle.content检查。

导入_scope按本机owner/project/current principal与本机mapping，不借origin grant；reference只绑定原来源。原import1938–1983先完成全部内容/本机Asset或Material映射、写原Manifest、核archive全hash，再在有checkpoint的最终事务插入bundle_imports并返回receipt。DB index_state默认not_built是后续索引状态，不是导入文件尚未ready；本轮没有因它不为ready误报。损坏/缺mapping与变化后的bytes/locator仍需实际负例。

导出193–228固定原journal的owner/registration/request.purpose/profile/selector/input SHA，使用原_selection的真实携带闭包为公开T；内部V不能替被携带许可的公开用途/grant。259–267及355–382仍要求ready archive、原journal/version/bytes与最终身份。不得以query切purpose或重提交export。源码等价范围需独立实测原两步权限、projection/full、import-origin、坏journal、ready→非ready、撤销/到期与文件变更。

## API、DTO与声明的实际关系

[DeliveryContentMetadata585–614](G:/开发测试/Codex/VideoCreatorImplementation/Backend/DeliveryMetadata-B16/FinalSourceCopies/services/engine/src/video_creator/domain/contracts.py:585)是唯一闭集模型，version0.1.0-candidate，六discriminator locator，size/time严格整数，authorization_expires_at_us显式必填且可null；local BundleRef的instance必须为local_instance_id，import origin身份保留。purpose kind与locator绑定，非null期限必须晚于checked_at。没有grant/私有path/Bearer/法律资格字段。

API247–280让Asset metadata和content调用同一actual_asset核真实完整字节；Asset为installation owner而非delegated读取。五Bundle metadata和对应content都消费同源facts。API254–261防御getattr仍存在；299/331/357/367四callsite仍用它，309单leaf才是直接方法调用。五真实方法已存在，原stage503只在方法确实缺失时触发，不是假全部守卫被删或全部永久503。

metadata_input240–245拒未声明/重复query、body、Range及条件；未知UsePurpose仍经原DTO422。Host/Origin/Bearer/current principal在原依赖中检查；EngineError有原唯一Envelope，404隐藏、403用途/许可、401注册失效、409阶段、422损坏、503真实缺资源的原边界保留。P01例外不能被声明文档补绿。protected_file282–287在真实facts后才304/FileResponse；源码显式写quoted全SHA ETag，206长度不当完整文件大小，Asset没有304支持。

transport_contract48–94由真实函数装饰绑定实际APIRoute/OpenAPI，闭合GET/schema/path/query/default；182–207从同内容函数继承真实authorization。固定actual OpenAPI（SHA1606ba21d00d75e3e8fe669806cab0fec9b4aeabf14d8883b92a2fa9f27ba8cd）独立JSON比对确认37唯一operation、37transport声明、34path、77component、6一一关系，目标GET/单schema/security/authorization/同名参数一致。schemas SHA1604f3d8f1a4dba13a1f72985e41d1c323b97dca8d841fe913e52e2c4a08565a与owner129模型声明固定。详见RV25FactsCheck.json。这是声明与源码阅读，SDK/NativeManifest再生与native/端到端消费未执行。

## 原权限方法、批准范围及历史失败

NarrowScopeReceipt SHA2c0b44737c7e43687936e14afdefb0727e6efc962714a40576e5883198d154a6报告17 unchanged AST方法。本轮从SourceGapCopies/bundles.py SHA824b6d4e7a0813f8254c25986d669a6fa8d09ee1b380880d21a3daa87ba7edd6到正式源逐项独立比较原方法正文，17全部相同，包括_actor/_visible/_rights、grant/revoke、export request/journal/scope/acquire/build、import/visible/export、verify/publish/rights/correction。Review没有运行AST工具。原方法没改不等于新caller继承全部约束，尤其export_content不再直接调用_export_scope，所以上述相干链仍需独立读与运行；该凭据不能代许可通过。

两项组合补丁自动审核拒绝按原证据保留：RejectedBundledResolver.patch SHA4a77db1ba961a44776b58188e1a3fd0e991f2d0aed807c3b024a7f3bf704efc9；RejectedApiCleanup.patch SHAe7a3e300bf399fc07a6cdba5155daec909325bb42e113fb4f0dea5d2451de119。原因分别为整体替换内容授权链、同时激活五metadata的宽敏感范围缺精确准入。未把被拒提案当已应用：全局_resolved_content提取不在实际源；五API guard清理未整批落地。ApprovalScope及Addendum记录后续同apply_patch对local leaf/Manifest、import leaf/Manifest、原export journal逐链接受；实际Accepted-bundles.diff（SHAded89f86e6a5dd8b945d8f1ceae3f721a64c3b1553c8505f025cf553a3b56a2d）与最终源码相干。app阶段before SHA04c44f8b0ee04ec618a0a8c0a276f27a79264eb2069875d6bd599a337c6faa0b到正式源差异仅单leaf调用（Accepted-app.diff SHA47c622a98f2807c87fabe8e3d6b5076e0b4738c5b63db2d67ff7f4a1ef570a92）。这些是固定源码/owner过程证据，不是Review补授审批或运行权。

原不存在tools/export-contracts路径读取、stage Ruff、fb7420 red、复合shell0中实际Ruff I001、PowerShell brace路径读1、两auto-review拒绝均保持；后续窄Ruff/AST0只覆盖对应新源。schema首次文件名检查只看engine.sqlite3，不能证实际Metadata.sqlite；原记录未覆盖，后续固定SchemaDatabaseObservationReceipt仅观察输出两JSON、无实际DB/sidecar，不重跑export。B12两轮owner红仍由原RV24固定范围保留，不在本轮重审或洗掉。

## owner运行证据与待补

RuntimeCommandReceipt SHA87b3e4f58b0ce2727fbeb0b2633464fe13b4824fd0974f44448e87d4748908e6记录唯一owner argv为root .venv Python+固定RuntimeProbe.py，8c2d25实际exit0/5.5059983s。RuntimeProbeReceipt SHA38466879318a5754f4a28ebf0b3a2efead1c093e116f27f5a219a5e24150b82a：actual PID23864/parent29540，47 result=passed，Asset1；operations/productions/runs/Bundle/export/import/grant全部0，source/dependency drift为空、export线程及新线程结束，原Starlette warning保留。

范围仅自产UTF8文本Asset staging/import201、metadata200/full200/Range206实际SHA/size/MIME、权限/Host/Origin/expiry/input拒绝、五Bundle-family缺ID404而非stage503、同长度Object篡改422/缺文件503及清理。没有published/imported Bundle阳性、替代grant、V license/cycle/expiry、final-clock/revocation或archive成功；TestClient不是TCP/Windows Job/native生命周期通过。SchemaExportCommandReceipt SHA9a47d9630f059b099fb998adebc981178bfb717177fc8f5a09e2db499ee748ff仅一次CLI schema/export exit0，43 JSON检查仅声明。这些owner证据不代独立Test/Acceptance，本轮未重跑。

后续独立Test/Acceptance按原标准与真实准入范围覆盖P01、leaf-only vs whole Manifest、坏候选与有效替代/重选、单grant不拼权、proof-only用途、联合循环/损坏/时间边界、初末registration/grant/ready/identity变化、non-playback import/origin、本机完整映射、journal/selection/archive、条件Range/304、save commit重核与native/三OS。禁止以Mock/AST、owner缺ID拒绝或许可字段构造当完整阳性。精度/真实权利/模型与商业资格仍各自待证。

## 终态

源读取已释放，64固定输入after身份0差异；所有工具在交接送达时已终态，live handles=[]。Review只读JSON比较脚本c3528c的Select-Object逗号笔误exit1由同快照be7e29改正并记录，不当产品红或重跑业务。仅写本报告与Review/DeliveryMetadata-RV25，UTF-8 LF。正式交接带Report/Snapshot/Facts/InputPins完整SHA，P01仍OPEN，归Backend后续批，Review不修源、不放宽标准、不签运行。
