# I28 私有索引运行时接口

状态：源码候选；未构建资源、未启动 bootstrap/产品、未编译本次 Rust 源。I26 旧 StageMoved 与 I27 已生成契约保持原身份。本接口依据 ADR0023，不授予发行、DLL 命名空间、干净系统或三平台资格。

## 可信构建与身份

唯一 builder 为 `tools/build/BuildIndexedEngine.py`，只用标准库，不导入 engine。输入是精确 I26 资源索引及其 Installation SHA、同源 Backend ordinary snapshot、实际 contract export freeze、生产 uv.lock 与各自 SHA。输出必须是自身 owner 下不存在的新目录；原 Stage 不改。

builder 完整复制原物理文件与 package data，overlay 同一个 Backend snapshot 的所有源码/迁移。主环境必须保留 147 个生产传递依赖与一个内部 engine metadata；完整 dist-info、RECORD、entry_points、来源文件 SHA 随索引保留。不是静态 import 图裁剪。碰撞、缺件、未知基线成员或 source 漂移保非零及部分产物。

新目录包含：

| 文件 | 消费方式 |
| --- | --- |
| `InstallationManifest.json` | 私有 `native-engine-installation-v2-candidate`，可信 native build 嵌入全文 SHA，不能由 renderer/env 提供可信根 |
| `LoadPolicy.json` | 私有 `portable-engine-load-policy-v2-candidate`，Installation 包含相对名及 SHA；每一个 policy file 必须是宿主已 hold 的相同 SHA/size |
| `IndexedFileManifest.json` | 全文件 provenance/index，不自发运行或许可资格 |
| `Bootstrap/BaseStdlib.zip` | 同一 CPython 纯 stdlib 与固定 bootstrap 模块，ZIP_STORED，不把全部第三方塞 zip |
| `Bootstrap/IndexedBootstrap.py` | 固定主脚本；不得换成任意 module 或 shell |
| `Provenance/uv.lock` | 完整生产锁的固定副本 |

Installation 固定 `artifact_version`、`backend_snapshot_sha256`、`contract_freeze_sha256`、解释器、archive、bootstrap、LoadPolicy、Migrations 五文件以及 FFmpeg/probe。LoadPolicy 不反引 Installation 自身 SHA，两个文件没有循环摘要。旧 `EngineFileManifest.json` / `CandidateInstallationManifest.json` 只是保留的输入 provenance，不能冒新可执行配置。

## 四个启动 profile

| profile | 固定 entry | 原 CLI command |
| --- | --- | --- |
| api | `video_creator.cli.main` | `serve` |
| worker | `video_creator.cli.main` | `worker` |
| mcp | `video_creator.cli.main` | `mcp-stdio` |
| asr | `video_creator.media.asr_worker` | 无；保原 stdin 数据 ABI |

每个 profile 独立记录解释器/CPython 3.13.16 ABI、实际 builtin/frozen 表、完整 module/有限 namespace portions、metadata/data/native/工具及迁移身份。现输入是 B18/W14 历史固定候选，未混 B17/W15/B19 活源。后续新源/迁移/profile 要另建新版本，不能继承此源阶段声明或旧 ASR method qualification。

可信 Rust API `LaunchResources::prepare_role(role, instance, private_token, arguments)` 返回 `PreparedLaunch { executable, args, environment, guard, source_carrier }`。只能由可信 Rust consumer 调用；不供 renderer spawn，不返回 bearer/base URL。每个独立 Worker/MCP/ASR consumer 必须把 guard 保留到实际 child 终态，不能随主窗口或 API 关闭提前 drop。当前 API 源已接入这个准备路径；其他 consumer 与产品生命周期还需独立衔接验证。

固定启动 argv 为：

```text
<profile executable> -I -S -B -X utf8 <Bootstrap/IndexedBootstrap.py>
  --installation-root <host-held root>
  --load-policy <root/LoadPolicy.json> --load-policy-sha256 <host-held digest>
  --profile <api|worker|mcp|asr> --system-directory <actual Windows System32>
  --native-source-context <private immutable carrier> --native-source-context-sha256 <host-held digest>
  --data-root <trusted instance> --data-root <instance/Temp>
  -- <original fixed role command/arguments>
```

