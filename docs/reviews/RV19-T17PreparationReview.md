# RV19 — T17 第1轮准备整改与标准修订2复审

**批准精确版本的 criterion revision2、68项计划及有限纯准备机制；RV18-P01仅在本轮固定源码的前置校验/后置构造顺序范围局部关闭。真实运行准入、完整0.3 bootstrap、六consumer ABI仍未就绪，不授launch或产品pass。** 这是最多三轮中的第1轮复审；原报告及红绿保留。Gate0→R1独立验收三OS与真实自动作品→连续R2不变。

## 固定版本与批准范围

| 对象 | SHA-256 | 判断 |
| --- | --- | --- |
| criterion revision2 JSON | 2f5203983e5c696ad6cb2ee89d81ed2bf7b5d51a31abbdfe5a6f6d9a576b85d2 | APPROVED_CRITERION_REVISION2_ONLY |
| criterion revision2 Markdown | 0242cd3fbbe3736f8cafd7635d03145f67cd93e0aeb41ca5cc2d215b8036796c | APPROVED_CRITERION_REVISION2_ONLY |
| T17CasePlanRevisionTwo | 81d3c522e72bcd117f5a65444d9a00b9e97b82150ed1dcb5970b4c1c53590a91 | APPROVED_PLANNED_COVERAGE_ONLY |
| t16_guard.py | 83147ff064c0d9bbde4eb229575c5b5c35e10c4f819029e947ebfb6cd8156661 | APPROVED_STATIC_PREPARATION_MECHANISM_ONLY |
| t16_business_adapter.py | 89f657566749f5693a91cac85844fdfe2fda63f8f8b5169648fe7bfa7bdadf9d | 同上；完整接口兼容与runtime未批准 |
| t17_reference_assertions.py | afe4209834f38e2bd9397f11dd6325a798762ad85fbc5c0191f1828d24bc069b | 仅grammar/full-unit/hash准备断言，不认证HMAC/authority |
| T17FixtureManifestRevisionTwo | c01769eb01924e93a0764bb1f2daa55a4a3f28bfaad9f19f7d873ae0b5e96a47 | 固定准备库存，不是实物/资格或可执行全包批准 |

正式T17 Handoff：JSON750210f82f92b68c9fd6e52ac2d6f9712971e532f1f617af5094d4a0caa4305a / Markdown2c0a3cb1fe734a6b850f4ac4b36d9c0d2017242dc4f36ab163095f1f6223164e。33普通副本全部匹配，copy manifest aa00fd61b0cbda0e02b6af478468aa7363539d131b8462a09daa2be6533d906f。仅读冻结Test/架构材料及自身旧Snapshot，不读B11/A14生产、不持freeze。

## RV18-P01：局部关闭静态顺序缺口

原P2的具体问题是：admit仅遍历admission自列项，BundleService目标是否归档在import后才检查。本轮代码已改变：

- guard第110–117行分别核admission与独立Binding的外部预期hash；第118–143行核批准标志、固定目标/source_root/criterion/隔离DataDir/零费用及prelaunch正文manifest，调用identity_preflight。
- identity_preflight第58–63行要求Binding的source/resource非空，并与admission全集精确相等；第64–78行要求目标及逐层package/__init__规范路径完整；第79–100行先核正文全集、逐项真实源/正文SHA及所有资源。
- ServiceAdapter第24–34行改收post-preflight bootstrap函数，admit先完成，函数来源/qualname须在已核正文闭包；第35–36行拒此前已import的producer，不接预构造service。第37–43行之后才逐层调用PathFinder.find_spec，提供显式父搜索路径；没有在preflight前调用通用find_spec来import未核parent。第46–49行才import与实际service构造。

因此，在**独立批准、外部固定且未由admission/caller自定缩小的Binding与预期pin**这一准入前提下，旧“目标/正文/资源未核就进入loader/import”的静态链已修正。状态为 CLOSED_STATIC_ORDER_AND_BOUND_CLOSURE_COMPARISON_ONLY；关闭不覆盖真实loader、完整依赖闭包或OS安全边界。

外部pin的可信来源不可由两个true标志、自改Binding再算hash或自造admission替代。identity_preflight是可直接调用的内部纯检查，参数本身不产生批准；admit_runtime接收的expected_binding_sha256/expected_admission_sha256必须来自另一次独立Review与root批准的精确固定记录，不能来自caller提交的同一材料。代码不会凭hash算法判断hash的授权来源。本轮未出现真实最终Binding/批准pin或bootstrap文件，故这项运行前提尚未实证，也未被本轮批准。后续必须先绑定完整生产/Test/包/资源正文及正式factory，再独立准入；不得把局部关闭解释为现在可以launch。

未发现需新增P级整改的静态顺序缺陷；不把未执行的动态边界写成真实通过。RV18-I01六consumer完整签名仍PENDING，不读未来B11来倒证旧B9。

