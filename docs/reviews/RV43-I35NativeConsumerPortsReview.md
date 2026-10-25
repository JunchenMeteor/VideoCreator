# RV43 — I35 原生消费者私有测试接缝有限源码评审

结论：**SOURCE_REVIEW_FINAL；本固定切片未发现新增静态阻断。** 生产 File/Win32 默认与私有故障端口进入同一预算、collect/carrier/bind/recheck 和完整 postCreate consumer。实际 PreparedLaunch 在失败/正常 hook unwind 清理与成功返回中保留原资源所有权。没有编译或运行新库、执行消费者故障或 Windows 原生调用；不关闭完整 P01/P02 运行验证，不授安装、Source/guard、ABI、三 OS、Gate 或作品资格。

## 1 固定输入和身份

唯一 I35 根：G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeTestInterfaces-I35/。只读 SourceCopies、完整 Before/diffs、正式交接/PrivateConsumerPorts/LibraryBuildPlan、23 包普通归档/索引及锁比较所必需的 I32 历史固定 lock/cache。没有读取 I36 WIP、T32 输入/结果、当前生产或系统 DLL/catalog/store；没有 Cargo/Rust/EXE/native/Test 执行。

| 正式对象 | SHA-256 |
|---|---|
| I35Handoff.md | 7397e3586ce5df2073423be9bf08c29942ca8a4dd61e28bbecd27bc161856fcb |
| I35Handoff.json | 41b1711c81bde7b012065a97741c5d5a560295047edc09122069338e87147a3f |
| I35SourceFreeze.json | 17c83491aadeeee4c7467d75c542f9c02e446b9cac836a4b99f85dfbaa3d8548 |
| PrivateConsumerPorts.md | ce3c5a2dd121c2946fa21debe1b65a290f9c60c627eb25b77343b3d1086eaa91 |
| LibraryBuildPlan.json | c1f0d647b7f5c0d97df129b7fff07cc2c54895d23c0de7cd631468ea93889040 |
| SourcePreparationReceipt.json | 457a26610be74f8048ff747672d702d8835fbf282299ceed16e287f101594c51 |
| RegistryPackagePins.json | fbf80ca701326a04b0b7496e6fccfa8eaee7b40b51febfd681c3acee1d8d6b57 |
| CargoHomeConfig.toml | 04528d4e60e5e4816bd3cd083f891760546e1e5a12c670e9d7762a809a5ba9c5 |
| 原 I32 Cargo.lock | 4ed28469188fd84f03b734a5e4b13ebd1c05b66d92684e3f200c635b50667183 |

9 份普通支持源码包括 8 变化/新文件、1 只读 resource_pins。6 对既有 Before/After/diff 均逐文本吻合（resource_pins 的 diff 为空），3 新文件独立固定。23 archive_source/copy 与 index_source/copy 共92路径 hash/size 匹配；未解包执行或 Cargo resolve。合计127输入路径。

初读127中唯一不匹配是统筹将 RV43 卡从“待实际恢复”改为“已实际恢复，准备或源码评审进行中”；原卡 SHA d509bac8eaed86a3af3d39db5803723bf1732e680e904e4f4db6011f14c9b71b，新卡4688925806f13679018f619697de225c9effe765d9ed605abdf451deee1b54e0。已读新全文，标准库比对确认只调度状态行变化，权限/固定输入未变；原 initial pins 保留。其余126固定来源/材料无 mismatch；按已观察卡版本保存新 pins 后127末核0变化。这不是产品源漂移。AGENTS SHA6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d。

| 普通源，相对 SourceCopies/ | SHA-256 |
|---|---|
| apps/desktop/src-tauri/src/windows_native_sources.rs | cead31cb154eadd82dff97ca600909df355d6b2b4c16ef868bd2e05343447f21 |
| apps/desktop/src-tauri/src/platform.rs | 2085c24a44d7ae1135c728d0eaccf094f6640a57332502ba6438162c21f9f7fa |
| apps/desktop/src-tauri/src/load_policy.rs | 50a48bf42e01771762bf750b1fb2aed216f052e4877c0fb9aba82edc1f89e4c8 |
| apps/desktop/src-tauri/src/engine.rs | 2e4692a777f279dbaf718185b7ce0c37c8553c1cba0029ea480e487b7ddec0ce |
| apps/desktop/src-tauri/src/resource_pins.rs | 930278a6df5444d483c60c2733992b24a056956650ffb4bd22e55e2f2a99b351 |
| packaging/IndexedRuntimeContract.md | 509d5ee4d9d97dbf90564521de33de1c7b87bb317116c659ac7ba492b8ba690e |
| tools/build/native-lifetime-library/Cargo.toml | 86c2297b89028a27783ec828c3f298b314ae863eaa7cf023e160329929c2678c |
| tools/build/native-lifetime-library/src/lib.rs | 8437cdcd1ea254b8db5888a579c94aed22db11b6bf58956ab405618444838395 |
| tools/build/native-lifetime-library/Cargo.lock | 4bb0070c55d57ffaaedb41eaa5442138d51aec8d6e75e8dc44d9013ad9616334 |