环境闭集从实际 Windows 系统 API 取得 SystemRoot/WINDIR/COMSPEC，保 TEMP/TMP、固定 `VIDEO_CREATOR_MIGRATIONS_DIR` 和必要私有 child 会话值。portable 不依赖 PYTHONPATH，不继承 PATH/site/customize/加载环境。Win32 canonical 本地 drive 前缀只在传入严格 Python 领域接口时正规化；UNC 不放行。DataDir/TEMP 不进入 module/metadata/DLL 搜索域。

## 实际加载规则与边界

`._pth` 在 guard 前只开放固定 archive。启动 hash 要求精确 CPython 提供 builtin `_sha2.sha256`；缺失就报明确失败，不能先找外来 crypto DLL。bootstrap 核 LoadPolicy 原 bytes SHA 后才安装唯一 indexed finder，再 run 原 entry。

source 从已核 bytes compile，不取未知 pyc。namespace、pkgutil、metadata/entrypoint、importlib resources 只枚举已登记记录；第三方物理目录/数据保留。扩展及受控 ctypes 请求先验证相同 native 索引与静态/delay 关系；FFmpeg/probe 连同同目录 DLL siblings 纳管。未知 fullname/resource/native 请求不回退 PathFinder/CWD/PATH 或临时安装。

Windows search 设置不等于 C/native 任意系统调用 sandbox；ResourcePins 也不能阻同用户新增目录项。bootstrap 前 CPython 依赖、系统/CRT 来源、动态 DLL 分支、147 包实际兼容及 POSIX guardian 均还要真实验证，不能用一次扫描、audit/postload 或 JSON 字段替代。

## ASR 消费缺口

新 Stage 要重建 LocalAsr RuntimeFileManifest 与 ResourceManifest，纳入新 `python313._pth` 并把旧 execution qualification 清为 not_admitted。原模型四 SHA、provider/worker/loader 源身份保持；不覆盖原 Stage 或更换 ABI。

历史固定 `local_asr.py` 的 `run_local_asr` 使用 `python -I -B -X utf8 <worker.py>`，不能消费上述 indexed bootstrap profile，新的 guard 会明确拒绝这条裸子进程路径。媒体 owner 下一片需消费可信、同根/同 SHA 的 child launch 数据及资源 guard 生命周期；Integration 不修改其业务源或猴子补丁改 Popen。只有这个接缝实际修复/验证后才能称 ASR profile 已接通。当前后端/媒体完整自动制作也未因此获得运行资格。

交给 Media 的具体输入是可信 consumer 构造的私有 launch descriptor，不是模型或 renderer 提供的自由 argv：

- 当前已持有 Installation 全文 SHA、LoadPolicy 路径/SHA、artifact/profile 身份；从同一个已核 `profiles.asr` 取得 `LocalAsr/Runtime/Python/python.exe` 和 `LocalAsr/Code/video_creator/media/asr_worker.py` 的 size/SHA。worker entry 固定，不能用绝对脚本替换。
- 共享 `Bootstrap/IndexedBootstrap.py`、BaseStdlib.zip、两个解释器的 `._pth`、完整 ASR module/native/resource 索引均属于同一 held installation。`LocalAsr/ResourceManifest.json` 与 RuntimeFileManifest 各自的实际 size/SHA 由该安装身份取得，四模型 SHA 从既有受信配置消费。不存在 renderer 自报 SHA 授信。
- trusted launch 构造使用上表的 `profile=asr`、闭集环境、实际 System32、与资源无重叠的 runtime/TEMP 数据域及原 owned stdin/stdout/stderr 管道。最终 argv 在 `--` 后不追加脚本、module、模型自由命令。私有描述符必须在 API/独立 supervisor 已保持同一个 ResourcePins 生命周期后才能交 child，接收者不能从普通 JSON 字段 `qualified=true` 或 root 名称推导准入。
- Media owner 在自己的边界把原 `python_executable` 裸 worker 启动改为消费上述固定 launch 数据；host/独立 supervisor 保持 guard 到真实 child 和受控后代终态。若 Media 自己持有子进程，则先定义/验证实际 guard 所有权转移，不能仅因 Python open 成功称等同 Rust held pins。

