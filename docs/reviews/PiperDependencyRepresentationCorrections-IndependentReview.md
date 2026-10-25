# Piper 表示测试准备修正独立评审

结论：原 **PDRT-P01（P2）在本固定 PowerShell/Python 两入口中 CLOSED_SOURCE_STATIC_ONLY**。原 **PDRT-I01（P3）仍 OPEN_SOURCE_STATIC_PARTIAL**：新准备材料的 UTF-8/LF 已支持，未来 Python JSON writer 仍有一处未修。当前 87 项全部 NOT_EXECUTED；Review 未运行候选、parser、案例或产品，未批准 runtime。

## 固定范围与输入

任务卡 SHA `27a55642fcd331222a1fd49deb9eb3195add1a194cf07ca68390bf81f1558971`。停止根为 `G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperDependencyRepresentationPreparationCorrections/`，只使用 `SourceStage/Ordinary/` 中 82 件原副本，以及已 pin 的 9 件治理/正式交接。自己的 InputBefore/InputAfter 共 **91 项，逐路径/大小/SHA 无差异**；未扫描或复制 whole runtime。

| 固定输入 | SHA-256 |
| --- | --- |
| CorrectionHandoff.md | 91eb394c970acb49fb5d2e231dacbc47220048ed2096d5435e756e832fbff65d |
| CorrectionHandoff.json | fccd0bf6c6a06f06b35a6ae59249647a2deb810532e4f58cce66300232617720 |
| ActualInterfaces.json | 7d951d876c6d8130a159339e73ea1ee1400c1acbcceb7e5d86e33bb401d22391 |
| CorrectionSourceSnapshot.json | 3b7baa1b9904319868cb5429a1dc2b6aafbbfb625eb91297d4b6289592fc9e48 |
| SourceStage/CorrectionOrdinaryIndex.json | 22f8defd785deafc0fc634b13e243fa796e76329012b74835365897111891d7b |
| CorrectionFinalizerToolTerminal.json | bed24ebc4c9b054eabc200af6726bd381249d15e0b3c3512040a7ce983990a18 |
| RunRepresentation.ps1（9226 B） | cf9b189554c51b697ac9a07d51f21732f67830217b2010acf6cb82589537abfa |
| ProbeRepresentation.py（17960 B） | 604a94e5527ac83fc223bfc45f6ee94174e9a83c8774d88f754bf90537065e26 |
| RepresentationInputIndex.json（607722 B） | e6b82ba3809142ded10c50a04f102fcd821ae196d7bb9c5a756b5554da53cd67 |
| FutureLaunchRequest.json（1667 B） | 6c748c81cf431491701fc5896feaca34f55bdfcc026e7169d79c2cab262ada25 |
| FullSourceDiff.txt（123457 B） | 852012f9913b134fbbf583f209006763d009b0b9ababb61fc15744bc31a85eb5 |

源/交接/终态的身份与内容分别核对；作者 parse/metadata 0 只属于准备，不作为运行支持。正式交接中写入时的 tool-return-pending 字段与其后 Test 实际 2e4cc3/0、TRUE FINAL、读者释放分别保留。

## PDRT-P01：两入口的真实索引核对链

PowerShell `RunRepresentation.ps1:48–59` 读取物理原路径的完整 byte buffer，并从同一 buffer 算 SHA；`:65–68` 与外部固定 SHA 比较、一次锁存原 path/size，再解析这份已核 buffer。`:152–162` 末核把 index 和 1041 records 分开：先从锁存原路径重新读取、核原 path/size/外部 SHA，再独立 Assert-Pins；任一缺失、读取异常、漂移均保留 false。`:163–171` 不把未证明的 input_after_verified 写成 true，errors/forced/缺 EOF/末核失败均使整体非零。

Python `ProbeRepresentation.py:44–58` 同样核 byte buffer/物理完整路径/原 path+size/外部 SHA；`:243–248` 仅解析首次已核 bytes。`:319–332` 用原锁存 identity 独立重读原 index，再独立 verify(records)，各自默认 false，失败先抛 RuntimeError，不经过全绿 Summary 分支。没有 index 自身递归 hash 记录，没有末读后刷新预期，没有用 records 等价替代 index bytes。

审计只在 `reader_guard:81–85` 为这一个锁存原 index 路径增加读取许可；原 absent-cache 条件、固定 FileLoader.get_data code identity、source size/SHA 和 owned-output 写入限制保持，未宽放普通路径、网络、子进程、ctypes、SQL 或禁止模块。

