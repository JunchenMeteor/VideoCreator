# RV66 — B32 Owner TEXT 解码单片独立复核

2026-10-09，SOURCE_REVIEW_FINAL。RV65-P01 可 **CLOSED_SOURCE_STATIC（仅本固定 B32 版本）**；真实 SQLite/current/registry/replay/pending 和原目录/held/writer 运行层仍待独立 T47 正式证据，本轮未读取 T47 热材料。未发现这次单 `_decode` 改动的新源码阻断。原 T44/T46 红及未到达记录保持，未签 RuntimeBinding、实际 Owner、OS/vault、产品 Gate 或 R1/R2。

## 固定来源与改动证明

固定根 `G:/开发测试/Codex/VideoCreatorImplementation/Backend/OwnerBindingDecode-B32/`：

| 文件 | SHA-256 |
| --- | --- |
| B32Handoff.md | `9d478e3ef9e8906a7ef616bde97c1528b8ecf342d4d1ee7e9c7f03caf80c1541` |
| B32Handoff.json | `591b137669c7f6f120866da71b838f909ccc062d755d02b36b96844619d28454` |
| B32Interfaces.md | `2a128066fd4726a0e723c62dc23fd55934dc28e5c19cfcc9b58d7663a6fa26bc` |
| SourceSnapshot.json | `ccb1693a62db690464fd9148a26143f92b9c144bb173f1b00195286926bb76ac` |
| AcceptedSourceChanges.diff，823 bytes | `206f49c4ba68480a1ba0c9d36138bcda5b0b8950e3cd6d698b8d341864ff8475` |
| SourceCopies/services/engine/src/video_creator/application/owner_bootstrap.py，19846 bytes | `d53044244c7206420e7961f97dd09a75d9bd3d8a4fcf452ad7e2ceea3797dec7` |

实际读取新/旧完整 Owner 源，B30 Before SHA `35200d06bd2a54926a5914c0cb06c92e4f55d36c6e307219fc87a8f0315da996`。两处明确文本替换精确复现新源全部字节：函数加 `body: str`；解析前 exact TEXT gate，传 `body.encode('utf-8')`。移除各自 `_decode` 正文后所有其余字节相等，保护外部区域 SHA `b21071e09c2ef6f6c00a8d0cff26d4b512e624197fe721bce34c2715c7a40a3a`。因此原 current/OS目录/held cap/同 writer/floor 及其它 finally 等正文没有改写。

两个固定 source_map 的 58 个名字及 57 个未改源 SHA 逐项一致。这是**索引身份比较**，本轮不重复物理重核全部 57 个源/环境；实际复核必要 shared parser/canonical/EngineError、授权/assembly/API 的固定普通正文并核 hash。全部 22 必要独立输入末次 SHA/大小无漂移，完整路径见自身 `RV66Snapshot.json` 与 `RV66InputAfter.json`。

过程原落盘器 `5beef7` 自然 exit1，严格末核发现统筹为任务卡追加准确输入根：起始 SHA `0b237a5f4809a4d37402cce4b252d367fe3d5b4a5404454e4df8c57f8a7d1c3f`（1032 bytes）→当前 SHA `1188556b9b318b9cf417949af4c0114b4ebdf7d861ec673a1f4512ebbc17fb34`（1597 bytes）。`5348d4` 精确定位仅该治理变动；原正文按同 SHA 验证后保存 `RV66CardAtStart.md`，原失败/旧落盘器保留。实现/交接无变化，未运行业务或产品，不能将该元数据拒绝记为产品失败。

## 单边界与三个真实消费者

B32 `owner_bootstrap.py:72–89`：74–75 拒 `type(body) is not str`，76 严格 UTF-8 encode 后传原 bytes-only `strict_json`；77–78 仍将 `canonical(record)` 与**原 TEXT**逐字比较。未 strip、字符替换、自动重写行、填身份、捕获 AttributeError 或返回伪成功。81–88 原实际目录/record 主体检查保持，在成功解析后仍执行。

| 消费者 | 固定真实调用 | 结果边界 |
| --- | --- | --- |
| metadata 当前 Owner | `_read:91–93` → `_decode(row[0])` | SQLite TEXT 进入唯一严格转换，不改 DB/schema/text_factory |
| commands 同 key exact replay | `change:184–190` → `_decode(existing['result_json'])`（187） | 原 request hash 冲突及原 floor 完成/高水位检查保持 |
| pending 恢复 | `change:208–213` → `_decode(pending['record'])`（211） | 原外层文件 bytes parser 与 record:str/字段集检查保持；不新 start、不重置 floor |

这些源路径补上 RV65-P01 正常 TEXT 误送 `.decode` 的接口错误；未宣实际三消费者运行成功。原 initialized record、原 command 和 pending 外层协议不迁移，旧 DB 不用 SQL 改授权数据。