## 标准修订2可批准的依据

原criterion1 JSON b3944783e8420ac742bfd55ea875d1f52109163efeef5c22fdb2f2ce72de2d20、Markdown340514bfd9fb8b5bb126056f3143fd16d1bf725cc516a5465e005a50e9f55048字节不变。revision2继承旧38和旧20的全部值及顺序，计划亦相同；原有共享字段仅candidate_revision/status随本次提案变化。原六断言主体字节不变。旧12相关字节、T16旧27普通副本均无mismatch，原6sanity与原红绿未覆盖。新10 criterion与计划逐值一致；68业务项均planned/not_run。

ADR0017 31265c04fee71ed285e25f3b941b96eba8cdf56c129ca3d8bd2cc1eda733f992与REF-01—10保持一致：reference/report/benchmark各自独立kind与精确版本/role分派，同scope不混grammar，不改旧0.2audit_summary/default/hash。参考须对应本run实际原音轨完整decode/sample/PTS和固定Transcript全量单位；原列表严格ID、唯一/范围/人口先核再map，不能从mix/源稿或调用方SHA冒原音轨。

listener/arbitration须可定位真实不可变正文、人员/工具与独立性及完整人口审查，单SHA或占位不够；issuer仅在实际获准scope/criterion/audio-work/listener范围签发并受当前expiry/revoke约束，不获得policy/方法资格或authority安装权。签名只是issuer对声明字节的认证，不证明听审独立性或ground truth，不能复制被评预测再自签。

三层输入/身份明确分开：签名canonical正文移除signature/content_sha256；内部content SHA移除自身而保留signature；readyReceipt/FileRef/Manifest使用完整实际文件字节SHA。单位、音轨、监听、issuer字段不删；纯helper明确HMAC_or_issuer_trust_verified=False。来源→reference/Receipt→Alignment→measurement→WorkValidation/Quality/Manifest无futureSHA、占位或循环依赖。

完整测量导出须有实际参考、报告、必要listener/arbitration及许可闭包；受限媒体文本projection明确父包/取得限制，不冒完整证明。origin字节/ID/hash保留；导入不安装root/key/authority或授新制作资格，能核HMAC仍须本地registry证据/范围/revoke。无参考qualified路径继续not_measured，reference/N/P95/locator全null且无placeholder；strict缺参考等待，不换策略、借benchmark顶替。max端点误差、完整N、nearest-rank200000us与MM05均未降低。

## 两轮pure证据及限制

| 历史实际批 | 结果 | 耗时 | 身份范围 |
| --- | --- | --- | --- |
| 0023a2，Receipt2248fc69260e4687dedb9c7c8c87521bfa45af7f8719f569a2a8f25698ca1b5a | 15pass/0fail/error/skip，exit0 | 0.09578919998602942s | 9项before=after |
| 031d78，Receiptb445a6605d8b34860f055c2af6fbbcf4a84c4c9010889cbf177cd33ffe6545e8 | 15pass/0fail/error/skip，exit0 | 0.07123099997988902s | 9项before=after |

本轮只读收据/raw与源码，未重跑。实际是原6加9个pure checks；自己生成的plain file从未import，identity_then_loader的callback只记sentinel一次。actual admission/PathFinder/producer loader/BundleService/HTTP/MCP/ASR/decoder/DB均0。不能称15项真正业务或完整bootstrap通过。

两批仅reference helper和sanity新增严格ID子例后变化，原首批不覆盖；首reference正文4f6657dbfca19caf540c07480ddd92604e2ef1705b731e4288a410521afd0ab1保留并核匹配。首新增sanity正文35d43758…在增补前未归档，原before/afterhash/raw可支持身份与结果，但缺正文保持，不能用末287b3967…正文倒填。末8份Test正文与实际源及末before/after均匹配，归档明确postrun，不代未来生产prelaunch全文归档，也不补T14。

自身只读元数据脚本曾选错旧Snapshot记录字段，Get-FileHash报null path；该次未接受旧27核验。之后仅按已有fixed_candidate_bodies纠正字段，27真实hash匹配；原工具错误记RV19FactsCheck.review_tool_limits，不算产品红或测试重跑。

## 后续与结束

实际完整0.3唯一模型/签名、六consumer ABI、独立固定Binding及Test bootstrap、完整生产正文与资源、真实听审参考/issuer/方法资格、全包/API/MCP、MM05、三OS及独立验收仍pending。这些是准入/证据缺件，不假称当前产品已失败或通过。

Reviewer产品/测试/网络/安装/费用/key读取均0；全部工具终态、无live。本轮静态与标准批准不授任何收费/运行/发布/安装许可，不签Gate/R1/R2。固定事实见自身RV19FactsCheck/Snapshot/Handoff；阶段FINAL释放，不等待活跃生产。