取消、deadline、超时、输入音频 SHA、模型四 SHA、execution identity/configuration 以及原 local-asr-v2 stdin/result/progress 坐标 ABI 均沿原 Media 控制，不由 bootstrap 解释成新业务命令。不得将 EOF 当 cancel、放大重试/费用额度、重造结果或继承旧 method qualification。上述 descriptor/profile 是本次源接口，消费者仍未实现/运行；下一片由 Media 定义所需私有类型并固定版本，Integration 再按其正式源构建新 artifact。

## 下一批与未测

资源构建、boot、native 编译与真实 API/Worker/MCP/ASR 每批先固定全部输入/工具/依赖/argv/env/write 范围及 owned 终态，再按任务准入执行。源码阶段只做 AST/文本/接口检查，不把这些检查当 runtime。原 I27 TypeScript7 compile0 仍保留 native tsc.exe 当时未被 Node trace 捕获 SHA/PID 的限制；未来实际构建须固定它。

CRT、PyAV/BtbN source/NOTICE、各包/模型/font 分发许可及干净 Windows/macOS/Linux 证据保持 pending。完整 R1 自主制作与三平台独立验收后连续 R2，未缩成永久 unavailable 或仅 health 的应用。

## I30 私有 v2 来源与启动绑定增量（仅源码）

三组规则在 builder、bootstrap、loader、Rust 使用同一 `portable-engine-load-policy-v2-candidate`，拒旧 v1 和未知格式；新增 `WindowsNativeContracts.json` 是可信 build 的 exact 声明来源，官方依据与支持/许可 pending 不能当系统事实。原 I29 资源/各红批、B18/W14 五迁移基线均不回填，本次未执行新资源 build/boot。

`system_contracts` 的每个 importer/profile/static-delay edge 引 exact id。宿主在 Python 前通过实际 OS API取得 Windows/System32/build，核 metadata carrier 当前 loaded handle 路径、目标 PE/bytes/物理 file identity、Microsoft WinTrust embedded 或 exact MS CatRoot catalog。cache-only/未核在线撤销、未知最低 OS build、未知 VC toolset floor和未授权 redistribution 分列；VC/MFC 源算法读取实际 file version并比较明确 floor，缺 floor 仍拒，不能用系统名字或 prefix 免检。

collector 新增 `version.dll` metadata API carrier，下一事实执行 Plan 必须明确加入；其余 carrier、API-set target 和实际 catalog 文件也不能由 source批准隐式取得运行授权。API-set v6 只取唯一默认映射，不猜 importer-specific 多目标；不支持分支报缺证。catalog 每目标首个候选（不复用已释放枚举 cursor），exact `{F750E6C3-38EE-11D1-85E5-00C04FC295EE}` 域、128MiB累计 budget和只读句柄保留；后续其他catalog需明确版本而非无限试探。

carrier 在 CreateProcess 前 create_new、全文 SHA 和只读句柄固定，含实际 collector observations、host PID/creation 与 profile/artifact/policy。Windows child suspended → Job assigned → GetProcessTimes 后，可信宿主私有 hook 对唯一 owned stdin 写入 `NATIVE_SOURCE_BIND ` + strict ASCII JSON + LF、总长≤1024B。八字段是 host_pid/host_creation_filetime/child_pid/child_creation_filetime/profile/artifact_version/policy_sha256/context_sha256。私有 pipe 明确4096B容量；真实失败/超时和平台保证仍须实际 native批，源码声明不是实证。

