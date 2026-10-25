# RV14：T14 候选修订2实际标准与夹具独立审批

2026-10-08，永久独立评审，FINAL。**批准 `gate0-local-recovery-phased-evidence-v1` 的候选修订2，以及下表精确十份拟执行文件作为本窄K/R/N复验的标准/夹具版本。** RV13-P01/P02的静态标准覆盖缺口在这一固定版本范围内关闭。RV11-P01产品恢复问题仍P2 OPEN；标准门批准不是产品执行、修复、技术Gate0、R1/R2或独立AV通过。

实际测试仍须统筹对最终停写B7/W7源/资源精确冻结并明确准launch；任何候选漂移要新hash复审。不得继承已拒绝的RV13候选1批准标志，不能提前运行或把标准批准倒填旧红。

## 精确批准单位与来源

RV14卡 SHA `3a1752705276b596e7717b4dfcc2c1623c05f67097fcf0665fb1dbfa5da9cf2f`，AGENTS `6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`。

修订2 Handoff JSON `a85ab7966d51be5c3117c748ee3ab5438dbb779e0710e833d4d10de0868c6fbd`、MD `145f40faf6b384947448fab4453d775ac3e49cb2095dab9b490b92f7fe7fb6ab`实际匹配。规范JSON明确candidate_revision=2、RV14审核及当前manifest；有效清单是 **T14PhasedFixtureVersionsRevisionTwo.json**，替代旧候选1的1b752948清单。MD前段沿用的旧泛称清单名不作为运行身份选择，以本表和规范JSON的RevisionTwo精确路径/hash绑定。

| 批准文件（repo相对路径，manifest为Codex过程文件） | SHA256 |
| --- | --- |
| docs/acceptance/criteria/gate0-local-recovery-phased-evidence-v1.json | 87e1e9d1f9d495ad97985df644591545ad1d93a7a935a1ddbd10cd79dd8bf927 |
| docs/acceptance/criteria/gate0-local-recovery-phased-evidence-v1.md | 03d00c495ba732184cafebf745ba80c6530f5bada2ca925ab17a685813e1ef75 |
| TestDevelopment/T14PhasedFixtureVersionsRevisionTwo.json | a7382bc0590b28d0ad40b0c376e34f1b66074aacee9d69689c4283e702ba0cc1 |
| tests/gate0/t14_process_helpers.py | fcfaff96a9bbd9d35d39ad99f7419a3f823af28819a774883d4b61dd119b9db7 |
| tests/gate0/t14_evidence.py | c91f05efdd92db5fb4a283c7305c4d735adc6aef84012801ee4b9a36a411bb9d |
| tests/gate0/t14_phased_assertions.py | f7436124fa7927e2fa5bb15f7353b3aeb97fb0f1aa4864750cf6aae44689a72e |
| tests/gate0/test_t14_recovery_phased.py | e44654f749d4a1faae675a1cc9f8295156a146f483f67a94be0e1de44b59ed28 |
| tests/gate0/T14Fixture/PhasedTrace.py | cb60cdbef4b47e2b69db48f8c7ab6a1f0de2cae07334081ffc8920a9939775ea |
| tests/gate0/T14Fixture/PhasedWorker.py | fa86095584df33235d4a18ad456ab62f09e0111fa3b1ecb3c7eddd2a6435a728 |
| tests/gate0/T14Fixture/SuccessLatch.py | 5a7f33533e9be3013064d40fff1214be03d5b02661d5c66a839dcb688cca0a56 |
| tests/gate0/T13Fixture/OwnedSibling.py | e8db5d8c8f35e96ce139644268ccb8449c9c4f70482dc487de583ce8d04556ab |
| tools/testing/run_recorded.py | 5094d5829d7e1a76540334d1f48763d18836c581b907ac2af89124e8a5bfdbba |
| tests/gate0/T14Fixture/ProbeTrace.py | 71637068ae8f323f46f81d6157515d34bc6936c49cf2ba04544806bae00ac198 |

十份实际文件hash/字节均匹配，UTF8/LF无BOM。实际读全部候选文件，改变部分按正文审；五个未变依赖与RV13已保存同hash正文一致。纯sanity工具不在本十文件拟执行产品case单位，不授予重复运行它的要求。

已保存固定 `Review/RV14Snapshot.json`，SHA `f273c2cb7f216e0986473d6681f054da76067b6131a49d944d6570ce99df43f4`，包括实际十源全文、规范/交接、30普通副本核对及sanity范围说明。本报告只用该固定快照，所有读取终态后停止候选读取，不追后续生产修改。

## RV13-P01：原probe文件关联缺口，固定标准范围关闭

`ProbeTrace.py:9–28`仅对原decoder受控Staging内有限文件被动stat/hash，不读目录外目标。`31–56`每次原probe调用生成唯一call_id，记录PID/targetRun/规范化path及真实hash/size/mtime前后、decode_requested、原返回probe；原probe恰调用一次，不额外FFmpeg调用。原异常重抛，记录失败只附异常说明，不替原结果或擦失败。

`PhasedTrace.py:44–46`实际安装这个包装；`t14_phased_assertions.py:26–63`配对begin/returned/raised调用，要求R预期PID/Run、精确K文件path、inside_staging、前后完整指纹相同、真实decode_requested与decoded video/mp4/4秒/720×1280/v+a。只解码别的文件即便同字节或规格也不能满足精确path要求；错误/变化的原目标亦失败。`assert_R:86–104`进一步绑定K唯一attempt/staging及Operation完整manifest、MIME/source/rights，主case真实调用assert_R。

