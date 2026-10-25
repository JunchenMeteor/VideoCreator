# ADR0033：POSIX本机资源authority的最小实施边界

2026-10-09，A30。**准入私有POSIX接口与分阶段实现；不批准生产资源资格。** ADR0032/Windows I49协议、原对象身份和qualification分离保持。本卡不读B31热源、不实现/运行产品。完整三OS R1独验后连续R2；RES13原拒未改变。

## 已核来源与当前缺口

I49固定普通9源配置+合同10项SHA全部匹配。Windows真实facts-only父/子probe自然0是owner证据；Python工厂、合格安装和POSIX未通过。`platform.rs`只有Win32 OwnedProcess；`resource_authority.rs`直接依赖Windows；`resource_pins.rs`明确因普通POSIX open不能阻止写入而拒observe。**这是需补的源缺口，不是仅缺机器。** 原source/出处/研究SHA见自身`InputPins.json`。

Linux [unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html)明确SO_PEERCRED取connect/listen/socketpair时的kernel credentials；父先创建socketpair再继承不能据该静态PID冒child。 [pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html)从Linux5.3提供稳定进程FD、实际退出poll；[proc_pid_stat(5)](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)第22字段为启动后的clock ticks，不能取四舍五入毫秒。 [cgroup-v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)规定fork继承所属cgroup、populated涵盖子树、cgroup.kill处理并发fork；迁移权限必须实际受控。

