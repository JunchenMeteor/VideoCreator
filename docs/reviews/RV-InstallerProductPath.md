# 安装包与产品路径独立评审（RV-InstallerProductPath）

**结论：OPEN_P1_BLOCKED。** 安装/授权/重启/受理这一段真实跑通，且产品 API 的 management 门、页面不泄 token、V9/V10 的**已测产物**大体成立；但严格按“用户双击安装 → 授权 → 制作 → 发布 → 取片”的 R1 线和“非安装器写入”的信任边界，发现两处 P1：

1. **安装记录/安装清单没有外部签名锚**：`InstallManifest.json`、`InstallRecord.json`、provisioning record 都是同目录可写文件；launcher 在启动时**现算** record SHA 并把它交给 `product-serve`。我实测：在临时硬链接安装树上加一个 `AsrPackage/Tamper.txt`，不改 record 会被 `trusted_startup_bytes_changed` 拒绝；但把 record 的 `AsrPackage` tree 摘要同步更新后，`product_host._check_record` **ACCEPTED**。也就是说，同 OS 写者可以“改文件 + 改记录”伪造安装，trees 摘要只防意外/非同步篡改，不是安装器信任根。
2. **R1 产品链没有闭环**：安装器只启动 `product-serve`，不启动/安装 `product-worker`；`POST /productions` 只得到 **202 queued**，没有执行、成包、发布、取片。Handoff 自己已承认 `product-worker` 未启动。以“制作 → 发布 → 取片”为验收线，当前只到“受理”。

## 1 逐条核验

| # | 必核 | 结论 | 证据与实测 |
| --- | --- | --- | --- |
| 1 | 信任边界：改记录/加文件/挪目录/跨实例/换注册是否拒绝 | **P1（改记录）** | `install.ps1` 只按同目录 `InstallManifest.json` 复算每个文件；manifest 自身无签名。`Launcher/launcher.py:48-67` 读取 `Control/InstallationProvisioning.json` 后**现算** `_record_sha256`，没有外部 pin；`:176-179` 把它传给 `product-serve`。`cli/product_host.py:32-84` 只验“record SHA 与传入 SHA 一致 + 记录内 bytes/tree 与实际一致”，不验 record 来源。我的实测（硬链接复制 InstallC + 原 DataC，直接调 `_check_record`）：baseline `ACCEPTED`；加 `AsrPackage/Tamper.txt` 不改 record → `trusted_startup_bytes_changed`；同步更新 `AsrPackage` tree 的 `file_count/bytes/sha256` → `ACCEPTED`；把 install root 换到不存在路径 → `trusted_startup_instance_conflict`。`installer_provisioning.py:204-247` 的 `provision` 只要求四个授权表为空、无 owner binding；没有安装器身份认证，删除 record 后可重新 provision。**记录/清单/ACL/registration 都可以被同一 OS 写者一起改写**；未改 record 的加文件、挪目录、跨实例路径冲突会拒绝（PASS 部分），改记录后不再。 |
| 2 | 执行权威是否只授予该授予的；product-serve 能否管理 | **PASS（management 门）；P2（product-serve 执行装配）** | `product_host._factory`（`cli/product_host.py:104-133`）只允许 `for_management is False`、无外部 runtime，管理 registry 不装配；`api/app.py` 的 `management_access` 先拒绝与安装 token 相同的 Bearer。我用真实 app 请求 `GET /api/v1/local-copy-input-scopes/scope-x/revisions/1` 与 `POST .../install`（仅安装 token）→ 均 **403 production_management_denied**，与 `Tests/managementC.json` 一致。产品授权 approve 不再建 management secret（P1-1 修复），management registry 403。P2：`_factory` 把 `execution_registration` 传入 `assemble_owner_services`，API 进程仍获得了执行主体验证/受理路径；本卡只要求 product-serve，产品 worker 未启动，执行权威未做端到端负例。 |
| 3 | 页面/launcher 是否泄 token/secret | **PASS（已测产物；P3 history）** | `Launcher/launcher.py:162-181` 的 token 只进引擎环境，`:214-220` 只打开 `#a=<secret>` fragment；stdout 的 `launcher_ready` 只有 `url: http://127.0.0.1:18123`（无 fragment/token）。`apps/workbench/src/productAuthorization.ts` 从 fragment/global 取 secret，`scrubFragment()` 用 `history.replaceState` 清掉；`workbenchBootstrap.ts` 只读 origin、不读 token。`Tests/page-authorize.out.json`、`launcherC*.stdout.log`、`InstallC/Workbench` 均无 token/secret 字样。P3：`webbrowser.open` 的 fragment 在页面替换前可能短暂进入浏览器历史/截图；`VIDEO_CREATOR_LAUNCHER_SECRET` 可被同用户环境读取；测试脚本 `Tests/page-authorize.js` 用 argv 接收 secret（非产品路径）。 |
| 4 | V9/V10 判据是否可信 | **P2（判据过窄）** | V9 的原判据只扫安装根 `*.json`/`*.cmd`；我递归扫到安装树内 `Package/Code/video_creator/cli/development_host.py`、`development_owner_initialization.py`、`cli/main.py` 等含 `--development-registration`/`serve-dev` 源码。`Engine/VideoCreatorEngine.exe serve-dev --help` 确实 exit 2（PASS 的这一条），但“安装树无 dev 串”不成立；源码副本是安装包内容。V10 只扫 64-hex：launcher token 是 64-hex，所以能覆盖当前 token；但 authorization secret 是 **32-hex**，base64/url-safe 形式（页面 `isSecret` 明确接受）不在判据内；Workbench 的 64-hex 命中是契约常量而非 token。当前页面/日志实际无秘密，**但 V10 的“无 token/secret”结论不能由该判据外推**。 |
| 5 | R1 完成度（双击安装→授权→制作→发布→取片） | **P1（未闭环）** | 真实已验证：安装+provision 105 s、InstallC/DataC、页面授权→重启→`/projects` 200、production 202、management 403、tamper 检出。**未验证/未实现**：product-worker 启动、production 执行、bundle 发布、下载/取片；因此“制作→发布→取片”缺失。详见 §4。 |