严格坏数据语义保留：非 TEXT（bytes/BLOB、None、str 子类等）被显式 TypeError；严格 UTF-8 编码的 UnicodeEncodeError 属 ValueError 系列，沿 79–80 原 catch 转 owner_binding_invalid422。模型/非 canonical 同该原 422。原 `bundles.strict_json:96–116` 的重复键、非有限数与指数溢出、坏 JSON/UTF-8 gate 未改；其 EngineError(bundle_text_invalid422) **不被 Owner catch 洗掉**。`EngineError` 不是 ValueError/TypeError，目录/权限/current 错误也未改成解码成功。这里是源码异常链，不是已发送 HTTP ErrorEnvelope 或独立运行坏数据样本。

原共享 parser SHA `687c2b51475593718ac9791733eb3ff15bf5c216bbb6bf8e302abc33b0028c04`、canonical SHA `3cfb8351560e53b97cded1fcc26748479da70694ca69d2e45c7506d86c59b823`、错误类 SHA `4bb8b859a340af0cd6f6093a5f97863c00e7f02d0a5f9ff95f523da389c6e6a5` 均实际核普通字节。原字节调用方契约、公私鉴权、预算/Op/unknown 没有借类型修正扩权。

## 附加两处测试 oracle：按实际动作区分，不宽匹配求绿

以下是统筹明确请求核查的 **SOURCE_CONDITION_ONLY**。未读 T47 未正式 fixture/result，也未改原 T46；没有宣称这两条件在原 T46 已到达。

**C06：直接修改 self.store.os_identity，实际 inspector 身份未变。** B30/B32 `assert_current_directory:61–70` 在 62 取得真实当前 identity，64–65 与已锁存基线不等立即抛 **owner_directory_changed409**；current 的先行 guard 在 B32:119（B30:117）。B30 接口已明确新增“变化409”，不是此 B32 单 decoder 改了状态码。旧 B29 `_decode:68–74` 仅用 cached self.os_identity 和 record 比对，其 mismatch 分支为 owner_binding_denied403；实际 T46 因 decoder 错误未到该旧分支。新命名 oracle 应对“直接改变 Store 基线”精确期待409；保持“当前基线未变但 record 实际主体/绑定不符”在 B32 `_decode:83–88` 的 **owner_binding_denied403**。必须保真实目录/current 拒绝、旧 cap 与 held/writer目标；禁止把状态码改为任意403/409/503或用模拟基线变更替代实际目录替换。

**C09：nonmanagement 私有 service.get_policy，management=None。** B32 `owner_services:66–68` 的 for_management=False 构造 registry=None；私有 `get_policy:257–258` 首先 `_principal`，37–39 明确 **production_management_unconfigured503**。旧 B29 同 `_principal:36–38` 和 get_policy:250–251 也是503，属于原私有配置契约，原403期待把层次混淆。固定 B32 `api/app.py:135–142` 公开 management_access 对缺/普通 bearer 返回 **production_management_denied403**，origin 403也保留。Test 新命名的具体 private 缺配置 oracle 可精确改为503，同时保公开普通身份403；不得补 management、授 cap 或改生产默认制造成功。

固定授权源 SHA `dbec8e2002a00c39c7c908e8636f0db66d73a908c38bdf99ca88dcd0539bf6ff`；assembly SHA `57ea29425bb0e71b7d920ff292c21a3630421fdfb975d29cc23fddc3d57e5968`；API SHA `5ec7b2d786f17e2441f9a6ee10b698cb1a0cd0089ac73fd53030777373616e56`；旧 B29 授权源 SHA `6f34f1bcaf8093661a4b0a8774876ffdcbc6f70884d39db8eb6419d3b14e6a60`、bootstrap SHA `37b9d13a214d03283a32effd4a0dd0c3dcab7e140e65f19891855cc7abd2f694`。以上实际普通正文和源行均核，未读取 current SDK/API。

## 未测与终态

B32 原 StaticReceipt SHA `893ea5fd89d770685cda2fd7a64c8d35c0d2993d2824963141e93aae0d7b4e77` 记录 owner25952、Ruff launch6852、wait/return0、communicate EOF、streams closed、drift[]，physical PID/Job 未证明；只静态 AST/copy/diff/Ruff，未 import 产品或运行 Owner/DB。本评审未重跑该命令，不以它代 T47/OS/许可或生产资格。

RV65-P01 仅固定版本 **CLOSED_SOURCE_STATIC**，运行闭合另待 T47 正式真实 Engine/SQLite 三入口及坏数据证据；原 T46 12=1pass/1failure/10errors、C11 未达、main1/driver0、两 Test 接线缺口仍保持。本次测试 oracle 纠正不改历史，不删原目标，不批准重新执行或降低任何标准。RV63-P01 仍只已有源层限定支持，不能扩大为全部 OS TOCTOU 已解决。

全部必要读者关闭释放；无当前生产冻结、无产品/测试/DB/OS/secret/ASR/provider/network/install 执行，费用0。仅自身 Review 过程及 docs/reviews 写入。完整三 OS R1 独立验收后连续 R2、实例持有数据与五步前台均保持；有限阶段完成，不等待 T47。