## 2 预算、File 与完整 context 接缝

固定 [windows_native_sources.rs](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeTestInterfaces-I35/SourceCopies/apps/desktop/src-tauri/src/windows_native_sources.rs:32)。

CatalogReadPort32–37 为 Read+length，File 使用实际 metadata；read_catalog48委派同 read_port49–56。先读 metadata、在单 context CAP128MiB/remaining 内 reserve 全 length，之后 take(size) 有界读取，短读/I/O/after-length unknown 或变化拒绝。保留 reserved，失败没有 refund 或 new account；metadata失败在 reserve/body 前返回。verify_catalog_candidate61–66 用该 budget 先读取再调用 verifier，给实际 body 的 SHA/size并返回原 held File，不另做 budget 或 fake HANDLE。

生产 WindowsSources107–114 接实际 held File、file identity、WinTrust/catalog、loaded origin/version。SourcePort97–105 为 crate-private 并在非 test 配置 sealed；只有 collect_for_test320–322 在 cfg(test) 允许外部 fixture port，进入与生产 collect317–319 相同的 collect_from324。没有 Deserialize context/renderer DTO 构造途径，私有 port 返回实际 File，不能从序列化 Bool 得生产资格。

collect_from327 只创建一个 catalog_budget Mutex 和 source Arc；四真实 metadata carrier331–334先观察，per-target340–355错误记入 observations.errors 后继续后续目标，不在错误后 reset account。observe369–372在该 Mutex 内调用 source.signature；错误后 reservation 保持。carrier396–410先同 context.recheck，再 create_new/sync_all/held 原 carrier。bind76–88同 context.recheck 后只写原有界 NATIVE_SOURCE_BIND 一次；recheck413–419用同 source/host/root/file身份及同 catalog Mutex核原目录/File/catalog members，不 copy/reset budget。克隆 Arc 并发重核仍共享 Mutex；这只是源码上的共用关系，尚未实际测并发/故障。

生产 windows::signature241–273保持原 embedded WinTrust 和 **单个首 CryptCAT candidate**；同原 GUID/root/path约束后实际 held catalog通过 verify_catalog_candidate。没有用释放的 catalog cursor 继续枚举，后候选 unresolved 保持；该端口不模拟 native candidate selection/WinTrust内部 I/O。online_revocation 仍 not_checked_cache_only，观察不等一般 MinOS/再分发授权。目标 errors、VC numeric floor unknown 等缺口必须由实际消费者/Bootstrap接收并拒绝或明确未准入，不能把 fixture 填出的签名状态当生产来源通过。

## 3 同一 complete postCreate 与精确 owned bundle

固定 [platform.rs](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeTestInterfaces-I35/SourceCopies/apps/desktop/src-tauri/src/platform.rs:3)。

owned_launch3–47是生产与故障端口共用完整 consumer；NativeLifecyclePort9–24为 crate-private、非 test sealed。测试可以用 opaque Created/Write sink，避免把任意数字 HANDLE 包装成 File；生产 Win32Lifecycle 的 Created79–82持原 Job/process/thread/真实stdin及stdout/stderr管道。

生产 create86–112 的所有 argv/env/Job/pipe/attribute-list 可能失败步骤均在成功 CreateProcess 之前；成功106–112之后只做 ownership moves和 attribute-list释放，没有 fallible调用，再返回 original Created。共享 launch38–39在 create返回后立即建立 PostCreateGuard；assign41、identity42、before_resume/stdin43、resume44任何 Err及正常 hook Rust unwind均经过该 guard。45–46仅在 resume成功后取出同 Created并通过规定为 infallible 的 transfer移动到 Owned。生产 transfer134–138确为原句柄移动；这不是“测试自行造一个影子 guard”。

guard Drop27–35只对该 exact Created调用 terminate，然后**分别**计算 terminal 和 active；只有 Ok(true)+Ok(0)释放。请求 bool、timeout、query Err、active>0均不能作终态，保持相同 bundle 和 caller尚未返回的 PreparedLaunch；不 lookup/kill新 PID、不重开。生产 terminal127–132用原 process WaitForSingleObject及原 Job Accounting ActiveProcesses；Job未分配而assign失败时也持原 process，经相同清理。正常 Rust hook unwind在此边界受保护；清理端口自身 panic、Rust abort、恶意同OS root及真实Win32异常不因静态源码得到额外保障。

trait 的 transfer必须保持真正 infallible ownership move；未来 Test 不应在违反此契约的伪 transfer中 panic，再将该伪行为包装为原生产生命周期结果。实际 Win32/Job/等待故障及 original identity注入尚未运行，不能称真实cleanOS/guard qualification。

## 4 实际 PreparedLaunch 与成功/失败资源寿命