独立完整 before/after JSON 关系核：1041→1041，原 999 runtime records 字段逐值相等，无增加/删除。除任务根搬移外只有六件自有记录的 size/SHA 随源码更新。364→364 cache mappings 中唯一变化是 Probe source_size `15545→17960` 及对应新 SHA；cache path 的根搬移与原 tag、optimization、absent、readonly、caller/code 条件保持。这个声明来自逐项比较，不是作者 MemberContinuity bool。原 runtime 999 只比较已冻结 records，未重扫环境。

因此 P01 源码缺口具备有限关闭依据；真正 index-only 篡改、丢失、读取故障与正常执行路径仍待独立实际 Test，不把静态分支称作已实跑 fault。

## 原算法、标准、Windows 启动与生命周期保护

六段完整 diff 的全部 before/after 行均独立重建并与普通源全文相符。原 `RequirementRepresentation.py` 14205 B / SHA `9eae0ad968c464189810a62e0ecf2579a2dc5ef11de1fc6dd3b523e3018ac382` 及 16 件固定输入完整字节未变；Cases/Oracle 字节未变，87=54固定+20变量+11边界+2原始/改变案例。whole parser 的 importlib loader/exec_module 与 origin/hash 校验保持，没有抽取 AST 被测函数或 Mock。AST 仅用于 Review 对比，非测试执行。

解码 FutureLaunchRequest 的完整 Windows cwd、argv 中 runner/index 路径及外部 index SHA 与普通件一致；runtime_approved=false。原 argv/env/物理路径/独占输出、364 cache 必须不存在等启动门源码保持。PowerShell `:107–149` 持原 Process/creation/handle，原 90s 上界、强制失败、并发 stdout/stderr byte pumps、原对象终止和两 EOF 检查保留；末保存异常未被吞成成功。Python 原首错停止/剩余 NOT_EXECUTED/实际 87 计数保持。以上都是源码支持，未创建候选 Process，未观察 OS handle/EOF 或保存故障。

## PDRT-I01 与本轮 PDRTC-I01（P3）

独立核新 27 件自有普通文本均 UTF-8、LF、无 BOM。PowerShell `Write-Json:17–20` 对结构 CRLF 转 LF，准备脚本的 Json-Write 同样处理；JSON 字符串 escaped 数据仍按 JSON 值保留。原 Cases 原 bytes 相同，Provenance 仅任务根搬移，16 固定材料及历史 raw 没有换行回填。

但 `ProbeRepresentation.py:262–263` 的共享 save 仍使用 Path.write_text(..., encoding='utf-8')，**缺 newline='\n'**。Windows 默认文本换行会把未来实际 JSON 结构 LF 转为 CRLF；ActualStartupBinding、case 完整/partial、CacheReadEvents、InputAfter、Summary 等均经该函数。这是继承的未修 future writer；目前没有执行生成输出，不声称已观察 CRLF。新准备 JSON 的 LF 不足以关闭此项。

归属原 Test；在新 immutable 源版本中仅显式指定受控 writer 的 LF，保 JSON 值/allow_nan=False/escaped raw、87 oracle、audit、时窗、原失败，不由 Review 改源或授运行。Finding 路径 `G:/开发测试/Codex/VideoCreatorImplementation/Review/PiperDependencyRepresentationCorrectionsIndependentReview/Finding-PDRTC-I01.md`；SHA `919b5bdf2a2ea6480ae3c176ee61a4fb791398759c314e2e676987ff1f506326`。

## 原错误、限次与未测边界

原 9c07c5 anchor 准备失败及旧 19/20 元、literal 12 差异红永久保留。本轮 Review 误按简称查 ActualInterfaces.md，b2282b/1；3e563c/0 按正式引用补读 ActualInterfaces.json，属定位错误。自有 cache 观察器首次误用 source_path 字段，4d387c/0 保存原派生结果 CacheMapFactsFirstObserver；真实字段为 source，修正观察器后 6487b3/0 得到唯一本来允许的 Probe size/SHA 更新，不改变原候选/预期，也不将观察器问题称产品失败。

没有新候选/87/保存故障/parser/archive/HTTP/SQL/产品/native/model/安装/收费执行。原 PDM 两入口只另片 SOURCE 关闭，本报告不继承实际 fault。SOURCE_STATIC 支持不授运行准入、不证明 Pydantic/Owner/native/整安装、真实媒体或 R1；完整 R1 后连续完整 R2 尚未验收。所有未测与原三次限制保留。

## 交接

正式 scope 为 SOURCE_REVIEW_FINAL。InputBefore/InputAfter 的 91 项全部 unchanged，自己的 CorrectionComparison 包含全部 1041 关系、六段完整 diff 重建、固定字节/87 数据、27 LF；CacheMapFacts 单列 364 关系。无 retained source reader 或目标进程。最后 Review 元数据 writer 的真实自然返回及无 live 状态由结束消息确认，不由报告文件存在推定。
