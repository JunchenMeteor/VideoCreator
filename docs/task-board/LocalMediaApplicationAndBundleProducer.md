# LocalMediaApplicationAndBundleProducer

ACTIVE，唯一原 agent_media。只写仓库 `services/engine/src/video_creator/workflows/`、`providers/`、`media/` 非测试生产源码及自身 `AgentMedia/LocalMediaApplicationAndBundleProducer/` 过程；不改 Backend/Integration/Frontend/Test/Review/Acceptance 文件。目标是把已停止 Media55 候选修复后真正应用到当前产品源码，并按已独评 0075 接通本地适用媒体/证据生产；不得再止于未应用影子源。

固定输入：Media `LocalMaterialFlowAndBundleCompletion/SourceIndex.json` SHA-256 `95dc15020b56965c169b0c108d519290e1743115480e288164f3d1c86c6b68c1`、Handoff SHA-256 `ac7922a6ef3f36525dd2c0bc3027c01cafce3936aa7a59038d60a7f84451b3f9`；Backend 已停 `LocalPlanBackendCompletion/SourceStage/SourceIndexLf.json` SHA-256 `0c662eecb4727586d84e102e527481c99fdb4cc818116ad551b052beffc849ef`，仅消费其真实接口，不写其源码；ADR0075 SHA-256 `776a1bb058bc79d9beee04aa9da129219e786c33707a01732a1c9b942a071091`，设计独评 SHA-256 `54b550e100b4ed75e496b7a6c65ecba66433ab21fa915464cd60526075ef7061`。源码独评 `Finding-LMF-P01.md` SHA-256 `95363b78eea3a70fa90c988e3c0f6fa1f2af9509a43200d4bac3ef1312e425f4` 已固定，正式报告在写；继续接收其后续确定 findings。

先以实际当前工作树和候选哈希三向核对、只覆盖 Media 自己白名单的适配文件，将 55 源改动真正写入仓库；修 LMF-P01：接受同一宿主的真实 `RegisteredOperationExecutor` 安全子类/对象关联，保留原 Operation journal、sameRun/fence/授权与未持有拒绝，不能改 Backend 为裸 executor 绕门。LOMD-P01/P02 静态修复必须保留。清晰记录应用文件数、差异、是否有先存改动冲突；冲突暂停单文件并报告，不强覆盖。

随后实现 0075 Media 所属：静态 PNG/JPEG 原probe/source范围与 display-hold/整数帧映射；由原request/受控plan产生实际适用 video/audio/narration/mix/cover（无音轨/无旁白/audio-only 不造假）；真实 final speech/no-speech/no-audio 证据、ASR/CTC/两真实authority/200ms和零cue字幕材料绑定、质量/semantic/RAG V2 受控材料。与 Backend sole DTO/Bundle 入口配合，缺资源走原同Run WAITING/恢复，不把原稿当ASR、不造假精度或权利。优先拿出最短可运行口播视频路径与完整缺口，再扩 audio-only/no-voice；不得把安全错误永久503当最终产品。

每个小段实际做可运行的 AST/Ruff/允许的原测试与回归，并留原始命令、exit、错误和文件哈希；如原 Pydantic19/三败限制仍命中，不换名重试，继续可做的静态/子模块验证。不要付费、改凭证、部署/发布。交付实际仓库 diff、Impact、接口/未通点和自然终态；静态检查不算成片，真实运行与独立评审/验收另行完成。
