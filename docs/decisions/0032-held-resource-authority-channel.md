# ADR0032：宿主 held 资源的 Python 私有观察通道

2026-10-09。状态：**Windows最小协议准入，通道/资源资格均未运行通过**。I48仅ResourcePins新源及覆盖库编译0；B29固定OwnerServices工厂有注入口。本轮不读B30活源、不实现/运行/凭证/收费。R1完整独验后连续R2、三OS与RES13原拒保持。

## 通道与真实身份

选**每个真实 child 一条双向本机 NamedPipe**，不复用MCP/ASR/stdin/HTTP/普通Bearer。Integration在可信launch前创建随机唯一pipe，`FILE_FLAG_FIRST_PIPE_INSTANCE`、`PIPE_REJECT_REMOTE_CLIENTS`、实际Owner SID/System的明确DACL；只接一个已经登记的child，未知连接拒绝并保原child槽位。child自行open，**不由父预open client handle后继承**（否则OS client PID可能是原父，不能冒子进程身份）。名称/JSON/session ID均不授信。

建立依据是同可信PreparedLaunch的OS真实launch记录：宿主保原process handle、PID+创建FILETIME、SID、OwnedProcess/Job、实际image及同Engine instance/角色/registration绑定；suspended→Job→resume保持。server用`GetNamedPipeClientProcessId`和OS进程handle核PID、creation、token SID、已登记launch及所属原Job，client用`GetNamedPipeServerProcessId`核host PID/creation/SID和实际宿主image。child还核实际父/launch关系与安装Owner保护的可信build image身份；仅path/对端JSON/hash自报不成立。待编译/实测的Win32调用兼容不冒通过；不声称抵抗同Owner/admin任意代码执行。

locator/期望launch描述只经可信PreparedLaunch私有启动配置到固定Python入口；无公共CLI/model/renderer字段可选pipe或host/image/instance。真正认证取OS及可信安装链，不能仅因环境有locator就构造client。bind阶段双方互验并核同instance、API/worker/mcp具体role、registration/resource/runtime身份；全部由可信factory提供，不从任务payload读。host绑定完成之前不授观察；startup失败保child/guard直到真实终态。

建立顺序固定为create pipe→owned launch/登记真实process handle→双向bind→Python工厂装配→原API/Worker ready。早到连接在有限startup deadline内等launch登记，不能在未绑定时返回观察，也不能等API ready后才服务pipe形成循环。instance绑定原真实数据目录/Owner保留控制身份及固定Python Engine，不接受任务自选；初次无Owner/资源时只可明确facts-only通道验证，不冒执行登记。

## 固定两方法与原观察

私有wire=`held-resource-authority-v1-candidate`：uint32 little-endian长度+UTF8严格JSON，单frame≤32MiB、单child一次一个call；启动/读写/观察均有已准具体launch plan的有限deadline，分段read/write，禁止无界缓存。完整预期映射若超过界限应在launch准备拒并交明确协议修订，不能截断/drop资源求绿。重复JSON key/未知字段/乱序/额外method/不完整frame拒绝；仅顺序递增`seq`，失败不自动重试或转其它host。session/observation ID是随机非授权locator。

| 固定请求（均绑定原session/seq） | 响应与责任 |
| --- | --- |
| `observe`，无paths/argv/缩小集合参数 | 宿主从可信安装清单取得该role完整Engine/source/indexed资源集合，调用**原**`pins.observe_files`，返回ID、实际observed_at_us、实际bytes/SHA有限映射及独立qualification结果/引用；不能由client选择子集 |
| `assert_current(observation_id)` | 只查本session原对象，重核OS peer/launch/instance/资格及`pins.assert_current`，返回同ID/current实际复核时间；unknown/别session/已释放ID不重新观察冒旧对象成功 |

