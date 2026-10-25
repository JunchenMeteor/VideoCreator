# 0073：本地素材计划的绑定键

状态：FIXED_ARCHITECTURE_CLARIFICATION / PENDING_INDEPENDENT_REVIEW。仅澄清0072§3.1的连接语义，不改0072原字节，不关闭CPSC-I01源码/运行问题，不增加资格或权限前置。

## 唯一规则

`registered-local-material-plan-v1.input_bindings` 每项的exact字段为 `binding_id,asset_id,sha256,size,media_type,probe,source_ref,usage`，即0072原七字段加一个明确的 `binding_id`。其余字段类型及实际资产核验保持原合同。usage只允许大小写精确的 `narration`、`visual`、`background_audio`。

Backend唯一grammar固定生成/校验规则：先按原Identifier校验asset_id和usage枚举；对仅含 `asset_id`、`usage` 的对象采用严格JSON编码：按键排序、紧凑分隔、ensure_ascii=false、无NaN，UTF-8无BOM，无尾换行，不做Unicode归一、大小写转换或trim。将完整编码字节SHA-256的小写64位十六进制加前缀 `b-`，得到binding_id。这是连接标识，不是授权、来源证明或文件hash；Media使用Backend方法/已解析结果，不定义另一个算法。

binding_id不含plan自身hash，因此没有自哈希循环。同一真实asset_id、同一usage在计划修订和幂等恢复中保持相同ID；SHA/size/probe/source_ref是绑定事实，仍完整写入不可变计划哈希并受当前资产/来源/权利检查。相同连接ID不能替换这些事实。新资产/新源版本按原真实Asset和计划版本机制处理，不就地更新已准计划。

连接作用域仅为当前已准不可变计划的 `input_bindings`。跨Production/Run有相同文本ID不构成可跨域访问：必须先取得原同Run/current/lease/fence及原计划，再在该计划集合中精确解析。不得按全实例“搜相同键”、asset_id回退、前缀/hash截断、列表顺序或最新计划解析。

## 合法复用及引用

计划内 `(asset_id,usage)` 唯一，binding_id也唯一；每个键对应一份完整绑定事实。重复定义即使字段全部相同也拒绝，不自动去重。多个镜头或多个音轨可精确引用同一条binding，不要求复制输入Asset。

同一带实际视频与音轨的Asset同时用于visual和background_audio是合法的：两条binding的asset_id/SHA/size/probe及真实source_ref保持该资产事实，usage不同且ID不同。各用途仍分别通过原rights/current检查；可读取不等可混音或再分发。相同Asset同usage的多次剪切/映射用多个shots/audio_tracks引用，范围在各引用上，不新增歧义binding。

shots的input_binding_id必须等于当前集合某个binding_id，且该binding.usage为visual。audio_tracks的input_binding_id必须精确连接narration或background_audio；用途直接来自binding.usage，不从track_id、文件后缀或模型描述猜。各用途所需实际媒体流、源范围/时间线范围、原解码与音轨映射由既有driver/timeline验证，不能凭合法键伪造可用流。

所有timeline引用都必须成功解析；不要求每条已准输入一定被当前timeline使用。未用输入不授副作用、不冒最终作品来源；实际输出lineage只登记真正消费的binding与范围。

## 失败与兼容

Backend唯一parser在准入前对缺/错binding_id、非exact字段、重复键/重复pair、悬空引用、引用usage不符、算法不符返回具体422，未调用媒体或provider。实际Asset字节/来源/计划版本漂移和原current CAS/fence冲突继续按既有409/权限拒绝处理；来源权限不因该连接键而扩大。未知Operation、READY恢复和收费规则不变。

新local plan的sole v1类型尚未在该冻结基线中实现，因此本澄清补足同一设计grammar，不迁移或重写已有业务记录。七字段或把input_binding_id当asset_id的未完成草案不是合格v1输入，不默推导修正；旧0072文档作为原设计历史保存。其他旧媒体/生成/修订格式原样支持，不能拿本规则改其hash或错误语义。

Backend负责唯一schema、严格canonical连接方法及parser；Media planner经该方法获得ID，Flow/driver只消费唯一已解析绑定与原真实Asset。Integration仅从后端源生成契约/SDK。实际目录白名单优先：`application/media_registration.py`的host分派/typed接口/final-context归Backend；`workflows/current_engine_production.py`的composer及workflows/providers/media生产代码归Media。此澄清不阻挡authority、首Goal和固定factory可独立实施部分。

独立设计评审后，后续实现/测试应覆盖：同Asset两usage合法；同binding多个镜头合法；重复定义、错误ID、悬空引用与usage错误拒绝；同键事实漂移拒绝；同ID跨Run不能读；恢复不重分配或新增收费。这里只列必要验证，不实现测试/改变标准、不授运行。

固定输入：0072 SHA `1c4fc5782213a364b1504bb9b9456ede231f7f1cdac8d780e309cb0722aceec3`；停止Finding-CPSC-I01 SHA `37c52afbe4e92b29a80c83826da825f7f6f67ec3a452497cd79fcddeaa8044e7`；任务卡SHA `862e29908bc052fe75816c4a6bea56cc05ed0ac34e4689bbbf496cdb67ee1f39`。完整R1独验后连续R2、真实媒体与多模态质量/费用/权限全部保持。
