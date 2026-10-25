# CurrentInstallationFixes 独立源码复审

结论：**CWI-P01 / P02 / P03 的原精确源码缺陷均可在本次固定版本限定为 CLOSED_SOURCE_STATIC。** 未发现此有限切片的新源码阻断；运行、协议、安装资格和完整验收仍未通过。原报告及原问题单不改写，以下是后继版本裁定，不回填旧版本。

## 身份与实际读取范围

原报告 SHA `20ec6c3981975abb5a574baca11af05be88f5d2904fdc3d79c39c32ff9919217`、三个原 P2 问题单已独立全文消费。固定新版本：

| 来源 | 普通源码 | SourceIndex SHA-256 |
| --- | ---: | --- |
| Backend/InstallationQualificationMigrationWiring/SourceStage 中间版本 | 101 | `68e191a0790910a06fb7d9bef6c3d5ea397635e9e357e4d81f17c0156b0010de` |
| Backend/QualifiedSetupDependencyRetention/SourceStage 最终 combined | 101 | `4ceea4bb916a5223133fe15c881bb61c864752ca6f735ff3bc1c663c4524035c` |
| Integration/InstallationTrustProducer-A45/SourceStageRevisionThree | 41 | `e7bf14ae39b3d7216164aa56e81e063e4fa0dd3e23769987997c9cb70bade25b` |

上述 243 普通件均实际核大小及 SHA，无 mismatch。原索引、必要原三源码、原 migrations1..10 和 Native 原单源码也只读固定普通副本；原 carry101→combined101 独立比较恰三源变，Native RevisionTwo→Three 恰一源变 / 40 保持。完整相干源码方法与两 Backend patch、Native 独立生成实际 diff 已读，不只信作者静态 bool 或工具 exit0。完整库存匹配不表示对无关业务模块重新做整产品语义审计；相干语义范围准确保存于 `SourceAuditScope.json`。

全部固定输入末核 **282 独立路径** 无漂移，见 `InputAfter.json`。自身过程根 `G:/开发测试/Codex/VideoCreatorImplementation/Review/CurrentInstallationFixes/` 保存来源路径、完整 SHA、差异与原失败限制。本次不读取热生产源码、重新盘点运行环境，未 import/执行产品或 Test。

## CWI-P02：正常迁移、版本与备份的源码接线闭合

**原 P2 / Backend → CLOSED_SOURCE_STATIC；实际迁移/SQL/数据完整性仍 NOT_RUN。**

最终普通 `services/engine/src/video_creator/infrastructure/database.py` SHA `ee0a8a5829f8305688976336e83f4bacb8a9175524837c7c9852648a92ba6f46`：14 行唯一当前版本 11；35–38 将真实旧 v10 纳入原 pre-upgrade snapshot；41–59 在原单 BEGIN IMMEDIATE 事务内按 1…11 升级，53 行明确调用原 `0011_installation_qualification.sql`，43–44 拒绝大于 11，56–58 每次严格校目标版本。100 行备份支持范围纳入当前 11。

最终 SQL SHA `b4fd817ee514a52c9c4c3996baa052d2a11a7546428b3769abadc44f1ecfb7fb`，52 行追加 `PRAGMA user_version=11;`。与原 SHA `784a6a8726510d01ceae0478a9fd100c4abf1ee56f4b08e79dd07b7c1e76f72d` 独立逐字比较恰原全部 DDL 后追加这一行；四资格表、约束、不可变触发器均原样。原 migration1…10 普通副本字节相等，不以重建 fixture 表或改旧版本代替升级。

正常调用链实际存在于固定 `cli/native_owner_setup.py:356` → `application/engine.py:56–61` → `Database`，随后才至 `installation_trust_consumer.py:125–130` 查新资格表。本次修复不引入第二个 Engine 或手动建表路线。`_apply_migration`、`transaction`、`connect` 原方法 AST 独立相等；146–154 原逐完整 SQL statement 执行，167–174 原 commit/rollback/final close 保留。这证明源码接线与原事务语义没有被修复绕过，不是实际 rollback 已测。

`snapshot_backup` 原 SQLite backup 捕获完整 Metadata.sqlite，含资格表；快照声明明确 `rollback_compatibility_verified:false`、外部 credential/installed manifests/current roots/revocation floor/newer cost knowledge 不能从旧 Snapshot.json 恢复成权威。已有单独停止/分目录/不得回退版本的恢复要求保持；此 module 没有新增自动 restore callable。

后续 Test 必须调用实际 Database 构造：fresh→11、真实 v10 既有数据/预升级 snapshot、existing11/restart 不重复、>11 拒绝、失败迁移同事务回滚/版本不假升、11 snapshot 及原外部 floor/未知费用恢复限制。Review 未连接 SQLite，不能据 AST 或 DDL 字节宣布这些运行通过。

## CWI-P01：未知关闭停止依赖链、强持有与真实终态边界闭合

**原 P2 / Backend → CLOSED_SOURCE_STATIC；原租约受理窗口/OS 句柄/清理运行仍 NOT_RUN。**

最终普通 `cli/native_qualified_setup.py` SHA `3b5e0c5d8cabc7a3f3404210aea0d99657de4626b2def32e5e100023458983f4`。State 构造33–41保原对象和强 `_states`；新36行存 close complete / first failure。49–75：成功重复 close 直接返回；已有首失败在52–56原异常重抛、无调用；首正常 close 57–59检查同原 thread/member，先 closed 阻新工作；63–67逐依赖关闭且没有内层吞异常；68–72首失败立即停链，保存该原异常，保 `_states` 和 `_production_members`；只有完整成功后73–75才 remove。没有凭 exception/window/返回整数宣布 release，也没有新 terminal setter 或盲重 end。