Integration会话线程先clone原Arc<ResourcePins>，在该稳定局部borrow scope中保存`ID→HeldFileObservation<'_>`，用原issuer复核；先drop观察再dropArc，避免self-referential结构/unsafe延长生命。原对象不Serialize/Clone，wire复制事实不复制guard。同PreparedLaunch guard必须是真正同一Arc/issuer；不能重新open文件造同SHA对象。成功观察selected全集合仍不证明目录membership、DLL origin/ABI或license；qualification必须另由真实已准资源记录及当前检查提供，未知/被撤销为not_ready，模型Bool或配置SHA不能使其qualified。

## Python消费与当前检查

Backend唯一实现私有`OwnedAuthorityConnection`和薄`NativeInstallationAuthority`：连接只能由上述可信factory建立，无public DTO构造器；依旧实现`observe() -> InstalledProductionEvidence`、`assert_current(observation) -> None`，不改B29字段/公开DTO/SQL/SDK。

`observe`只有身份、完整事实和**真实当前资格**全部通过才构造原Evidence（同instance、三SHA、workflow/driver、完整两映射和实际微秒时间）。adapter私有identity-map保存`这个实际Python对象→session/ID/epoch`并强引用，比较`is`而非dataclass值相等；`replace`/反序列化/同值新对象不能assert。`assert_current`核原对象/连接epoch，再向原host请求复核，成功仍须保原connection/guard。facts-only响应可在独立通道验证中检查；生产adapter抛具体503，不能把它包装成InstalledProductionEvidence。

所有IPC/hash/OS与资格复核在writer外，沿B29 `ProductionAdmissions._installation/current_guard`调用；短writer只核现policy/fence/floor及本机已观察失效状态，不在事务内做RPC。Backend把连接断开/超时/host死亡通知为不可逆session invalidation，并在该transport guard的writer前/现guard检查核本机状态；不得缓存“上次True”继续签发。它不承诺回撤在故障被观察前已提交的动作；窗口关闭/EOF不取消制作、不清unknown/费用或盲重交，原核实/恢复账本继续。

## 生命周期、分派与独立验证

pipe disconnect、peer/creation/SID变化、timeout、host/child异常、session线程退出均使所有ID和PythonEvidence失效；禁止自动reconnect复活旧ID。**会话无效不等guard可释放**：正常host仍持PreparedLaunch/Arc/进程与Job，直到child及owned后代真实终态；shutdown marker/发stop成功/PID不见不代此证据。后台Worker须独立仍存活的真实supervisor/专属pipe及guard；API/窗口关闭不能释放它。现ApiRuntime仅API的所有权不能冒后台Worker已接。host异常沿实际Job终止/保留终态证据；parentdeath资源释放顺序与非Windows等价保护仍需实测，不宣完整OS sandbox。

**Integration先**实现pipe server、真实双方peer/launch绑定、原borrowed观察registry与lifecycle；**Backend随后**实现薄client/factory消费，按原`assemble_owner_services(engine, owner_subject, *, bundle, for_management=False, installation_authority=..., execution_registration=...)`同Engine/Bundle/Owner/Control注入，Worker不加载管理secret。Media仅消费既有真实资源身份/authority，不接管pipe或改ASR stdin/监督；RES13不触碰。不存在合格资源不妨碍先实现并真实验证channel/held facts，Owner管理仍可单独完成。

错误用原ErrorEnvelope，Backend唯一定义精确code：peer/launch denied403，坏frame422，foreign/stale observation409，断线/timeout/未配置/资格未就绪503；不得null/Bool/expected-red冒正向。Test独立核真实child双向OS身份+actual held读/复核、外国同SID进程/错PIDcreation/错instance/role/Job、pipe抢占/remote/ACL、复制对象/ID跨session/乱序/超大/半帧/EOF/超时、原guard不提前drop、观察线程结束旧ID拒绝、host/child死亡和后代终态；无资格时原Evidence必拒，有真实资格后完整observe/assert/factory/current/final链另验。非Windows端口目前明确unsupported，必须后续Linux/macOS真实等价guardian实现，不能降三OS。架构批准不代通道、Owner、资源、许可或产品验收通过。
