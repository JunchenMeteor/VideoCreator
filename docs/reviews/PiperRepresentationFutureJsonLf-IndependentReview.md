# Piper future JSON LF 独立源码复审

结论：PDRTC-I01 的受控 Python JSON writer 缺口在本固定版本可判 CLOSED_SOURCE_STATIC_ONLY；原 PDRT-I01 中同一未来 writer 子项仅在源码级闭合，原历史记录不改。不发现新的阻断源码问题。本裁定不整体替代 PDRT-I01 其他范围，也不授予运行。未来 JSON 输出、87 项候选、保存故障注入均 NOT_RUN。

本次只审原 Test 的 immutable LF 修订、共同 save 函数、完整旧源码保护及必要路径/大小/SHA 关联。没有启动 Python、候选/parser/cases、产品或运行时成员；没有 archive、HTTP、SQL、native、模型、安装、费用或密钥访问。完整 R1 与其后完整 R2 未验收。

## 固定版本

正式根：G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/PiperRepresentationFutureJsonLfCorrection/

- 任务卡：65bb298324923187dd83ca77c81d7d3648d956bef409ed0b4c7a667d80047489。
- LFHandoff.md：bc70052bbd79487dad8d2dba155af25ff2462651f774d324a66abbece1c94a00。
- LFHandoff.json：417495b1f0310c7d47e94784affb8cc8dfe135b1058f706dc60b5751d23bb96c。
- ActualInterfaces.md：66822974927b30a63a466e6f8a8060cba6f4aee1aaf32146a96266d2a10d3d55。
- SourceStage/LFOrdinaryIndex.json：6c678753c05e4840e77637106106c69646b588e62579997919b466476c637ac2。
- LFSourceSnapshot.json：53dc65068be223a45660ca7e82369ad7fe35f360d7ad70c61f023b8621063fef。

69 个 source/ordinary 对的实际大小及 SHA 全部匹配。含治理/原 finding 等控制输入共 145 个独特有限路径，InputBefore 到 InputAfter 无变化。没有重新读取或扫描 999 个运行时文件；999 仅为既有冻结索引声明的逐值比较范围。

## P3 的具体闭合依据

唯一新实现源是 SourceStage/Ordinary/Input015-ProbeRepresentation.py，17974 B，SHA d065f669787e2f8b10b8cec0f66a68b97507acc5a4b3a0a3f356a24a41356af2。

原件为 Input045-ProbeRepresentation.py，17960 B，SHA 604a94e5527ac83fc223bfc45f6ee94174e9a83c8774d88f754bf90537065e26。

实际新源第 263 行在原 Path.write_text 调用中增加唯一的 newline="\n" 参数，增量 14 B。独立从整份新文件删除这一出现一次的参数，所得全文精确等于旧文件；共同 save:262–263 的序列化值、ensure_ascii=False、indent=2、allow_nan=False、尾部换行及编码保持原样。所有 Startup、完整/partial results、CacheReadEvents、InputAfter 和 Summary 仍经过此共同函数。

原问题是未来 writer 未显式固定 LF，而准备 JSON 已是 LF 不能证明它。当前参数确实位于将来保存的受控调用，因而满足该源码修正要求。没有实际运行输出，不能宣称已观测 Windows 写入 LF、异常保存终态或全 87 通过。

FullSourceDiff.diff，54791 B，SHA 7bffe943a09cf61d83397dfe07e19dde211ea74f9fb862cf31c6e1a8c2aa6744，包含两份完整 Probe 与两份完整 Run。独立提取四段，分别与实际新旧全文精确相等。FullSourceDiff.txt 的 123457 B/852012f9... 是保留的前一版大差异，不把它误当本次增量。

Run 的完整新旧字节同为 cf9b189554c51b697ac9a07d51f21732f67830217b2010acf6cb82589537abfa；Cases 同为 8dd5dc91509f19ef92cf5628bf2a1072291068ecd2f827d9e83b70b6b42014e0。全部 16 对 FixedInputs 逐文件大小/SHA 相同，其中完整 parser 保持 9eae0ad968c464189810a62e0ecf2579a2dc5ef11de1fc6dd3b523e3018ac382。未抽取或执行被测函数，也没有改 oracle。

## 关联与控制流保护

新 RepresentationInputIndex.json，607402 B，SHA eebc3fde031942f040df11628c43c358e6c40a3b8b20b2e49f2579f3d5c62d3d；原 Before 607722 B/e6b82ba3809142ded10c50a04f102fcd821ae196d7bb9c5a756b5554da53cd67。

独立递归比较全部对象键/数组位置和值：允许的差异只有候选专属根迁移，以及 Probe 的 17974 B/d065... 身份和它对应的唯一 cache map source_size/source_sha256 更新。1041 条记录、364 条缓存映射残差为零；999 条原运行时声明完整相同，未以数量相同代替逐值比较。

FutureLaunchRequest.json，1290 B，SHA 63a0b824fbb6a5e2eba6c6e7726cb958b79685f5af0a8760e66c9c93ed2049c3。解码后的完整 argv/cwd 指向新 immutable Run/根，ExpectedInputIndex 对应新 SHA；index 身份、专属 LauncherRoundOne/MethodRoundOne 与新候选关联。保存索引中的原解码路径表示，未默默改写请求。其 runtime_approved=false、ready_for_execution=false、实际数量 0、计划 87、原旧19累计 3 均保留；不是运行许可。

逐全文控制流核对：原完整启动身份、同原 index 字节首解析、physical/fileidentity/SHA 读取门、原 FileLoader code identity 缺失缓存例外、audit/禁止网络与外部写、独立末 index/member 核对保持。Python save 后续异常和 finally 仍为原控制流。Run 的原 Process 对象、原 handle/creation、实际 byte stdout/stderr 两 EOF、原时窗、首次失败 sticky/原退出码及 finally 后身份检查保持。这里是源码保护支持，不是实际生命周期或故障通过。JUnit 的原二进制 XML 写入亦未改。

## 原失败及本 Review 的证据限制

原 Test 的 e9e5ad、1b8575、c38944 准备失败及后续 formal LF 修正记录保留，均不改称 87 的失败或通过；原 literal 差异、旧19三次实际失败、原 17+1/2/12 pure 等历史不覆写。有限新 JSON 数据检查是 .NET 元数据观察，不是 Python/parser/87 实验。

本 Review 原始工具错误也保留：首次 functions 输入因 JS 模板中的 PowerShell转义符而在工具编排前 SyntaxError；844356/1 为自有 PowerShell 数组表达式把目录误送 ReadAllBytes；7b1b12/1 为自有 Compare 名称命中 PowerShell alias。d99a9e/0 的两条同值 17974 误报来自自有赋值 Int32 与 JSON 解析 Int64；原 IndexAssociation.json 保留。修正为原整数宽度后，仅重算原有限 JSON：9565e3/0 的 IndexAssociationFinal.json 残差 0。这些不是目标源码漂移或候选失败。

最后有限 after 原 functions cell 183 按同柄自然完成，172156/0：145 路径的 source/copy 与 before/after 差异均为 0。当前没有 live handle，停止全部冻结源读者。后继真正 87 及故障实验仍由 Root 独立准入并交原 Test，本 Review 不代授权。