原当前防线仍实际存在：State.assert_current:43–47拒 closed/thread/member/Engine 变化；record/production 入口先走它。固定 `qualified_authority.py` SHA `f67431c13c0260948e40099735a5197ab61424d308ea9706980588aee69614a8` 的 begin/end:173–208 发起前置 `_lease_unknown`，仅精确 validated receipt 消除；close:210–217 拒 active/unknown。`native_qualified_issuer.py:143–149` 同样先拒此状态；`native_installation.py:110–117` 依次 issuer→connection，失败传播。现在它们拒绝后，State 不再调用 dependent `qualified_build.close` / record/trust/source / stream，不再移除强根。固定 `windows_authority_pipe.py:197–200` 的真实 image HANDLE close 可达于成功顺序，不能再在上述未知 authority 失败后因 State 循环吞错继续到达。

原调用方 `native_owner_setup.py:435–479` finally仍调用原 State.close；EngineError 只记录失败和 result1，并不是终态证据。失败 State 保住 source/stream/build 与原 issuer/connection；原顶层 frame/continuation/production helpers 的 AST 独立保持一致，修改仅 State 构造/close，没有扩大工作权限或重置 floor/预算/unknown。

Native 原持有链在固定 RevisionThree 相干源中可核：`owner_setup_runtime.rs:73–81` 在任何 post-Create 可失败调用前建立 `OwnedSetupRun`，强持原 Arc<Mutex<OwnedProcess>> / PreparedLaunch / Installation / carrier / sessions；140–142 在 authority 启动前保 continuation、同原 process 注册。正常167–171先 `wait_terminal` 后 join；269–294 的原结构和 Drop 持 registry/action，错误路径走原 OwnedProcess.force，并实际等待原 process exit 加 Job 空，再 join 原 session/流。`platform.rs:140–187` 使用原 process/job HANDLE、creation identity 与真实 Wait/GetExitCode/QueryJob/TerminateJob，不以 reopening PID 扮持有者。这里“force”是原 owning Job 清理，不是此次 Review 运行或对其他进程授权。

`qualified_authority.rs:17–20,31–35,102–105` 同原 Registry/Installation Arc 和已注册原 process；serve返回前仍等原 process与Job终态。`qualification_registry.rs:13–15,102–106,119–131` 持真实 read guard/原 process；正常 end 释放原 guard，而 unknown/EOF/unwind 的 Drop 在同原 child+Job未终态前继续持有，不能用错误帧提早解锁。它与新 Backend 强根形成相干源码生命周期；本次未编译或运行，不能称 OS 已证明此守卫。

下游 Test：真实 begin 可能受理后响应丢失、真实 end ACK未知、原依赖HANDLE有效且close计数未增、重复close同首异常/无I/O/无重交、原closed-state拒新writer；正常精确ACK路径每对象一次关闭；同原 child/session自然或正式owningJob终态后再确认原资源释放和账本/floor未改。fixture不可赋 terminal true 或仅返回整数冒这些事实。

## CWI-P03：正常 current 的闭集回包形状闭合

**原 P2 / Integration → CLOSED_SOURCE_STATIC；真实 wire/current/foreign/unknown 交换仍 NOT_RUN。**

最终普通 Native `qualified_authority.rs` SHA `6252ee6619fac6a7e6ca79e5af455644f20ebeb4eb7a95241467aaf1a2dbca1b`，实际独立 diff 恰71行去除 Assert成功 `response["observation_id"]=observation_id.into()`。36–40 的原 response 初始化完整14字段，`observation_id:null`、`observed_at_us:null`、`files:[]`；只有 Observe58–65 赋观测ID/时间/map。Assert67–72仍从同session observed HashMap取原 member，70行做原 installation current + registry original observation 校验，binding仍由原 member生成。foreign/unknown ID仍409；closed canonical/session/seq/peer及真实writer guard未被放宽。

Backend上述固定 `qualified_authority.py:18–21,65–118` 的14字段闭集、原 non-observe空事实规则、lease shape保持原 SHA；163–171使用原 observation发 current且严格比 record/ref/registry/floor。无 consumer 宽松解析来掩盖 mismatch。独立实际新旧Native比较另外40源 SHA保持，原正常对同 member 关联和 current资格条件保留。

后续独立测试须冻结同源 producer/consumer：健康 bind→observe→assert_current；non-null files/time/ID的非observe回包拒绝；foreign/unknown原ID、changed source/current/floor和租约状态拒绝。未执行 wire，不以一个属性赋值删除就授整个协议/资格运行绿。

## 失败历史、缺口与交接

两 Backend作者 source静态自然0、AST90，仅静态方法/身份证据，不当 DB/Win32/Test 通过。任务卡记录 once-granted Cargo97cb19/1在离线 missingpkcs8 resolver停住、编译未达；本片未另消费完整 compiler 批或重跑，不把旧I62/新syntax当current编译成功。原拒绝 patch、原loader test8NOT_STARTED、原CWI报告三个旧OPEN、MCR Old错误发送/Fixed6pass与准备失败均原件保持。

B43-I01 同步stdout可能阻塞、I02 OS-buffer早字节观察独立 OPEN；higher floor、replacement/restart/retirementcaller、真实独立producer/report/license闭包、实际 human Owner与native安装资格仍缺或未测。GMNR剩余材料窗口由单独修订case评审/Test处理，不混入此源码裁定。完整真实多模态作品、三OS安装、R1独立验收后连续R2不缩。

Review费用/密钥读取/ASR/产品运行/测试/安装均0，只写本报告和自身过程；必要相干源码读取结束，输入末核完成后释放全部reader。最终actual工具自然终态由FinalHandoff明确，不等下一实现/平台资源。原显示输出截断已保留，并按确切缺段定向补读，没有伪称截断全文可见。
