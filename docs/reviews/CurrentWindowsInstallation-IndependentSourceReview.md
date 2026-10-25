# 当前 Windows 安装接线独立源码评审

结论：**SOURCE_STATIC / 本切片不通过，三个 P2 保持 OPEN。** 已独立核固定 Backend carry 101 件、其基线 101 件，以及 Native RevisionTwo 41 件源码与 14 件普通证据；没有执行产品、SQL、原生调用或测试，也不授 RuntimeBinding、安装资格、Gate、R1 或 R2 完成。

## 固定版本与范围

Backend 当前来源为 `Backend/SetupProductionCarryImplementation/SourceStage`：SourceIndex `c8676d0d5bc912a6b0906e168da6b3979cf0ff114efc836501091eb3d5a0dddc`；Handoff MD `f72395dae89ff77fad52a8d49bc8a38f418ad8b1e9547725aa67916eabda4598`；Changes.patch `6413f516c91d958874c9fca451b9cb2d36ad734018e744a6eafe26bbff051172`，两源增量、99 件原件保持。基线是 `Backend/InstallationRecordConsumerNext/SourceStage`，其索引 `69b61ad2355267d6ba893a6a244ada01af30d305e808d7aebee662d87bba8ada`；该基线对 SourceStageOne 的旧 74672B patch `334102aba7aa6123f1bff8aaa0e65865f7c9d61d33382860506366448198e26e`，8 改/5 新/88 保持，不能倒填为 carry 本轮增量。

Native 来源只用 `Integration/InstallationTrustProducer-A45/SourceStageRevisionTwo`：SourceIndex `8345923c9cab43477f353bec5ab91285f3e66b6b10afc13b8328e365c0432a9c`；FreezeReceipt `36de87e24b8bfa9269671881978b1c150789845661df993cb35060be2ed38ef9`；其实际普通 ABI `EvidenceCopies/Seq6ProducerAbi.md` 为 `8e69125dd7266df02e5a301c77c86f98e9621d3945cc5ce0ca0026a40a86f4a0`。ABI 泛称 SourceStage 不取代这个实际 RevisionTwo 索引。所有具体普通路径、大小与完整 SHA 留在本角色 InputAfter/SourceAuditScope 及问题单，末核无漂移。

语义评审完整读取相干 trust/record/commit/current/outer lease/seq6/清理方法与实际调用方；完整库存哈希不表示把无关 Bundle、全部业务源码或所有运行资源重新验收。旧入口 AST 对照显示 `_request`、`main`、`initialize_and_bind` 等原 13 个顶层节点保持；变更集中到 `initialize_bind_admit_trust_and_record` 的 continuation。AST 相等不证明行为或 Windows 可运行。

## CWI-P01：未知原租约仍在，State 清理继续关闭其依赖

**P2 / Backend / OPEN_SOURCE_STATIC。** 固定 `cli/native_qualified_setup.py` SHA `b16c74308219f883a67e3597dad05654cb9ea7e7daa67f41db7ee67415441b52` 的 State.close（48–61）先标 closed，然后捕获 qualification authority 的关闭失败，却继续关闭 build、相关连接与 sources 并移除成员。`cli/native_owner_setup.py` SHA `b30cecbbf0ebc2f3e1190879caff3d07d95064acc39a16ed643bdc85b79af391` 在 473–479 的 finally 无条件走该清理，尚未观察原 child/Job 的实际终态。

明确触发为原 begin/end writer lease 已可能受理但回复/ACK 未核实：`infrastructure/qualified_authority.py` SHA `f67431c13c0260948e40099735a5197ab61424d308ea9706980588aee69614a8` 的 173–217 保存 lease_unknown 并拒绝 close；`application/native_qualified_issuer.py` SHA `7778919e7d339c6f5701fb1a40381f264335743dec45b556f192ecd3201c5957` 的 120–149 保未知状态并拒关闭。`application/native_installation.py` 的 close 顺序会将此拒绝上抛，而 State 捕获后仍调 `OwnerProtectedNativeBuild.close`（windows_authority_pipe.py:197–200），实际关闭原 image HANDLE。State 已 closed 也使重复 close 无法成为有效的后续保留/对账收尾。

所以“内部 connection 正确保未知”不足以保护外层依赖生命周期。Native 自身持有强 Arc/原 Job 不把 Backend 的提前释放自动变正确。最低修复是由同一原 retained scope 继续持有所有依赖，直到原 ACK 核实或 exact child/session 真终态；首异常与未知账本必须保留，不能用重开同 SHA、虚拟 lease、盲 end 或清 pending 代替。独立 Test 后续应证明受理后失联/结束未知时依赖未关闭，且实际终态后只关闭一次。**未在 OS 上复现。** 完整路径/六源 pin 在 EarlyFinding-CWI-P01.json。

## CWI-P02：正常 Engine 初始化从未执行 0011 资格迁移

**P2 / Backend / OPEN_SOURCE_STATIC。** 固定 `infrastructure/database.py` SHA `925e322e2f0e78b34ca5877fe441803b60b5827961104d80ccfea0a308bbd8ca` 的 34–57 仍只遍历 migration 1…10，最大支持版本 10；backup/version 分支 98 也仅承认旧版本集合。新增 `migrations/0011_installation_qualification.sql` SHA `784a6a8726510d01ceae0478a9fd100c4abf1ee56f4b08e79dd07b7c1e76f72d` 创建资格四表/不可变触发器，但没有 user_version=11，固定 101 源闭包没有把它接到正常 initializer。