bootstrap 用 raw stdin 逐 byte 消耗仅绑定帧，拒EOF/oversize/CR/非ASCII/duplicate或unknown keys/类型/身份错配；不会预取隐藏后续API os.read/MCP/ASR数据。不产生ready/echo/token输出。builtin hash核carrier完整性，actual PID/PPID先核；trusted `_ctypes` 准入后再核 GetProcessTimes、loaded module路径和实际 volume/file index/mtime。SHA/JSON并非认证或新信任根，真实宿主ctor/held source guard才是前置条件，同OS恶意root隔离仍未证。

有限 alias 只含固定 hashed MSVCP：主 profile canonical为numpy.libs、re2 requested member与RECORD保持；ASR独立根不借主runtime。源码核两个member SHA/size/machine/static-delay closure/owner，注册alias/SCC数据，预载前检查同basename已载handle实际origin，canonical预载和后查都保存真实origin。DLL初始化可能先于Python postload核，不声称全部native执行前sandbox。

条件目录只给固定CT2 4.8.2 CPU源码实际compiled code object及其递归对象（strong reference与object identity，非co_filename/模块字段）。两个exact缺目录直接FileNotFoundError，不调用OS、无cookie；已存在未知内容拒绝。正常已登记目录cookie由resolver保持，来源guard/PreparedLaunch由API或独立可信consumer保持到owned child/tree真实terminal。此源码尚未证实cookie关闭竞态、父崩溃、四profile真实兼容或Windows生命周期。

新的 `tools/build/native-system-facts` manifest复用同一collector/现locked crate版本，工具只接受固定36 exact名字与声明源SHA，未知来源条件保错误；当前尚未编译或运行。事实执行/编译完整工具依赖、目标physical pins/catalog动态授权边界和实际MinOS仍必须独立准入。完整147/24、FFmpeg9PE、CPU ASR86PE、四profile与数据/metadata能力保持；产品/ASR监督传输尚未全部接通，不能用source/static替资格。

## I32 两个评审修复的源码语义

I31原两编译EXE/锁/raw保留，仅编译成功不授系统事实。RV37-P01/P02是静态缺口，本段描述新source，不自签独立关闭或实际OS绿。

catalog唯一显式reader先从held handle metadata取得size，核单体和同context remaining配额，reserve全size再用`take(size)`有界内容读取；拒绝预约不读body，读取/签名/后核错误不退款。原collect继续处理其他目标时仍用同账，不能重置失败耗用；context catalog recheck也使用同账。只读句柄/精确首catalog/GUID/identity仍保；WinTrust内部provider访问不被这些字节账伪装成全OS I/O sandbox。保守预留可能导致合法后续复核缺额，必须真实测与报告，不能放宽128MiB求绿。

成功CreateProcess后立即armed私有PostCreateGuard。AssignJob/GetProcessTimes/trusted hook/Resume失败或正常Rust unwind都经同exact process/job持柄Drop，终止请求成功与否都不作结束；只有原process实际wait terminal且同Job查询ActiveProcesses0才释放。超时/查询失败一直保这些handles和调用方尚未返回的PreparedLaunch/source guard，不PID替杀/重启。创建失败无child可Err，成功Resume后才把职责转给OwnedProcess；公开ABI/窗口后台/Worker/MCP/ASR语义未变化。Rust abort/系统级故障或恶意同OSroot不在这段source的已证边界。
# I35 private test consumers (source candidate; not compiled or run)

The `tools/build/native-lifetime-library` entry contains the exact collector,
platform, indexed policy and ResourcePins modules. It excludes desktop main,
Tauri build.rs and facts EXE. Its lock retains the I31/I32 registry package
versions/checksums; only the local root package name changes. Extra windows-sys
features select existing API definitions, not new dependency versions.

`CatalogReadBudget::read_port` reserves metadata length before bounded reading;
File delegates to this same implementation. Metadata unknown does not read,
short/error/changed-length reads never refund. `verify_catalog_candidate` uses
that same account before the signature verifier. `collect_for_test` exists
only under cfg(test), enters the actual collect/observe/error-next-target path,
and stores its fixture SourcePort on the actual VerifiedSystemContext. Production
`collect` creates only WindowsSources (real held File/WinTrust/CryptCAT APIs).
Carrier creation, binding recheck and later recheck use the same context Mutex
and held File catalog membership. Fixture ports are crate-private, never JSON,
renderer configuration or an installation qualification.

