# RV59：F8 当前 F10/I44 类型与静态构建独立证据评审

结论：**FINAL / LIMITED_TYPECHECK_BUILD_SUPPORTED**。本轮固定 F10 与 I44 输入下，原 native noEmit 与 Vite build 各一次自然退出0的证据成立，四 Dist 产物与原 raw 相干。未发现新增阻断 Finding。没有执行编译或产品；不授真实 UI/API、installer/native、完整制作、三 OS 或 Gate/R1/R2。

## 固定身份

正式 F8 MD SHA `4f5e79bf4788723aed1f0386dcc8e344d330ed9bc53ce04aa15fbf2c06302deb`；JSON `55dc2cb234173bc02b6c393a7585bc4670d83d991478343e1ccd72ccf6249b7b`，本 Review 已完整读取/解析，未使用统筹曾截断的中段倒填结论。准确根 `G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchVerification-F8`。

本片56必要路径的完整 size/SHA 均匹配，前后漂移0：F8元数据/runner/Entry/Plan/原raw、F10十一普通源和snapshot、I44八固定生成普通件及有限data正式/原收据、四已有配置、四Dist、规则与任务卡；逐路径见RV59Snapshot/SourceAfter。未重新盘点1380/8500依赖或全机，未读取当前SDK/活I45/Test材料，未重跑Node/TS/build/UI。

固定 F10 Snapshot `480e257504d689ad78a19d20cabb7a652e8245504c28c0b60b83b8ff1cf2cfd4`；helper `b1c085fcce215a2e90b035f6df45091bc5276661ffdb1991c6856e9f8ef8f573`、Workbench `6cc07b96c542668dbf3378efd88dcf8d3f0e64d7148fb21cf582cb6a5bad9b39`。两个保存的运行输入索引均包含F8正式声明的全部F10生产/参考、当前SDK/固定I44普通字节，逐条size/SHA一致。十一F10生产/ordinary配对、八I44generated/ordinary配对一致；本Review仅重核固定ordinary，不把后来当前源读成原运行身份。

## 原命令与原始结果

类型顶层命令见TypecheckEntry：`C:/Program Files/PowerShell/7/pwsh.exe -NoLogo -NoProfile -File G:/开发测试/Codex/VideoCreatorImplementation/Frontend/WorkbenchVerification-F8/RunTypecheck.ps1 -RootAdmitted -ExpectedInputsSha bbf9a7b34efd52ff1356b3914e34c1fe93d7949203148f65a2fdb40d8ac4edf4`；cwd为 `G:/开发测试/Projects/VideoCreator/apps/workbench`。Entry.runtime_or_compiler_executed=false是启动前准备字段，与已执行Terminal分开。

唯一child为原已安装 `@typescript/typescript-win32-x64@7.0.2/lib/tsc.exe`，运行输入记录compiler SHA `f9ecfbdc93753d2c972d66a8d0d75f5bd737fd4a5f88b422d9091ea282bcb2c7`；argv准确 `--project G:/开发测试/Projects/VideoCreator/apps/workbench/tsconfig.json --noEmit`。Started/Terminal的PID35416、creation一致，2026-10-09T11:42:54.9829335Z→11:42:55.3439492Z，Process墙钟0.361016秒；native_exit0、faults[]、同原Process自然终态。stdout/stderr各0B，空字节SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。原顶层工具64065c actual0，由正式交接记录，未重跑。

构建同cwd，顶层命令以RunBuild.ps1/ExpectedInputsSha `b1ca078f11af15a4fa9729e2b8842292dd51b1324524ba5964dfb7e3ceaf65f0`进入独立一次构建。唯一child为原Node `C:/Program Files/nodejs/node.exe`，输入记录SHA `9a4eb5f1c29c6a2e93852ead46b999e284a6a5ca8bab4d4e241d587d025a52de`，argv仅本根BuildOnce.mjs。PID24688/creation一致，11:48:48.9131760Z→11:48:49.5271128Z，Process墙钟0.613936秒，process_exit0、faults[]；原顶层0955c7 actual0。

构建stdout真实689B，SHA `314a21f993dbdc8c8b7ac457dc382f6cd0621252c32478af4485a0b0c9dd847f`；stderr0B。原输出明确Vite8.3.3、2203模块、337ms构建记录、实际文件路径及gzip数；337ms不代Process墙钟，更不证明界面速度。没有诊断过滤、改写raw或吞退出码。

## 配置、输入边界及自然收尾

RunTypecheck.ps1:9起的Assert-VcInputs逐项size/SHA及link target校验，启动前调用；原Process自然退出后第109行再次调用，成功才source_inputs_unchanged=true。RunBuild.ps1同样启动前/第110行后检查。保存索引的类型1380输入/630links、构建8500输入/649links与Entry计数一致；对应两原Terminal的后置guard通过、faults[]，故支持这份有限闭集前后未变。