## 2 P1

1. **伪造安装可过**：安装清单/记录/ACL/registration 没有外部签名或安装器身份；launcher 现算 record SHA，product host 只验本地记录与实际 bytes 的一致性。我的“加文件 + 同步 record tree”实测 `_check_record` ACCEPTED；删除 record 后 `installer-admin provision` 也可重写。**“只有非安装器写入”不足以阻止改记录**。
2. **R1 产品链未闭环**：`product-worker` 未安装/未启动，202 只是 queued；没有执行、publish、取片。验收线未达到。

## 3 P2

- **V9**：安装树含 dev 源码副本；“安装根 root json/cmd 0 命中”不等于“安装包无 dev 串”。
- **V10**：只测 64-hex；secret 32-hex、base64/url-safe 未覆盖；Workbench 的 64-hex 是契约常量。当前产物无泄漏，但判据不足。
- **安装器无代码签名/无 Tauri/无自动更新/无卸载**；安装 manifest 与 record 无签名。
- **`product-serve` 执行装配**：`_factory` 仍传 execution_registration；虽然 API management 403，执行权威的边界没有端到端负例。
- **ASR/本地自签证据**：产品页面只做 Owner 授权；`evidence-admin install` 仍需手工 CLI，双击安装→授权无法自动完成语音证据安装，语音作品路径未闭环。
- **测试**：`tests/development` 35 pass/1 skip 未覆盖本安装路径；安装/记录/篡改/management 证据主要是外部 `Tests/` artifacts，不在仓库回归。

## 4 R1 缺项清单

1. product-worker 进程/服务未由安装器或 launcher 启动；production 202 后无人执行。
2. 无生产执行→bundle published→manifest/artifact 下载或播放的实测链路；“取片”未达。
3. 无产品内的 `evidence-admin` 一次性安装触发；语音证据/ASR 仍停在手工 CLI，带语音作品未闭环。
4. 无安装器/安装清单/记录/更新的签名信任根；无 Tauri 桌面壳、无代码签名、无自动更新/卸载。
5. management（policy/route/floor/secret/binding）仍是独立 Owner 管理路径，未产品化；当前只验证了 403 拒绝，不是完成。
6. 仅 Windows per-user；macOS/Linux、安装回滚/修复、服务生命周期未覆盖。
7. V9/V10 只是窄扫描，不是安装树完整性/秘密泄漏的充分证据。

## 5 真实复验记录

- 临时硬链接安装树 + 原 `DataC`，调 `product_host._check_record`（未改 deliverable）：
  - baseline：**ACCEPTED**；
  - 加 `AsrPackage/Tamper.txt` 不改 record：**REJECT `trusted_startup_bytes_changed`**；
  - 同步更新 record 的 AsrPackage tree：**ACCEPTED**；
  - 不存在的 install root：**REJECT `trusted_startup_instance_conflict`**。
- 真实 app（仅安装 token）management：`GET .../revisions/1` → **403 production_management_denied**；`POST .../install` → **403**。
- `Engine/VideoCreatorEngine.exe serve-dev --help` → **exit 2**（入口不存在），但递归安装树含 dev 源码串。
- 页面/launcher artifacts 无 64-hex token/secret；`#a=` 只出现在 launcher 的 fragment 与页面 bootstrap，`page-authorize.out.json` 的可见文本无 secret。

## 6 越界

- 本批实现/交付路径：`application/product_installation.py`、`installer_provisioning.py`、`cli/product_host.py`、`apps/workbench` 前端、`tools/build`/安装器 artifacts；均为对应角色路径。**未发现源码角色越界**。安装器交付物未入库、未签名是交付形态事实，不是角色越界。

## 7 最终

**OPEN_P1_BLOCKED。** 对“能不能被伪造安装或越权管理打穿”的直答：**伪造安装：能。** 改安装 record（并同步 bytes/tree 摘要）后 `_check_record` 接受，安装清单/记录没有外部签名锚；**越权管理：未打穿。** 真实 app 的 management 门返回 403，product 来源无 management secret。另有 R1 功能 P1：没有 product-worker/发布/取片，202 不是 R1 完成。