The shared `owned_launch::launch` covers create, immediate PostCreateGuard,
assignment, real identity, before-resume binding, resume and transfer. Native
Win32Lifecycle supplies the actual HANDLE bundle and File stdin. Test-owned
NativeLifecyclePort supplies opaque bundles and a Write sink; it does not wrap
synthetic HANDLE values in File. Termination requests are never terminal proof.
Wait failure/timeout, query failure or ActiveProcesses>0 retain the exact bundle;
only terminal plus active0 permits failed-launch release. Production dispatch
never obtains permission from a PID, a Bool or renderer input.

`PreparedLaunch::launch_owned` consumes the actual PreparedLaunch and returns
the owned process with that same PreparedLaunch after resume. ApiRuntime uses
this method. On error/unwind the original ResourcePins/source context remain
on the calling stack through postCreate cleanup; they drop after actual terminal.
cfg(test) `fixture` accepts actual held ResourcePins plus an actually collected
carrier; `launch_for_test` runs that same consumer with the Test port. The
fixture-only constructor is refused by the production Win32 launch method.
Test can observe an Arc Weak of the actual ResourcePins during UNKNOWN, and
after failed return/success transfer, rather than a substituted DropMarker.

Full WinTrust/CryptCAT/native OS invocation is still a separate real-platform
qualification. Scripted ports prove consumer ordering only. I35 does not
execute Cargo, fixtures, native child, System32/catalog reads or EXEs. T31's
old I32 source prefix is historical; independent tests must pin the full new
source prefix and default production wiring before testing this revision.

## I53 default installed startup source

Native v2 installs now require an independently build-pinned NativeStartup.json with exactly format=native-installed-startup-v1-candidate, instance_id, installed_native_image, registration_record, resource_manifest, runtime_manifest, engine_file_names. All named objects and the actual running host image are original ResourcePins members. Digests come from those held members, not locator.server or a JSON readiness claim. engine_file_names is the complete nonempty engine partition; the remainder is nonempty. This is a new artifact input; old I26/I29 stages remain unchanged.

StartupBinding retains that same Arc and refuses a different PreparedLaunch guard/profile. It creates an immutable per-launch native-startup-binding-v1 data carrier containing the original full held file map, both partition identities, instance/role, independent image path/SHA and three registered resource identity hashes. A create_new carrier is bounded and held read-only/no-write/delete through launch and teardown; it is not executable configuration or a qualification issuer. Host creates authority pipe before the child, launches the exact indexed PreparedLaunch and registers actual physical child HANDLE/Job before Python factory/ready. The carrier hash protects data integrity, while actual private channel peer/parent/creation/SID/image and protected build authenticate the connection.

IndexedBootstrap consumes only the native source binding frame, installs its fixed finder, verifies the exact startup carrier/domain, then calls the sole Backend-owned video_creator.cli.native_startup.main(startup_record=bytes, locator_bytes=bytes). No module selector or fallback plain cli.main. This symbol must be in the new artifact index. If absent, reject before ready. API/MCP/registered Worker dispatch use the same consumer; ASR keeps its existing module/stdio and refuses this service carrier. API stop/close does not imply persistent Worker cancellation.

ApiRuntime holds StartupOwnedChild plus same PreparedLaunch/source carrier/ResourcePins, sharing the original process Arc with the authority session. Pending errors retain/terminate only the original owned Job until actual child terminal and Job active0, then drain original output readers. Final process exit, listener closure, original EOF and service-specific marker remain separate checks. No ready is derived from channel creation or a configuration hash.

