# DailyGoal 装配后继独立源码复审

**SOURCE_STATIC：B43-P02 仅源码层关闭；B43-P01 部分修复支持、仍 OPEN。DG-P01/P2 归 Backend。** 无产品、测试、DB、Owner、Win32、API、MCP、模型、安装或网络运行，费用/秘密读取0。

## 固定来源

唯一新源根 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/DailyGoalServiceAssembly/SourceCopies/`，88普通件逐路径/大小/SHA匹配。正式Handoff `0806d37452e82f9586f134d9838400b2212ed1eeb5a2e23d6f113fbff601f269`；接口 `17b5aaf3141fa2fd25e68785247dfed87194a04a955bc155e5e7b73887abd18a`；Freeze `18eff10e16fb9e696a029a345b40fc37f91187a3a758fc191307b8378a0b6956`；Index `a3b56848bab96071d41c86fd704d581e3d5288e3ad6f88ee2934cc1782b01bbe`。

82份同B43最终索引，6处增量。用六份原普通正文独立重构16966B patch，与声明逐字节相同：`cc312da7230df1bee4e7038ff6ce97a063696767d0e9a968fe50c3ace068b4d9`。78份Python文本仅经stdlib AST解析；旧main/_request AST不变。六处完整源码和相干服务、资格、连接、事务正文已读；不依赖作者摘要判通过。

107输入中106未变，只有任务卡被统筹在读窗内追加状态/候选排期：3529B/b53d5931e8bae34f7b22b82e33b1de5c4cd73c106e93c21104d3614bfb48dc3c→4250B/29944dd07b8bc4597acc45136c0700ed31c1e204666f3f5d643380994038a0ab。原fad2b8/1 input guard失败与before/after保留，不能称107全绿。新增卡未改源版本、顺序或标准；定向读完并独立保存TaskCardAfter。原97b3dc/1因评审猜不存在Handoff.json，实际正式件是Handoff.md，定位纠正。合并输出396867/b2402d部分截断，已只补遗漏源码段；这些不是产品失败。

## B43-P01 与 DG-P01

新native_owner_setup.py:237完成原内部setup binding；:242在Goal等待后重核原Engine/Database/file/metadata，再把同concrete初始化source送入唯一continuation/确认consumer。native_instance_source.py:163–207保持同对象、原文件inode、实际metadata，缺失/变值拒409，无INSERT修复或重新Engine。内部setup完成只撤初始化20s条件，保原OS/current与后续人审/setup期限。

owner_setup_confirmation.py:75–87把实际writer连接传入原初始化source；owner_setup_service.py:145/164包围首journal INSERT，:179/186包围prepared UPDATE，失败在原事务中rollback。这些窗口有明确SOURCE_STATIC修复支持。

**DG-P01 / P2 / Backend / OPEN，未DB/OS/并发实跑。** 固定owner_setup_service.py SHA `3b8f06f1bb7784965f99b690b3be70ccd9f2f48f71101235a04a7c5d575e0178` 的:165外部检查后，:167调用原Engine.create_project。engine.py:228–239的另一独立writer INSERT projects/commands，不接初始化source、不查metadata；database.py:165–167正常commit。如果外部检查成功后、该writer前metadata改变/删除，草稿/命令可先提交；:177才409，不能回滚上一事务。

接受路径同类缺口：service:254–255外部准备检查，:267–274仅confirmation.assert_local_current后写accepted_json。owner_setup_confirmation.py:123–129、native_owner_confirmation.py:316–326只核原OS/member/deadline，没有这笔连接的metadata或initialization_source。于是外部检查后的实例行变化可先存旧实例accepted状态，再在执行检查被拒。不是声称已得到管理/安装权限。

任务卡要求原连接短writer effects前后关联；ADR0042:48/62保原实际身份与行变更拒绝。Backend应在这两个原私有effect路径提供同retained source/实际连接前后验证，由原事务拒绝rollback；保普通项目API、合法journal/草稿、原body/key/floor和期限，不全局hook/修metadata/新Engine。早Finding `BackendEarlyFinding-DG-P01.md` SHA `7106a9747f8c35f5ca9f5421b1423728f04dafa2fdb701ae4d70c405e4958bd8`。后继Test须真实合法source阳性、writer前后行改/删/换文件、确切409及该writer无新project/command/accepted提交；不得造授权或改历史红。B43-P01不能整体关闭。

## B43-P02：CLOSED_SOURCE_STATIC_ONLY

native_owner_setup.py:143–148只在ControlPipe拥有边界将原control_pipe_required映射为owner_instance_handshake_invalid422；固定lifecycle.py:81–86原非pipe路径恰control_pipe_required400。其他EngineError原样raise，:247–250输出原event/seq/code/status；不放宽Native oracle，真实schema/migration例外不变。只关闭原具体源码接缝；合法来源+实际非pipe、错误字节、真实migration未测。

## 同一 Daily/ready 来源支持与缺口

owner_services.py:80–150继续同Engine/Bundle/domainOwner/bootstrap/八字段注册投影、actual authority；:138–141构造原一个DailyProjectService，仅actual registered时配置。startup_services.py:56–91核原执行服务、role/authority/connection，拒management/vault registry。

新installed_principal_id:106–129要求exact retained StartupInstallation，同Engine/Bundle/role/注册对象/Daily/issuer及owned_projects，经过admissions.current_guard后返回Bundle原Owner文本；不是renderer、OS SID或新cap。CLI main:326–332只在真实installed对象存在时增加principal_id；ordinary serve无此身份。该guard调用真实installation.observe/current，native_installation.py:50–61对not_ready或缺qualification_issuer拒503，而native_startup._factory:32–34尚未注入实际issuer。真实独立qualification producer/injection仍缺，不能凭descriptor/SHA/bool称qualified服务。

B43-I01/P2 stdout同步write/flush:180–181无可中断completion仍OPEN；I02/P3 pending只看Python已读字节、OS queued提前Goal边界仍OPEN。Windows原child/Job/双EOF、正常初次Goal与两个后继日常Goal、真实Owner人审/恢复、媒体多模态作品、三OS安装未测；macOS/Linux peer仍503未实现。完整R1独验后连续R2不缩。

## 交接

过程 `G:/开发测试/Codex/VideoCreatorImplementation/Review/GoalSourceFixIndependentRecheck/` 的InputSnapshot、BackendSourceFacts、BackendIndependentDiff、BackendInputAfter保完整路径/SHA和原失败。Backend固定源读者已释放。后续Frontendcatch复审另报告，不混其证据关闭本Backend问题；不授RuntimeBinding/运行/安装/验收/Gate。
