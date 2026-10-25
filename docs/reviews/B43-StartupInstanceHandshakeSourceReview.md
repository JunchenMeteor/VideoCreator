# B43 同一 child 初始化独立源码评审

结论：**SOURCE_STATIC；两项 P2 保持 OPEN，不能据此进入已通过运行资格状态。** 本轮只读最终固定 88 份普通源码、两个旧版本改动源及有限治理/交接材料，没有导入或运行产品、Test、DB、Win32、native、Owner、模型、安装或网络；费用与秘密读取均为 0。

## 固定范围与实际核对

B43 根为 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/StartupInstanceHandshake-B43/`，仅使用 `FinalSourceStage/SourceCopies`。完整路径、大小、SHA 见 `G:/开发测试/Codex/VideoCreatorImplementation/Review/StartupInstanceHandshake-B43/InputSnapshot.json`。104 个输入前后无变化；88 源、78 Python AST；84 份与固定 B42 索引 SHA 相同，两份新增、两份修改。原 `_request` AST 保持不变。独立用固定新旧正文重构整个四文件 diff，与原 30259 字节 patch 完全相同。

- 最终索引：`1d64f63b629511c75efdcceb3a4ada4cbc34a955caf7d406d388a8bdb514d9b2`。
- 完整差异：`6656b097b527bd7c1b7878e7f2298e8d33468fc71e314364ec578786f30bd85f`。
- B42 基线索引：`aecd0ec796b6d44d3a594f4b297d614addb03277564f7d4a219be1d0acf31fcd`；只读其两份改变源正文，不读热生产文件。
- ADR0042：`5ce102204593390e421a4f50af4c0fb3c8c2fe78c071dd950502620ed42c4f13`。
- 只读补充 `InterfaceClarification/Facts.md`：`a960407626a7c0b1be2b4a5bdcbb4045917cacd06e4c0e5e7aa3395ca07738af`，没有实现变化。

原初批 `StaticOutput.log` 索引 `63a0a5…` / diff `ade9bb…` 与最终版本分别保留，没有把早期快照回填成最终身份。owner 两次静态日志均标 `SOURCE_STATIC_ONLY_RUNTIME_UNVERIFIED`；它们证明自身 AST/来源检查的有限结果，不能证明 Python import、OS 行为或安装。评审自己的纯标准库解析没有导入产品。

## B43-P01：首次制作准备前缺少当前数据库身份检查

**P2 / Backend / OPEN / SOURCE_STATIC，未实际复现。**

位置：固定 `FinalSourceStage/SourceCopies/services/engine/src/video_creator/cli/native_owner_setup.py:233–239`；源 SHA `029840069e7097095293d2ed1df7a6cfdba90f695db49463c7e8723cc0556420`。该段在输出 `setup_bound` 后取消初始化 reader deadline，等候原 Goal，然后只调用 `source.assert_current()`。

完整条件链：唯一数据库检查 `infrastructure/native_instance_source.py:162–177` 核同一 Engine/Database、实际文件身份以及 SQLite 的 `metadata.instance_id`，最后调用在 `native_owner_setup.py:228`、输出 `setup_bound` 之前。其 `assert_current():130–140` 只执行 OS 目录、原 peer、held host/receipt、原 child/session 检查，没有读数据库。等待 Goal 的间隙若 metadata 行被删除/改值，或数据库文件被替换，而目录 inode、Owner、peer 和 held 安装资源仍相同，收到 Goal 后不会重核数据库身份。

后续并没有等价保护：`_continue_setup:77` 只比对 cached `engine.instance_id`；`application/owner_setup_confirmation.py:66–74` 调 OS preparation；`infrastructure/native_owner_confirmation.py:151–162` 核目录/held 文件/peer或原局部对象，均不查询 metadata。`application/owner_setup_service.py:144–163` 随后打开原路径事务并以缓存旧 ID 写第一条 `owner_setup_journals`；`:165` 可继续创建草稿。这样“同一个 Engine 对象”不能保证它仍属于最初回复的实际数据库身份。ADR0042:48 和任务卡:9 要求 effects 前保持原根、文件和实际实例关联。

修复条件：收到 Goal 后、进入准备副作用之前重新验证原 Engine/Database/file/实际 metadata，并在短 writer 边界持续提供与该数据库一致的检查；缺失、变值或换文件应拒绝，不能 INSERT 修复、重新 Engine、生成新 ID 或重发 Goal。后续正常 Goal/人审可能晚于初始化 20s，不能直接借复用已过期的绑定 deadline 把合法后续流程永久拒绝。Backend 负责源码与接口；Test 后继要用合法初始化来源分别验证 metadata 删除/改值、实际文件替换、未变阳性，以及拒绝后的 journal/project/command 无新提交。不能使用 fake source 代实际 Owner 资格。

## B43-P02：非 pipe 拒绝逸出封闭握手错误码

**P2 / Backend / OPEN / SOURCE_STATIC，未实际复现。**

位置：同一固定 `cli/native_owner_setup.py:240–242`。初始化来源通过以后，`_InitializationInput:142` 构造原 `ControlPipe`；固定 `cli/lifecycle.py:81–82` 的非 pipe stdin 拒绝为 `control_pipe_required` / `400`（POSIX 同一条件在 :85–86）。新入口捕获这个 EngineError，直接把原 code/status 输出为 handshake `event=error` 帧。

ADR0042:40、ImplementationInterfaces:19 规定六组 `owner_instance_*` 握手错误；只保留真正 Engine schema/migration 的旧 code/status。这条失败来自 stdin/control，发生在 Engine 创建之前，没有 schema/migration 例外依据。因此 Native 严格消费者会收到不在合同闭集中的错误，无法按已批准规则归类为准确拒绝。该结论不要求虚构真实资源资格；实际触发的前提是合法来源认证已通过、stdin 是可读取 fd 但不是管道。本轮没有运行此 OS 条件。

修复条件：由 Backend 在 control/handshake 拥有者边界映射到批准的闭集错误，保留 exact wire/seq/code/status、没有 detail/path/Goal/secret；不要放宽 Native oracle 接受任意旧码。真正 Database schema/migration 错误须保持原诊断和提交事实。Test 后继分开合法非 pipe、EOF/early bytes、六对错误与真实 schema/migration 例外，不改已有失败历史。

## 有限支持与明确缺口

源链支持一个原 Engine 的创建：`initialize_and_bind:207` 只构造一次，保存原 Engine/Database，两个 identity 输出前均核实际 metadata 与文件；随后私有 `_continue_setup` 复用同对象，不调用旧 main 再创建 Engine。旧 main 仍原三 bytes 参数，Goal parser AST 不变；提取后的 prepared→accepted→goal_accepted、完整 recovery request 比对与失败 sticky finally 顺序仍沿原路径。

新 parser 固定六初始化字段、canonical UTF8、重复键/非有限数/严格 seq 类型、封閉 pipe role 与 peer 字段；bind 封套的三个值须完整 JSON 对象，重新编码给原 parser并核同 ID、全部 installation/独立 host/receipt、同初始化 server。封闭 source factory 只接受 exact record；来源通过真实原 peer、受保护目录/held 文件与当前 child/GUI session 检查再建 DB，不能由 JSON 或 caller bool 产生管理/安装资格。原 source 在 process 全局表强持有；finally 禁用新操作并关闭 stdin 的 duplicate fd，不主动关闭其 original held 资源或重新连接。这些都是静态机制支持，实际来源生产者/Job/guard lifetime 尚无本片运行证据。

**B43-I01：已披露期限缺口，P2 / Backend 与 Integration / OPEN。** `_instance_response:174–175` 同步 stdout write/flush 可阻塞，`:215/:230` 的 20s 后置检查无法中断尚未返回的写入。Backend 没有独立 bounded completion；Integration 必须真实持续排空双流并保持 original child/Job/guards 到终态。此项不能因前后 deadline 检查或 AST 绿而关闭；本轮没有模拟堵塞，也没有声称实际 OS 超时。需要双方固定实现及 Test 独立真实堵塞/EOF/终态证据。

**B43-I02：early-Goal 观察范围不足，P3 / Backend + Test / OPEN，SOURCE_STATIC 条件。** `native_owner_setup:226` 仅看 Python `pending`，并未检查此时 OS 管道剩余字节。`ControlPipe.read_available:104` 一次最多取 4096 字节；若完整 binding 读完时 `pending` 为空，而提前 Goal 已在 OS 管道中（例如合并队列读取刚好在 binding 边界结束），guard 可漏过，随后 `_request` 会消费它。当前实现能拒绝已经被读入 pending 的提前帧，不能证明所有已排队提前输入都被拒绝。保持原 Native 收到 setup_bound 后才发送 Goal 的约束；后继测试须分别覆盖 Python buffer 与 OS buffer 的真实边界，不仅测一个合并小帧。此处未做 OS 复现，不主张单次 peek 能原子消除全部发送时序竞态。

保留：真实原 GUI/Owner/parent image/child HANDLE/Job、受保护 DataDir/Control/祖先锁、新/旧实际数据库与升级备份、双 byte EOF 与 unknown 提交事实、正常真实 setup/每日制作接线、安装资源资格，均不能由这份源码评审授予。Windows 路径未执行；macOS/Linux source 在 `native_instance_source:58–59` 明确 503、尚未实现。20s 过期后初始化提交或备份不能删除/重置，setup_bound 不是人审或 Goal 接受；本片没有自动重试/重启/清 pending/预算降低实现。完整 R1 三 OS 真实多模态作品独验后连续 R2，不缩范围。

`InterfaceClarification/Facts.md` 只说明公开 null daily-ref 选择仍通过当前 Owner/grant/current guard；固定源码没有 publicly exposed selection GET，原 Engine daily service 未装配返回 503。该材料是后继接线和 UI 消费的边界，不能证明日常制作已接通；本片没有热读后继 Backend 或 Frontend。

## 证据与交接

过程根：`G:/开发测试/Codex/VideoCreatorImplementation/Review/StartupInstanceHandshake-B43/`。InputSnapshot/SourceFacts/InputAfter 保留完整 104 输入身份和独立重构 diff 结果，EarlyFindings.md 保留早交两个 P2。最后读取必须自然终态，读者释放；实际 finalizer tool 回执另写 FinalizerTerminal，不以文件存在或 Agent running 代替终态。无 RuntimeBinding、运行、安装、商业、Owner、OS 或 Gate 签字。