Backend owns parsing/assembly of the child record, original Engine/Bundle/runtime callback, current Owner/registration and the independent protected image check. Its fixed adapter is requested in Integration/NativeStartupAdapter-I53/BackendAdapterRequest.md and not shadow-implemented here. Current facts wire remains not_ready with no Evidence; full resource/ABI/license qualification and actual Owner/instance bootstrap remain open. Authenticated management is a separate required adapter, not downgraded to installation Bearer. No product/API/MCP/Worker/ASR execution occurred in this source slice. POSIX default launch remains dependent on the earlier uncompleted I52 closed-spawn/guardian and Backend peer consumer; Windows compile cannot grant its actual OS behavior.

B38 canonical child input is UTF8, recursive sorted keys, compact separators, no BOM/LF and no NaN; entire record <=33,554,432 bytes. Full map and engine partition are sorted by exact relative_path. The original NativeLaunchContext files-array default-separator representation separately retains its <=33,538,048-byte limit; the native producer accounts for those existing spaces instead of testing only compact size. No rows are dropped. First candidate compile/source/raw stay historical; final v1 source is a separate version.

## Current production resource build input

`tools/build/BuildIndexedEngine.py` retains the original entry and adds the paired
`--production-input-plan <absolute JSON> --production-input-plan-sha256 <SHA256>`.
Without that pair the existing ASR candidate path remains. The pair calls only
the fixed own data module `tools/build/BuildProductionResources.py`; no Engine,
provider, model, installer or user-configurable callable is imported/executed.

The exact `current-production-resource-build-v1` object contains format,
source_indices, resource_groups, production_drivers, registration_template,
asr_manifest, outputs and target. Target is explicitly windows-amd64/cp313 for
this existing Windows indexed builder; Linux/macOS qualification remains a
separate actual build/installation target, never inferred from these bytes.

Each source index is pinned by absolute path/bytes/SHA256, kind backend/media/
engine and exact ordinary_root. Backend/engine source_map members use the
services/engine/src and migrations layout; Media sources use its original
video_creator-relative layout. Every selected ordinary copy is individually
checked. A conflicting overlay requires an explicit supersedes map from exact
target name to previous SHA. The entire physical Code/video_creator Python map
must equal the selected immutable map, including current_policy_evidence; a
twelve-file Media overlay or historical base alone cannot claim completeness.

Each resource group gives role (piper/ffmpeg/engine_runtime/asr/support), an
absolute physical root, installation-relative prefix, pinned full files index,
original license_files and all actual metadata_files. Index membership must
equal the whole physical root; an index physically inside its root is retained
separately without self-digest. Files, directories and ancestors reject links,
junctions and casefold collisions. Piper additionally gives python_prefix
inside its group, the actual piper-tts METADATA version and original model
licence; the selected worker must match the current Media worker bytes. Actual
Requires-Dist and native static tables are recorded, not interpreted as proof
of resolved dynamic dependencies, ABI floors, redistribution clearance or real
synthesis. All original base packages/resources are preserved; no dependency
trimming is permitted to make the new input pass.

Production driver sections retain only the stopped loader's piper/wan2.7/ffmpeg
grammar. The Wan workspace/region/model/resolution/exact storage hosts must be
explicitly selected; the builder does not invent credentials, a route or vendor
entitlement. A pinned original complete registered-media-config-v2 template
preserves its AutonomousRegistration and rights declaration. Only the complete
current package map, installed relative resource paths and actual generated
identity hashes are rebound. Backend still validates its sole domain model and
current routes/rights/Owner/registered identity at real startup.

The fresh installation root receives ProductionResources.json (<=2MiB),
ProductionRuntimeFileManifest.json (<=16MiB, 1..100000 exact file rows),
RegisteredMediaConfig.json (<=1MiB), and ProductionBuildProvenance.json. These
files enter the existing full LoadPolicy/file/installation map. Production
provenance uses existing source_identity data; no new deny-unknown policy field
or eighth runtime plan/fifth qualification profile is added. The independently
held final-host receipt producer must select identity_files.registration=
RegisteredMediaConfig.json, resource_manifest=ProductionResources.json,
runtime_manifest=ProductionRuntimeFileManifest.json. The existing independent
host/control/payload guard and StartupBinding.from_installation then carry
those three actual identities; no host digest is fed back into its payload.