**这两批没有另存逐文件After观察文件**：后核证据来自完整runner的实际Assert-VcInputs及原Terminal，不称为独立重新取得的after向量、实际文件读取trace或全环境证明。本Review56路径的SourceAfter属于本次有限阅读身份，不冒充原编译1380/8500全量After。固定索引是静态有限超集，links不是OS沙箱或原子Job。

现有tsconfig SHA `e023861a7e63d7c20dae3cffcd6868c5402bc4aa5a4abeea61105468889b19a4`，strict=true、include=src、noEmit=true；原skipLibCheck=true保持，因此不宣称检查所有依赖声明内部。四配置在原输入中有pin并与本次字节相等，没有换空src/豁免应用诊断。package脚本`tsc -b && vite build`未被声称本轮执行；此获准入口是明确分开的native noEmit及Vite API build。

BuildOnce.mjs:5–19直接已有Vite8.3.3导出build，实际生产vite.config.ts/native configLoader，envDir=false，自有cacheDir/outDir，emptyOutDir=false；不换loader、生成源码或覆盖生产/旧F5 dist。固定Vite config `3d28355a199e96a30d01608cc7d881fd4b6528b5b0c6613ec4fe35dd5c76733b`保持ES2022/sourcemap、原插件。build command下trusted-origin define=undefined；原closed环境清空，仅SystemRoot/WINDIR/PATH/TEMP/TMP与build NODE_ENV=production，无engine/bootstrap/token。

两个runner的完整try/finally均保同原Process，原BaseStream→CreateNew FileStream；自然terminal后等待两个GetResult，再Flush/Dispose、后输入核及Terminal写入。任意capture/观察错误锁faults/rawCaptured=false，fallback只为继续drain，最终仍exit1；正常只exit原childcode。成功Start后的观察/写错误不Dispose live，也没有Kill/restart/PID替换。原两Terminal.raw_streams_complete=true与实际raw文件一致；未将正向证明扩到所有异常分支、OS Job或后代清理。

## 四产物与历史原红

BuildArtifacts SHA `c733da222596fa320e8a0740b00ae955febe7d9cc9923cddf8c554e0c01211ee`：

| 文件 | 实际字节 | SHA-256 |
| --- | ---: | --- |
| index.html | 454 | bef4d9b86a2fe8dd9c57baf038b1963bdd2ddd2425da8b775859f0cb0f703c85 |
| assets/index-CVHwtNLb.js | 493919 | 72b1a8698f0d7f4a4d9f46f14fe0d20616f2a077e07d7079854dd01415325537 |
| assets/index-DIbVb5c7.css | 704866 | 92cefe757cb3d0cf2ec90b29b2f16ff846acbf9470610f17c6299a9c82ed2e9e |
| assets/index-CVHwtNLb.js.map | 3076159 | 60530876e956dcc0f1cafd8f3d660f498cb2492505dc3eb7c9259cd06b4f2690 |

HTML两个资源引用均指向实际对应文件；map.file与JS文件一致、JS sourceMappingURL相干。仅以stdlib解析既有map，九份被嵌入的F10应用脚本正文SHA精确匹配；App.tsx纯reexport没有单独map条目，不能据此称源码缺失或全十一文件均嵌入。map/非空bundle不是UI操作、安装或作品证据。

I44有限data正式MD `5de18e8915c1f9f75fc50984ee7c395870096888fcb646f91dccea30fd8cf30f`/JSON `92047b3216d18354e3d487b63d7fe63e314c5bfde0c754b84ddd8c5040668d40`，原OwnerReceipt与ComparisonReceipt匹配。其existing记录data0/438 checks/first_difference null、80数字表示差异精确数学等价、新输入变化[]；本片没有重新实现或运行完整契约checker，不外推权限实现通过。原生成overallFAILED1和缺248 original before保持，new after无法补原执行前闭集；本次前端自然0不能把历史生成批改成0。

F8正式记录的b2aa7e猜错旧Plan.json与e6f79f路径/hash数组构造actual1、工具调用前JS引号错误、首metadata session52432经同句柄965b96→e2276a自然0全部保留；本Review未重演这些错误或以当前绿洗原失败。它们与本次type/build实际各一次区分。

## 有限结论与后继

本轮noEmit/build原证据可支持当前固定输入的类型检查和静态打包；无新增阻断Finding。RV57两source closure不因本批升级为真实React恢复/跨实例/取消通过，原T38/F6绿也不继承F10。真实UI、host/API连接、安装器/native、媒体/ASR/成片及完整Bundle/导出引用、三平台独立验收均待。完整R1独立验收后连续R2总目标不缩。

本Review只读固定材料及stdlib解析，编译/build/GUI/DB/API/native/ASR/provider/network/key/fee/源或标准修改全部0。56必要输入前后无漂移，全部reader已释放、无live；最终自有metadata写命令须由调用方观察actualexit0后发送FINAL。
