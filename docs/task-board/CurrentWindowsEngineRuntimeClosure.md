# CurrentWindowsEngineRuntimeClosure

ACTIVE，唯一原 integration_release 集成/发布角色；仅写仓库依赖/锁/基础构建配置、`packaging/`、`tools/build/`、`apps/desktop/`及自身 `Integration/CurrentWindowsEngineRuntimeClosure/` 过程。不得改 Backend/Media/Frontend/Test/Review/Acceptance 源或共享依赖、旧任务/旧包。目标是把已独立验证的 Windows FFmpeg LocalV1 资源切片推进到实际可启动的当前 Engine 私有 Python 运行环境，朝 EXE 安装闭包前进；不把准备清单称安装包。

固定输入：`Integration/LocalOwnedMaterialPackageResources/PackageIndex.json` SHA-256 `c961a30d1713b6d0306a80fdb53b0eca660dbec68bfba20fe6b4fc3b086e7b7d`、Handoff SHA-256 `9ca139b40f689987c237015a223fbaecceed3f5075e446f5357ba989221a6a16`、独立资源实测 Handoff SHA-256 `34717af12c6c8371cb59c0e483109d36ee0ec249f11c32603a757da027761dd5`。该资源包的 Backend134+Media55 是停止旧身份，当前产品源码已后续应用/变更中，不能直接宣当前 Engine 版本。现行 `services/engine/pyproject.toml`、准确锁/实际可用 Python 3.13/轮子/许可/RECORD 与原RuntimeContract 为本卡读取输入。独立 Playwright 缺1243是测试环境红，不属于 Engine；不要为本卡改共享浏览器。

第一步实查当前 CP313/隔离环境、pyproject/依赖锁与私有原29资源、历史147包/1.65GB及31/105/Pydantic19失败边界，给精准图、文件hash、native ABI、许可证正文/缺项；历史包不得整搬或借私有资格。能在当前主机从已核可分发物理资源构造**新隔离** Python 3.13 interpreter/stdlib/dependency stage时，实际构建到本任务自己目录，逐件哈希/RECORD/无secret、进程 `--version` 与必要不触旧失败的最小进程验证，保原始exit/双EOF和失败。若缺 exact wheel/许可/ABI，固定哪一件缺及可取得的合规来源，继续打包工具源码实现，不用 mock/降门。

设计并实现准确的 current Engine 源/迁移/FFmpeg/解释器/依赖索引组合器与启动器到集成白名单；Backend/Media 活动源只消费其后续停止索引，不热复制、不改已完成 203 资源包。Owner 四route/rights 和 ASR 四字段仍是私有真实绑定/WAITING，不能硬编码或用旧 env 伪资格。启动/绑定若会重做原 Pydantic19、三次 binding 或31/105同等失败实验，先保限制，不能换名称/进程壳绕做第四次；需要独立变更/新前提才设计新的有限运行验证。不得模型付费、读/复制 `.ssh`、外部部署或公开发行；FFmpeg GPL 完整对应源与NOTICE未闭合前不能宣可分发。

每阶段给实际产物/命令/exit/大小/SHA/Impact和下游独立Test所需界限。若机器/资源仍缺，精确写明，不停止无依赖安装器代码工作。最终交停源/完整diff/回滚/自然终态，不能自评 EXE/DMG/Linux或R1/R2通过。
