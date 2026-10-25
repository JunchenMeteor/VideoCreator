# Piper 六归档数据检查执行任务

角色：原 Integration；统筹不执行、不兼任独立评审。完整目标仍为 Gate0、独立 R1 与连续完整 R2。

## 停止基线

准备交接已 TRUE FINAL：e4f4f2、b19fbe 自然退出0，全部读写释放。根目录为 G:/开发测试/Codex/VideoCreatorImplementation/Integration/PiperSixWheelDataInspectionPreparation。
Plan 43442B SHA256 042067363c2bc20345856cbbf952147391616435bad13380f7ac5a7f7c0a34c3。
Helper 36457B 46d2a127083ea81bcdb30773ba227cd32de3106e42fe710b28f3fbcacce1dc9e；Runner 8833B b9933bce1c3ce679726634cdbf78f87de04ce69edb05cd47ba832a6432faf32f。
完整差异 88784B/1562行 395dd4d9908ccb21ead6e570ea477f31eb445809b9190ef4cf1e62e32dc91c0c，统筹已分段完整读取；Plan/helper/runner已完整消费，首次混合截断保留并补读。
正式 Handoff.md 2d314a9a059687fcb0f0096c8582c31420d356ae65205fca0172d4e40240be3e；Handoff.json 68bc18ac0245870febcfc5122828294cc57ba5f75b650adbc4051b2e871f728a；FreezeReceipt e90b9837d976f94eadfbcb81d37c1c3d4f70fc947aa77f389a9f357a5bc12199。

## 唯一执行

复核任务卡、仓库规则及上述停止输入后，只准一次现有 runner 调用：

```powershell
& 'C:/Program Files/PowerShell/7/pwsh.exe' -NoProfile -NonInteractive -File 'G:/开发测试/Codex/VideoCreatorImplementation/Integration/PiperSixWheelDataInspectionPreparation/RunDataInspectionRoundOne.ps1' -PlanSha256 042067363c2bc20345856cbbf952147391616435bad13380f7ac5a7f7c0a34c3
```

CWD 为准备根目录。64固定输入与6轮件总4425126B保持；运行前 DataInspectionRoundOne 必须不存在。唯一运行输出白名单为该根下 DataInspectionRoundOne/（含 Temp、原始两流、收据和 TextViews）；不修改工具、计划、旧阶段或任何产品源。
只读取六已下载轮件及同版本已保存 JSON；HTTP0、供应商导入/安装/原生加载/模型调用/费用/密钥读取均0。不得递归下载依赖、调用 pip 或变换范围。
保留原压缩/展开/条目/比例/RECORD/METADATA/文本上限；完整 CRC/EOF/RECORD/WHEEL 和原 Requires-Dist 多重集对照，markers/extras不激活。完整可用源码、风险资源及许可证只输出原字节；缺原生对应源/许可明确列缺口，不虚称合法分发。
持原真实 Process 与双字节流直到自然终态和两个 EOF；900秒超时粘性记失败，不 kill、不重启、不改 namespace 重放。第一错误保留原始/部分结果，后续归档 NOT_EXECUTED。观察超时继续持原句柄，不把会话超时当进程终态。

## 交付

报告实际工具返回、子进程 argv/cwd/pid/creation/exit/natural_terminal/两 EOF/timeout/errors、64输入前后和六归档状态。完成后仅有限只读消费所得收据与普通数据，先消息交接实际终态；后继正式复制交接另行安排，当前不创建额外执行批。
数据通过仅支持归档完整性；不授 TTS/CTC、ABI、四目标安装、三OS、R1/R2 资格。原 Regex partial、其余8直依赖、colorama/hf-xet、音色/模型/G2pw资源缺口及原失败限次保持。真实收费20元总上限与已耗尽次数不重置；不触发原19产品目标第四次。
