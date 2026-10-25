# RV2 W5/W4 稳定源独立复审

2026-10-08。永久评审角色，仅只读实现/测试/标准/过程证据，写 docs/reviews 与自身 Review 材料。未修改实现、测试、标准、锁或 ACL；未收费、读取真实 key/.ssh/ValidationInstance、重开 Crew 实验或兼任验收。

**阶段结论：原 58 回归在固定 W5/W4 源上真实通过，RV1-P01 解析缺陷可在已测机制范围关闭；RV1-I02 的 HLS/concat 调用前拒绝可局部关闭。新增格式/MP4 外部引用批另按 T5 终态核对，不以原 58 外推。** 发现新的公开415契约遗漏，归后端/架构/集成。技术 Gate、完整作品、包及 R1/R2 均未通过。

## 固定源和证据

W4SourceSnapshot.json SHA95908d77a9eb244d05a8b2a05ef1f586f0883fb16688fef564f9ca7d3572da8c 的12源逐项匹配当前字节；W5 react_protocol.py SHA84a39f18b6ceacdaa783c3e2b7266bc526a2b0e99f6496ef610dc704e2b238a2；W4 ffmpeg.py SHA36a13bb084228e1e1b1021da8812688720192c71560340a4951ad6595a201a5d。除上述二文件外，35原依赖的版本变化按 owner 与 T5 明确记录，不能把旧 W5 独立范围倒填为新 media 的通过。

独立 T5Original58Regression 实际 command：Python -X utf8 -m pytest test_t4_parser_boundary.py、test_w1_protocol_gate0.py、test_controlled_llm_gate0.py、test_t4_media_reference_boundary.py、test_b3_public_media_gate0.py -q（原6+35+4+13）。exit0、58 passed、0 failed/error/skipped、94.268s、112 warnings。39精确依赖 before/after、范围外监控变化均0，39当前hash再次逐项匹配。stdout hash匹配收据，XML SHA cdf6ed052e8f3cc5ad7ec84ba239ce3e5f9b791ca7c2bc29f1b05d9a7bb47fc7；CommandReceipt SHA e4d397b3271a62ab4170f210d61de83c634a126b49fd95dd14771fc022d397d7。

全参数/UTC/环境/sourcehash见 TestDevelopment/T5Original58Regression/CommandReceipt.json；本评审不自编、不重跑验收。T5新增批测试与最终交接另记，不从正在形成的文件推断整卡完成。

## RV1 问题复审

### RV1-P01：完整裸JSON→锁parser，机制闭环

react_protocol.py:98—101 对完整裸JSON明确加 Final Answer 控制前缀；97将数据内同名字面冒号作JSON unicode转义。原本的数据值、模型原响应/usage及Operation原文保持，JSON不是隐式工具动作。真Action有原前缀继续作为工具，混合Action/Final及伪Observation继续拒绝。没有改锁Crew parser、Task或账本。

T5原6与原35实际通过：无标记/含Action+Input/含Final课程字面裸JSON得到正确final，公开CreativeProposal语义保持；真Action输入解码值保持，原拒绝反例继续绿；成功子任务与实际模型产物一致、final精确复用守卫保持。原T4三红和RV1证据永久保留。关闭的是机制缺陷，原付费Crew三轮真实delegation0、LG无人失败与完整自主作品未通过事实不变，不授予新收费尝试。

### RV1-I02：调用前引用拒绝，限定闭环

ffmpeg.py:169—200 先有限识别真实 PNG/JPEG、PCM WAVE、允许major品牌ISO MP4，不以扩展名/候选MIME选择解码器；HLS/concat/XML/其他格式在Popen前拒绝。T5原4实际全绿，对应原三引用反例与自产自包含WAV正例。原T4 GET0/未导入的证据并未证明过SSRF或目录外读取成功，此次也不把拒绝反例称为修复已证外部读漏洞。

MP4新增103—166遍历有限box、只接受精确自包含url dref；203—231固定file-only protocol、指定demuxer、enable_drefs=0/use_absolute_path=0。源码策略明确，MP4外部dref与不同结构的独立反向证据由T5新增批核定；仅有flags、仅HLS通过不能证明全部媒体引用隔离。

真实MIME按格式/codec推断；PNG/JPEG真实尺寸、单帧且duration=null，与现有MediaProbe/AssetService兼容，无须复制新公开Schema。PCM WAV、视频MP4、音频MP4独立各自MIME；QuickTime/独立MP3等拒绝，不误贴格式。原B3畸形内容的422/media_process_failed兼容回归在最终源58批保持。

### RV1-P02：证据工具与真实停止分别记录

I4只修自身过程脚本的无证graceful=True，默认未知，原raw/exit3保持；这是证据工具修正。ADR0005只批准私有CLI control-stdin接口，B4尚未实施/实跑，不能关闭旧候选停止exit3的功能失败。未来CLI/API版本另固定身份，原T5源绿不继承未来修改。

## 新问题 RV2-P01：媒体领域415未声明到公开OpenAPI（P2）

**触发与源码事实：** W4 ffmpeg.py:92—95/APNG、147—152/外部dref会抛EngineError(status415)。当前api/app.py:39—52的ERROR_RESPONSES无415；85—88以真实error.status_code返回ErrorEnvelope。已生成 /api/v1/assets/import responses只有201/400/401/403/404/409/413/422/503，生成SDK同源。因此新增领域拒绝状态没有进入公开API契约，消费者不能从正式Schema发现该错误状态。

**当前证据边界：** 这是源码与生成契约直接可核的遗漏；真实HTTP415样本由T5追加/终态收据核定，不把仅直接AssetService异常当HTTP实测。旧ErrorEnvelope模型可继续复用，前端通用JSON失败分支不等于OpenAPI已经同步。api/app.py当前SHA90ca70480c8b245ba08717d1d89092e626a62cf703a38a9805509c18276228b1。

**归属与最小动作：** 架构明确415或既有拒绝状态；测试保留实际APNG/外引失败与published响应声明的反例；后端从唯一API来源补声明或按裁决统一错误语义，集成重新生成OpenAPI/SDK，前端只消费。等待T5全部CLI/API依赖批结束与统筹解除后再改源，不能在冻结测试中移动输入，也不改原期待伪绿。

## 版本边界与仍未证明

W4Before、ReferencesAfter/B3Original13After（中间源c7e5d2…：12绿1红）、ReferencesFinal/B3Original13Final（最终源36a13bb…：原4+13绿）是不同版本，原红未覆盖。W4FormatsAfter的7样本仍属中间owner实验，不倒填最终状态码或独立验收。

max_alloc限单次FFmpeg分配，不是OS总内存隔离；尺寸/像素/输入字节/流/时长/box深度计数及90s停止是各自限制，未据此声称完整操作系统沙箱。codec白名单未全部实样验证，不宣称全部兼容。原58包含真实自产媒体解码与免费注入协议机制，不是58个产品需求验收或真实动画/语音作品。

旧68c1f069 API包仍旧源码且独立AV0两次停止exit3；没有新打包产物证明W5/W4/B4生效。ASR解释器/模型未bundled、实际听审、完整API/MCP到Bundle/export/reference、全部自主/审核修订/无人链、公平框架裁决、Tauri/三OS安装及R2官方权益/支付/授权发布仍缺闭环。标准范围批准和ADR0005接口批准不等于技术Gate通过；完整目标继续Gate0→R1独立验收→连续R2。

本阶段交RV2Handoff.json给统筹/归属角色与AV。T5新增稳定证据收到后另补范围；未测项不计通过。收费/真实key读取/ValidationInstance/.ssh读取均0。