Missing complete source, Piper/model/config/licence/runtime, FFmpeg/ffprobe or
original ASR resources is a hard build error, preserving partial own outputs.
SourceStageOne is a reproducible partial source input: the later blocker source
must be formally selected before a current release is sealed. No configuration,
manifest, build success or static table issues installation qualification.
# Diagnostic catalog production build source

`tools/build/BuildProductionResources.py` accepts the independent build plan
`current-production-resource-build-v2-diagnostic-v1`. Its original eight v1
keys remain required, with one additional build-only `catalog_bindings` object.
This is producer input metadata, not a public Backend DTO or an authority
carrier. The original `current-production-resource-build-v1` plan, original
driver v1 branch and generated v1 provenance fields remain separate.

The diagnostic plan requires the Backend's complete
`registered-production-driver-resources-v3-diagnostic-v1` catalog and a complete
`registered-media-config-v3` registration template, including the required
nullable `alignment_registration`. The sole Backend domain models own all
inherited alignment, recipe/profile/output combinations, method/check kinds,
full routes and MethodQualificationRef parsing. The builder does not duplicate
those DTOs. Explicit immutable source indices and exact `supersedes` identities
still select the complete Engine/Media source map. A twelve-file patch or an
ASR-only map is insufficient.

`catalog_bindings` has exactly these four members:

- `rule_template_paths`: every original method `rule_template_sha256` mapped to
  a nonempty, indexed installation-relative file; exact SHA and a 2MiB cap.
- `route_paths`: every recipe route, diagnostic method route and non-null
  alignment registration route ID mapped to a bounded full original
  CapabilityRoute JSON file. The original unique-key JSON reader rejects
  duplicate keys and nonfinite numbers. The sole route model must accept each
  full body, with the same ID and `verified=true`. Recipe route identity uses
  Backend `plan_payload_sha256` and preserves the cost rule version; methods
  must equal the entire original typed route. Verification flags do not grant
  runtime permissions.
- `alignment_configuration`: null if alignment is null; otherwise a nonempty
  indexed file matching the original configuration SHA (2MiB cap).
- `alignment_license_paths`: empty if alignment is null; otherwise every
  original license artifact ID mapped to a nonempty document listed in a
  complete resource group's original `license_files`. This binds documents,
  not their legal sufficiency or a model license grant.

All recipe producer and method implementation source references must match
actual complete selected source/resource members and SHA values (16MiB per
source). Non-null alignment also requires all original model file hashes and
the actual worker/runtime resource members. Its original registration uses a
real full local alignment route with no credential and zero cost. The complete
resource-group membership, metadata, license documents, collision/link gates,
and Piper/FFmpeg/Engine/ASR requirements are unchanged. The alignment runtime
file is byte-bound; its inner runtime/ABI behavior requires the actual driver
and qualification checks and is not inferred from a filename or SHA.

`ValidateDiagnosticCatalog.py` loads only these eleven selected domain files from
the immutable source map: contracts, errors, production_authorization,
registered_production, bundle, evidence, current_final_evidence, affected_repair,
plan_repair_targets, affected_recipe and component_diagnosis. It rejects a
preloaded Engine namespace and creates temporary empty package namespaces;
package initializers, CLI, Engine, services and providers are not imported.
Each domain body's original bytes are checked before and after its definition
load. A separately fixed Pydantic/tool dependency closure is required for a
future actual diagnostic build. No Pydantic/domain loading occurs for v1.

The existing indexed builder's fixed sibling resource-builder call performs
this preparation before overlay/LoadPolicy sealing. Before generating the same
four output filenames, every bound catalog member is checked again in the
physical stage. Diagnostic-only provenance records the exact domain byte map,
binding map and actual members. Runtime/resource manifest hashes are generated
after the complete physical inventory, not inserted into catalog method
registrations as a circular self-hash. `not_admitted` execution/distribution
status remains explicit. This source capability is not evidence of a built
package, current installed resource observer, route rights, qualification,
native ABI, GUI approval or production execution.