真实调用链是 native_owner_setup.py:356 正常创建 Engine → 原 Database 初始化 → installation_trust_consumer.py:125–130 在 reserve 前 SELECT 新资格表。新 DataDir 或原 v10 数据不会有这些表；外部手工设版本 11 又会被原最大版本拒绝。这是固定源码上的正常路径缺件，评审没有制造 SQL 失败或宣称 observed OperationalError。需 Backend 同步正常迁移、最终版本、兼容 backup/restart 规则，并保存旧已应用迁移身份；不能让 Test 手工建表算修复。独立 Test 后续测 fresh、真实旧版本升级、重启与坏/回退版本。完整路径/pin 在 EarlyFinding-CWI-P02.json。

## CWI-P03：正常 Native current 回复违反固定 v2 消费方形状

**P2 / Integration / OPEN_SOURCE_STATIC。** 普通 Native `apps/desktop/src-tauri/src/qualified_authority.rs` SHA `601b63d3430af33fe564b6bf7dc7e7c06accdb04c018a278149471d300e62def` 的 Request::Assert（67–72）在 71 给正常 `current_qualified` 回复赋非 null observation_id。Backend 固定 `infrastructure/qualified_authority.py`（上述完整 SHA）163–166 向同原 observation 发 assert_current，108–113 却明确只 observe 可带 observation_id/files/time；任何非 observe 带这些事实都拒绝，140–142 使连接失效。

即使 instance、三 SHA、完整 record、原成员、lease/floor/时间全部真实正确，健康 observe→assert_current 也会因这一字段形状拒绝，阻断 NativeInstallationAuthority 发行首次 evidence 与 seq6 后生产。ADR0043 继承 v1 原 method 观测形状；v1 held_authority.py:220–226 同样禁止非 observe 的 observation_id。ADR0044:82 仅增加 lease_binding 和 begin/end，明确其余方法原字段不变，不能据此放宽 parser。

最低修复归 Native producer：保留原 observation 关联在强成员表内，current 成功回复仍用原非 observe 的空事实形状。独立 Test 按冻结 ABI 覆盖健康 bind→observe→assert_current、foreign/unknown ID 与非 null 观测事实负例；不要放宽 Backend 闭集 validator 求绿。**没有执行 wire 或 OS 复现。** 精确普通路径/协议条款/pin 在 EarlyFinding-CWI-P03.json。

## 源码可支持的有限事实

当前 carry 在同一个 Engine 与原 Setup State 上消费 seq6，严格绑定原 instance/role、三 SHA、完整 file map/partition 和原 native image；在 continuation 出现前不取 Goal，不另启第二个 Engine/child。原 four-field production ACK 后才交 Goal；私有 concrete issuer 保存原 evidence→原 observation 关系，真实 outer qualification lease 在短 SQL writer 外取得，短 writer 的校验只检查原对象/线程/连接/成员及已获 lease。管理动作和 reauthorize 的 outer preflight→原 Owner control→Production control→短 writer 接线保持，不能用公开管理 cap 默认认可缺报告。

Native 先由原两个实际交互输入分别形成 trust/record action，后绑定原 child/instance；CommittedTrust/QualificationSource 对真实持久 control/snapshot/完整 DB 导出证据与 action/ref/revision 做匹配，强持有原材料与文件对象。Registry 的 current、不可逆 epoch 与原 lease 不靠 DTO 布尔值授予。qualification_pack 核实际目标来源、原 Windows 版本/机器架构/CPU 特性/CRT 指纹与原 CPython/profile/fullmap；签名核的是原材料选定 key，具体 source admission 和 record acceptance 仍分开。Native OwnedSetupRun 错误 Drop 通过原 OwnedProcess/Job 收尾，待确切终态和 Job 空，再 join 原流/会话，不能继承为 Windows 实测通过。

这些源码事实只说明接线与限制所在；三个 P2 仍使当前切片不能认为可用或 qualified。许可/独立 review/acceptance 材料只是原 ref 与字节绑定检查，不是本轮完成了那些独立工作。

## 原失败与未测边界

保留 Backend 原两 auto-review patch 拒绝与未应用、原 checker 文字匹配错误及其后 AST 修正。原 baseline continuation gap 不回填；本 carry 是新源接线而非原 gap 当时已运行。Native 首冻结 722fdd 错定位、既有 before-capture 缺口和当前 source-only 原件保留；本 RevisionTwo 没有 Cargo/build，新增 Ed25519/cryptography 声明未代表离线依赖、ABI、payload、许可闭包已核实。三个 syntax 命令自然 0 只是有限静态证据。

既有 corrected1824 test 自然 1 / 八 NOT_STARTED 属加载 guard 前置失败，不证 SQL/产品失败。原 B43-I01 同步 stdout 可能阻塞而不能被 deadline 检查中断，I02 原 OS buffer/source 早字节观察缺口独立 OPEN。higher floor、pending/restart/replace、retirement caller、完整 actual producer/report/license 和 Mac/Linux source/runtime 未实现或未测，不能靠第一次 revision=1 支持外推。GMNR、真实 Owner 资格、模型媒体/ASR精度、三 OS 安装与完整 R1 后连续 R2 均保持原要求。

Review 自身路径定位错误 bb7c68/1、835cd3/1 的 native index 字段误读已保存，随后按真实索引定向纠正；它们不是产品红。大库存打印/协议输出截断不当全文可见，必要字段与候选链已定向补读；不重跑产品。全程费用、钥读取、产品/测试执行、安装均 0。

正式过程根：G:/开发测试/Codex/VideoCreatorImplementation/Review/CurrentWindowsInstallation。问题单、有限范围、末输入核查与交接均保留于该根。评审只给归属者整改与独立 Test 条件，不代实现、审批或验收。