Apple官方[XNU un.h](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/un.h)提供LOCAL_PEERCRED/PEERPID/PEERTOKEN， [proc_info.h](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h)有启动秒/微秒字段；本轮未取得对应SDK libproc查询flavor/availability证据，不猜常量或数字最低macOS。 [kqueue手册](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/kqueue.2.html)有EXIT/FORK/EXEC并会聚合事件，**不证明自动、无缺漏地枚举全部后代**。 [EndpointSecurity](https://developer.apple.com/documentation/endpointsecurity)提供系统事件，但需专门entitlement/system extension，不把它偷偷加成普通安装前置。

[flock(2)](https://man7.org/linux/man-pages/man2/flock.2.html)为advisory；打开FD、chmod自己拥有的文件、路径SHA、只读bind原可写inode均不单独证明不可改。Apple[访问控制指南](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/AccessControl.html)要求最小权限、注意TOCTOU；管理员模式与普通安装必须分开。Context7实际第二docs0取得Rust官方[UnixStream有限超时](https://github.com/rust-lang/rust/blob/main/library/std/src/os/unix/net/stream.rs)、[Unix open/CLOEXEC](https://github.com/rust-lang/rust/blob/main/library/std/src/sys/fs/unix.rs)，不能据此推OS peer或资源资格。首docs1是无相干文档，不是启动/认证/网络超时。

## 通道、身份与最小私有接口

两平台均选**child自行connect的pathname AF_UNIX SOCK_STREAM**；每child独立会话，宿主以实际Owner控制目录0700、socket0600、no-follow/祖先身份检查与create-new建端点，禁止abstract/远程回退。目录/socket权限只是接入边界。locator仅可信PreparedLaunch→固定bootstrap私有环境，不能由任务/renderer/MCP参数生成。

| 平台 | 双向身份和lifetime端口必须实现 |
| --- | --- |
| Linux | SO_PEERCRED实际PID/UID/GID；原launch立即保pidfd并保持实际waitable child，保boot范围+start_ticks和实际父/role/instance；核pidfd状态及真实/protected安装image。client同样保host pidfd，前后核创建身份和真实host安装链；读取/proc路径前须实际可信procfs，不能信JSON PID/SHA |
| macOS | SDK公开LOCAL_PEERPID/PEERCRED取实际peer；可用时保kernel audit token的pidversion，不以自报token补缺。原spawn保未reap child及创建秒/微秒；在固定bootstrap放行Engine代码前登记kqueue事件，client也预登记host。查询前后核同creation/UID/真实image与受保护build，退出/EXEC变化/registration错误不可成功。libproc实际符号、audit availability和pre-start机制由Integration固定SDK核+编译，不声称当前证据已够运行 |

不改Windows locator。POSIX另设**私有transport版本**`unix-domain-v1-candidate`与tagged ProcessBirth（Linux原ticks/boot范围；Darwin原秒、微秒及可用pidversion）；不把FILETIME、birth或audit当媒体微秒。wire仍`held-resource-authority-v1-candidate`：原bind/observe/assert_current、seq、32MiB、20s启动/10s IO和完整role全集映射保持；平台描述不进公开DTO。有限超时覆盖每帧累计读写，不能每字节续命；EOF/乱序/对端变化不可重连复活ID。

内部端口最少三项：`authenticate_actual_peer(owned_launch)`返回宿主私有保留身份对象；`observe_original(full_role_map)`返回借自原ResourcePins的真实对象；`confirm_owned_scope_terminal()`只返回Confirmed/StillLive/Unknown。Integration定义私有Rust类型，Backend按最终固定合同写薄Python消费；禁止public构造器/模型Bool/重复issuer。原`InstalledProductionEvidence`、is identity-map、writer外RPC+最终本机失效检查、不合格503保持。

## 资源保护与安装体验的明确分界

**不批准全体POSIX安装强制root/admin。** 本地免注册/BYOK、环境打包、exe/dmg/无头Linux和安装实例持有数据不变。先实现POSIX原FD/目录dev+inode/完整hash事实与原borrowed对象assert，未具强保护时仅probe facts-only/not_ready；不能删unsupported后使生产adapter构造Evidence。

可选受保护资源包实施路径：经明确安装授权，把版本化runtime/build放在受管理员控制、普通执行UID及其组/ACL无法改写/替换任一祖先或leaf的树；数据目录独立仍归用户。保原目录/文件FD与对象身份；installer/updater禁止原地更新，通过持有版本lease只新增版本；UNKNOWN不回收。**它新增该安装模式的权限前置，不能默转普通用户/便携安装。** root/admin任意代码不在本机通道防护承诺内，但正常updater仍须遵守lease。

无管理员的快照执行仍是**待选型验证的具体实现工作**：Linux需不可再写的匿名sealed资源或真正隔离的只读副本，不能readonly bind仍可写的原inode；macOS需匿名快照/只读FD与实际loader消费路径，普通unlink/RO FD本身不能被宣称完整不可再写。完整Python模块/metadata、native147+24依赖、模型、FFmpeg/Piper/ASR工具及动态加载都须来自同原快照；不能只保几个文件或替成模板/禁用能力。FD路径/dlopen/exec/transitive rpath、原source→副本清单身份、变更攻击与关闭后回收由Integration实证，再交架构/独立测试准入。**当前未有已证无admin完整方案；若候选失败，须给实测成本/缺口供产品选择更换快照机制或显式可选安装模式，不能把长期not_ready当R1交付。** 本ADR不冻结未查证的memfd/挂载/代码签名兼容。

## 后代终态与实施顺序

Linux：每实际child用独立受控cgroup-v2子树，启动门放行前加入并固定该scope，child无迁移授权；父pidfd退出+scope populated0+原wait/输出EOF才可确认。cgroup目录/权限不足为具体未配，不降为pgroup；kill只是动作，仍查真实终态。最少pidfd机制floor5.3不是产品最低Linux，cgroup.kill及发行版/内核配置须独立feature+真实矩阵冻结。

macOS：**当前公共资料不足以批准通用任意fork树闭合。** 最小候选为native guardian直接持有所有批准helper，各进程放行前装上原kqueue/creation检查；Python/FFmpeg/Piper/ASR等合法spawn须逐项迁移或证明已在同guardian登记。任何未登记fork、事件观测失败或逃逸使scope Unknown并停止新admission，不能仅因pgroup空/父exit释放。fork限制不等功能可删：Media先给固定源码中的真实spawn清单与等价调用要求，Integration/Backend接通批准launch，保所有制作能力。候选只有真实无遗漏反例验证及可信closed-spawn实现后可准生产；需要任意fork兼容时另评实际完整监测机制/权限，不能把未知后代当退出。

API/window关闭与后台Worker独立：每后台Worker有仍活native guardian/原guard专属通道；停止/取消制作分开。断连/线程结束立即废全部ID，但guard直到真实scope终态；宿主异常无法证明终态时保不可原地改的版本、不清unknown账本；不能声称POSIX有Windows Job kill-on-close。未知后代或宿主死亡下的实际资源保持/版本回收仍是必须通过的故障项。

1. **Integration**先拆现Windows专属module为平台条件实现，按上述UDS/身份/原pins端口补Linux/macOS源；无头guardian复用同核心，不依赖Webview。先交事实probe固定源/SDK符号/精确ABI，不等所有资源许可；随后提供两安装模式的实测候选和合法helper launch闭包。依赖/锁唯一由Integration维护，不换框架。
2. **Backend**消费最终平台私有合同，保持B31 Windows可并行；只按受信factory选平台并绑定同Engine/Control/role。POSIX事实不得变InstalledEvidence；错误沿原Envelope 403/409/422/503。若合法媒体launch需新私有消费端口，先交有限合同给Media，不把argv开放给模型。
3. **Media**只迁移自身固定驱动的实际批准spawn/资源消费，保功能及原Operation/fence；不改权限、私有通道、ASR监督或RES13拒绝。**Test**独立在真实Linux/macOS查同UID冒用、错birth/instance/role、host/child退出/exec、半帧/慢帧/跨ID、原对象/guard、合法helper成功、fork/setsid/双fork/父异常仍活后代、写入/替换/ACL/动态加载全部profile；三个平台不得skip冒通过。资格、许可、MinOS、真实作品/质量仍各自未验。
