# 0069 四制作角色与可选证据角色的基数

状态：DESIGN_ONLY_READY_FOR_INDEPENDENT_REVIEW。本澄清仅消除 MRPL-I01 的基数歧义，未批准源码、测试标准、运行或资源资格，未关闭 MDG 功能。独立评审决定该设计问题是否关闭。

## 1. 唯一数量与顺序

ADR0065 §2.1 中“恰好四项”准确指四个必需角色，不指包含可选角色后的总数。`registered-component-diagnostic-methods-v2` 的 `role_bindings` 只允许以下两个完整序列：

```text
[director, visual, sound, editor]
[director, visual, sound, editor, evidence]
```

必需角色数量为四；可选 `evidence` 数量为零或一；总数为四或五。证据角色只能处在第五项。缺少、重复、换序、插入未知角色或第二个证据角色均非法。可选角色不存在时省去该项，不补空绑定、空结果或伪造 Operation。

每项仍只有原 `role_id`、`method_id`、`method_version`，不新增 DTO 字段、格式或 authority。引用必须指向本次真实注册中唯一存在的 `(method_id, method_version)`；四或五项使用四或五个不同 method。method 内容、完整资源身份与原 method_ref 的真实性检查保持。

## 2. 未绑定 method

V2 catalog 的 `methods` 与 `role_bindings` 引用必须一一对应：两者引用集合相等，数量同为四或五，不允许重复注册引用。`methods` 原数组的编码与排序规则不变；只有 `role_bindings` 的角色顺序由上节确定。

未绑定 method 在本 V2 catalog 中拒绝，不能作为潜在 evidence、动态 agent、替补方法或任意选用方法。需要可选证据方法时，必须显式登记第五个末位绑定。ADR0065 保留的 `methods` 原 1..16 上限只是一项继承的外层上限，不授予 V2 增添第六项或隐藏方法的能力。旧 V1 catalog 的合法范围、选择方式、默认、原字节与哈希均不改变。

这将 ADR0065 “其余 methods 只能明确登记为 evidence”与“可选 evidence 最多一项”合并为一个严格判据，不以静默忽略未绑定项实现兼容。

## 3. 贯穿选择、结果与恢复

- `current-component-diagnostic-input-v3`、`registered-component-diagnostic-input-v3` 使用原受控来源中同一完整绑定序列，不能由模型、renderer 或任意字典替换注册关系。
- `select_methods(inputs_v3)` 仅按该序列返回原已登记的 method/intent。四个必需角色必须分别履行 director、visual、sound、editor 的原职责；共享模型或 route 不合并 method、原 intent 或 Operation。
- `current-component-diagnostic-observation-v2.method_observations` 和 `current-component-diagnostic-fact-v2.method_results` 与同一输入的绑定一一对应、同顺序，完整结果数量为四或五。每项都来自该 method 的原真实、成功且 settled 的 Operation 与输出；第五项存在时同样适用。
- 一条 Operation 或一份模型回复不能冒充四个角色。method_ref、input key、check ID、真实资源 completion 消费、父 edit lineage 与当前来源校验沿用 ADR0065；本澄清不允许新权限、未登记引用或取消完整验证。
- 部分结果保留原已持久 Operation；unknown 仍走 needs_reconciliation。冷恢复复用真实原结果、原费用与预算，不能为填满基数重发或换 key。完整同输入的 immutable replay 与不同字节冲突规则保持。

非法基数、绑定与结果关系由原 strict dispatcher/validator 拒绝；真实资源或 Operation 尚未就绪仍按原状态报告，不因四项数量正确变成成功。V1 原读取与真实历史事实兼容，不将旧单方法事实改写为四角色事实。

## 4. 唯一职责与必要独立用例

Backend 唯一维护原 V2/V3 类型、strict dispatcher、注册与 held reader 关系，并将同一基数判据用于 catalog、输入、输出与事实校验。Media 仅按原登记绑定调用并消费真实 Operation。Integration 的 producer/resource closure 输出同一登记内容，不从 manifest 或配置推导权限。无需新增公有接口、SDK 字段、迁移或前端内部技术字段。

Test 在自己的后续标准窗口定义并独立验证：合法四项、合法末位第五项；缺必需角色、错序、重复或中间 evidence、两 evidence、未知角色、未绑定 method、外部引用、重复 method/Operation，以及部分成功与 unknown 恢复。共享模型但四个真实独立 Operation 的合法路径必须保留。这里列的是未执行的需求，不是已批准或已通过的测试。

原独立 Review 单独核本澄清与 MRPL-I01；Acceptance 后续依据实际角色协作、父 lineage、冷恢复与成品结果判断功能，不凭本文件关闭 MDG 或宣布 R1/R2 通过。

## 5. 固定来源与兼容边界

本澄清只取以下停止正文：

| 来源 | SHA-256 |
| --- | --- |
| ADR0065 | `c88eb3620d0567cb3aa349c1fd4bd952e8c944342e19546c7e8f27da803fd313` |
| MediaRoleAttributionAndParentLineage-IndependentReview | `bfcd0aa77a4f1d885152a9409685d3a4d4e2c03c9d3e1baf1c800af14d1f1a75` |
| Finding-MRPL-I01 | `d51277b3c50377f380fc58b43f6edcd14a15102e5b72aa4bf26c6d1afcc04050` |

0065 与正在独审的 0068 原字节保持。本文件不改其他章节、producer admission、质量阈值、权限或预算。完整 R1 独立验收后连续 R2 的目标保持。