固定 [load_policy.rs](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeTestInterfaces-I35/SourceCopies/apps/desktop/src-tauri/src/load_policy.rs:35) 的 PreparedLaunch35–61持真实 Arc<ResourcePins>及原 LaunchSourceCarrier。launch_using48–53借其 executable/env/root，并在 before_resume使用其实际 carrier；self直到内层 shared cleanup完成才返回 Err或 unwind，成功返回 StartedPreparedLaunch{process,prepared:self}。不能用 DropMarker代实际 ResourcePins/held File/context观察。

cfg(test) fixture56–58必须从实际 guard.resolve取得已持柄 pinned executable，使用实际 collected carrier，并标私有 fixture_only。launch_owned44–46明确拒 fixture；launch_for_test61仍走同 launch_using。这个标记只隔离测试机制，不发行 installation/source/guard资格；发布默认不提供 test构造或 SourcePort/Lifecycle任意输入。

固定 [engine.rs](G:/开发测试/Codex/VideoCreatorImplementation/Integration/NativeTestInterfaces-I35/SourceCopies/apps/desktop/src-tauri/src/engine.rs:99) 的 ApiRuntime99–103从真实 prepared.take 调 launch_owned，保存返回的同 prepared；PendingApi58–64及成功128保存所有权。API ready/HTTP/owned listener错误由 PendingApi持原 process until terminal并 join输出；ApiRuntime Drop74–75同样先保原资源到 owned终态。正常 stop Receipt不能用 marker/port单项冒normal，145仍要求 actual0+marker+closed+tree empty且非forced。这些接线已源码更新，整桌面/main/Tauri尚未重编或运行；Worker/MCP/ASR完整独立 owner路径仍待，不能按 API这一接缝自签四 profile。

resource_pins69行完整普通源与 Before相同，实际 file/ancestor directory handles、path/hash/size核和 Arc寿命未替换。成功以后关闭职责是正式 ApiRuntime或未来各角色owner，fixture scripted terminal/active0不是真实 OS终态。

## 5 library-only、锁与待测条件

Cargo.toml7–17 root build=false、auto bin/test/example/bench=false、独立workspace/lib path、doctest=false；lib.rs3–10仅四完整实际模块 ResourcePins/platform/load_policy/windows_native_sources，无 main/build.rs/Tauri/factsEXE/新Test。engine.rs的新 API接线**不在这个 library编译范围**，不能以未来 library绿替代整桌面入口。依赖原 build/proc-macro/compiler的隐式运行也不等显式 collector系统事实授权。

标准库 TOML比对旧 I32 与新锁的23 registry package全部完整记录一致，全部锁字节仅 local root name替换，依赖 version/checksum/完整记录未变；cfg windows features只选择原版本API，实际解析/编译兼容待证。闭环 archive/index23对 source/copy身份匹配不等实际 Cargo cache可用。

LibraryBuildPlan为 PREPARED_NOT_AUTHORIZED_NO_CARGO_EXECUTED；HistoricalExpectedToolPins是 I32历史完整工具/SDK预期，不是当前工具重新核资格。本轮只hash该普通元数据文件，没有读取/运行完整 compiler/SDK系统树。下个launcher需自己的准确 pins/闭环境/source/test prefix/命令/时限与 retained Process+EOF真实终态，新故障测试的 fixture/criterion/runner归 Test，另固定并准入；本报告不执行或批准实际编译/测试。

必要独立验证仍包括真实预算 consumer metadata未知/超额不读/short/I/O/after变/签名或identity失败不退款、complete collect错误后next-target、carrier/bind/recheck同账号和并发；真实 PreparedLaunch+Weak<ResourcePins>在 assign/identity/bind-write/recheck/resume Err或正常 hook unwind、wait/query unknown/active>0中保持，并在同call terminal+active0后释放、success保同 Prepared。必须真实触达完整新源码，不能取T31旧prefix、fake File HANDLE、只测独立 guard或第二 budget；脚本端口机制绿仍不授真实 FFI/catalog/安装资格。

## 6 原证据和终态

原 owner f4cbeb actual0只支持 source finalizer、普通copy/metadata/cache固定；SourcePreparationReceipt自身明确其字段不替原exec terminal。I32/T31旧prefix/编译/失败产物保持，未继承为I35绿。新库没有编译或运行；VC八numeric floors、147+24资源兼容、四 profile、三OS和作品仍待，完整 R1独立验收后连续R2不缩。

本角色原文件名定位 session24297已3abf23自然exit0，不重开；后只精确根读取。文本差异/TOML分析 f3b459 actual0，127末核0变化（治理状态变更单列）；固定reader全部终态释放、live=[]、production freeze false。仅 docs/reviews 与 Review/NativeConsumerPorts-RV43 写入，无产品/Test/DB/native/系统扫描/network/key/fee。Facts SHA76c6e354fbc760b9c9941dc3b734788de09c6514e49c4c131a92d6d1bd8c7deb；SourceAfter SHAd3493cf4db4ef1f7a953186984c5df8aec125f2f457d49c4ac96676aa5f816ec。正式 Snapshot/Handoff 固定准确结论与所有输入身份。
