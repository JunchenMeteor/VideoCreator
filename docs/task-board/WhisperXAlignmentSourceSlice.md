# Integration — 固定 WhisperX 对齐源码与许可切片

QUEUED，原 Integration 角色；Architecture a3766d2 TRUEFINAL 释放后才恢复。目标是给 Media 实际固定3.8.6源码，不凭 README/main 编写驱动。保留 PiperProductionInputSelection 8ddded3b 后继及完整 R1/R2。

输入：停止 ADR0055 20626B SHA a2fee3e34896ccabcc4c873de8a160bda70452ba7dc0954327f21150ea54cf04，Root c62928 FULL 读取；tag commit 3ccc17b8de34f305300f8a3fd3c9f76ba820c0d0。Architecture 原停止 Handoff 的精确 PyPI JSON 普通副本路径/SHA，须先核对，不消费热文件或重新抓 metadata。

白名单：依赖/构建/集成原归属目录；本阶段不需改产品配置，证据仅自身 Integration/WhisperXAlignmentSourceSlice。不得修改 Media/Backend/测试、共享依赖或全局配置。

有限授权：从已保存官方 metadata 中选择恰 WhisperX3.8.6 wheel 与 sdist 的原 URL，各一次匿名 GET，最多2次，不重试、不HEAD、不换版本/端点。先冻结 URL/大小/SHA/输出绝对路径/输入身份/期限计划；wheel16486941B SHA cb6d4fcd3fb6c42305cb8b222a33a0b78f6b657e9db3b714345fe43dc0a69c1f，sdist16490881B SHA d647aecaa6c2f413bb924d722d925878ef300c99093ca49cd6cb7840bdbffe0e。HTTP状态、长度和完整内容SHA均核对；失败保留原响应/部分数据，不继续第四或等价绕路。每请求有限期限；原owner持有并观察实际工具至终态，观察超时不重启。

仅数据安全检查：ZIP路径/CRC/RECORD、tar路径/链接/成员/完整EOF等，拒穿越与未知链接，不执行、不import包、不pip安装。抽取固定 alignment 代码及它实际直接引用的源码、LICENSE/版权/通知、METADATA/PKG-INFO和完整成员索引，逐件内容SHA。对比两产物内对应源码/许可，记录不同或缺件；不能以tag metadata声称源码与git commit已证实。分析真实3.8.6 align/load签名、trellis/backtrack、中文字符路径、离线模型加载、weights_only安全加载及 import依赖；给 Media 完整普通副本与必要最小闭包，不能只给摘要/片段。

缺源码或绑定事实时输出具体 SourceGap，并给另行有限官方源对照计划，本卡不授额外请求。不得下载模型权重/Torch/任何 transitive包，不进行运行/推理/ASR/native/SQL/Pydantic/安装/收费/凭证读取/提交/部署，不能触碰原被拒 supervisor 或耗第四业务目标。

证据：真实命令/退出码/完整SHA/自然终态双EOF与未变输入、完整ordinary源码与许可/Handoff。供 Media消费源码、Review核来源、Integration后继解精确运行闭包；数据检查不是平台/许可分发闭包/算法精度资格。失败回滚仅自身新增数据，保留失败与其他角色内容。真实媒体、IntelMac与其余平台资格仍未完成。