因此原“任意decoded=True即可替代原文件解码”的静态标准反例已被修订2排除。该结论是代码/规范可区分性审批，未由评审运行probe或实测R恢复；未来原decoder运行/计时/错误路径仍按真实结果记录。

## RV13-P02：N有序产物关联缺口，固定标准范围关闭

`assert_N:129`实际调用新增 `assert_media_lineage:132–230`；主case将真实Kflows/Nflows与包含creative_revisions的只读snapshot传入该接口，并继续使用自己的受控字节副本独立decoder。

新增关联按step逐项核：Operation的run/production/input→原有序generated_files→allocation attempt/staging/output_key/input→imported staging及owner/size/hash/MIME→staging.asset_id的真实Asset owner/hash/size/MIME/source/rights→Step有序asset_ids及result manifest。五份输出Asset ID必须各自唯一，不能用同规格视频交换Step引用、共用Asset或以孤立记录凑数量。

接着由真实Plan Step/revision与固定Binding canonical hash导出预期Flow UUID；逐checkpoint核id/run/binding/planrevision、镜头有序prefix、compose video/mixed输出、review_pending和Run等待revision；真实quality revision的plan与有序产物须一致。UUID/行数相同但run/binding/输出顺序错误不再够用。主case还对每个Asset字节复制前后hash/size及真实decode/MIME/时长/画幅/音频分别断言，metadata关联没有替代解码。

因此原同为3秒shot2/shot3交换/共享refs、以及错误Flow引用能够只凭数量/规格通过的静态缺口在该版本排除。本结论不声称产品实际已生成这些正确关联，也不证明所有未来profile/模型交付。

## 原保护与授权链保持

- K原一次真实render、1 submitting/unsettled Operation、1 ready完整allocation、无partial；原PID/Creation/树及文件指纹即时落盘，再真kill和真实墙钟越租约，未改clock或由测试补业务SQL。
- R包装真实finish_reconciliation原方法成功返回后才闩停；queued/workerNULL/lease0/idle来自后端。保原Op/allocation/fence/binding/已有Step/Asset/Flow及文件identity，render/allocate/Asset/Step新增量0，decoder与生成分开。没有放宽普通grant写权限或代执行核实。
- N正常新fence严格大于R；同Run/Binding/Flow继续到真实quality等待释放lease；5Step/4结清0元Op/5allocation只用于这个无feedback/approve三镜profile。原shot1不重render，其余两镜及compose各一次，原Operation成功manifest和完成文件不覆盖；允许后续合法imported/asset_id及Step正常新fence。
- 旧12秒窗口/原红保持。当前K/RN Worker70秒、quality55秒、K/R闩30秒、真实lease等待40秒、natural wait85秒仍显式版本化，不改成生产SLA，不用CLI0替业务成功或无限延时。
- main与PhasedWorker都要求`independent_criteria_approved`、criteria_revision=2、criteria_review_id=RV14、root_launch_authorized；未复用旧rv13_approved标志。实际运行前必须以本报告精确hash建新freeze，包含最终生产/依赖/工具/资源；不能仅凭同名v1或布尔值自签准入。

## 归档、辅助sanity与未测

候选1归档manifest SHA `41c84e1219fcdbea3ee91dc3dec16c09a9e4cf84703e91804ad034d5bd8f23fb`、候选2普通副本manifest `483936a74ac4f7aa5b241ae445c4d19d0650f4011155dfa97d172bbfd27c9158`，各15份副本逐hash/size全匹配声明original/copy。旧RV13 Snapshot `ca1501c3862a26713a52a7c5718d049b0dbeb283b000004c0de25fff2ee5e3c4`、原03966测试及T13产品红XML `8a0b59334e1e82b7a9499388b810b900151e4c7228f118074f9ff118f119af91`保持，未覆盖旧不批准结论或旧字面断言。

辅助sanity receipt SHA `8028648bb45ab38996164d7670620a2c9ca8ec8ebdf86ea0e8356e3d6f24d9a1`、原stderr `1e01ade121999b69c049e39245b6306c0539b0505cd8c0f34b01420969bf6738`实际记录4 tests/0.678s/exit0；synthetic字典、纯夹具字节、fake callable，没有产品import/CLI/真实decoder或SQL业务。仅辅助判据辨识，不是产品绿。**receipt实际before/after只有5项（4份源码+Python工具），并非Handoff所称6；5项身份无变。** 这是非阻断交接计数说明，本报告按实际5记录，未修改冻结材料或要求重复sanity。

实际K/R/N运行、进程时序/闩窗口/异常清理/解码与B7/W7实现仍待测试；partial/多输出/缺失/篡改、旧fence、取消不复活、幂等/异证据冲突、公平性、Step已成功未Flow及其他反向独立样本不被此标准批准外推。模型自主作品、完整Bundle/RAG/Portal/MCP、三OS/安装/商业、R1独立验收及连续R2目标保持。

本轮仅关闭RV13两项固定标准问题，**RV11-P01产品问题仍OPEN**。评审自身运行测试/AST/产品/解码/看听/key/收费均0，源码/标准/测试改动0，仅Review白名单写入。正式FINAL释放槽；不等待实际T14，不代实施或验收。
