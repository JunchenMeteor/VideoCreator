# 0073 本地素材连接键独立复审

裁定：CPSC-I01 CLOSED_DESIGN_ONLY；可交 Backend 实现唯一 local plan grammar、Media 消费该方法/已解析结果、Integration从唯一源生成契约。未确认新P1/P2。源码和真实制作未被本设计复审证明，旧0072、原Finding及0072独评报告不回写；authority/同Engine首Goal/factory可独立实施，不新增发行资格门。

固定全文：Architect/LocalMaterialBindingIdentityClarification/Ordinary/0073.md，5227B，SHA8aa56933bb0f3d285f598b309a1f327e67cf4715d4276913ee1f565f7ae837a0，共35行。六普通副本大小/SHA均与OrdinaryIndex一致；其SHA ee4ddb3a39cae0623d0443fbaf5072a2d7790a8063da76b521a9995e2384ef4e。正式Handoff.md563d5591337e43b00e3dbc8bc6ea8814349798be064483daec8072d73f4b90fb、JSON7af6865263c272d6e4da81b7bbfd7418dd46ac73a18cf5fbc7c9ded517108db0及列明正式文件独立核身份一致。本卡SHA7a3e955966892048c1bb7b677c008de0ef00281696caa5fa75a141130576c7fe。

原0072第90–98行与停止Finding全文复核；两AGENTS字节等于本角色上个窗口已全文读取的治理版，未重遍旧53源。新0073、架构Task/Delta/Interfaces/Impact全文读取，InputPins/索引/SourceAfter作为有限metadata解析。原SourceAfter只作者metadata interval，不推出此前整个阶段无漂移。自有InputBefore/After对六普通、八正式、本卡与原停止报告共16唯一路径逐值比较differences=[]，没有环境树扫描。

| 原缺口 | 新合同的唯一规则 |
| --- | --- |
| 七字段没有连接键 | 第7行固定八exact字段：binding_id,asset_id,sha256,size,media_type,probe,source_ref,usage。 |
| ID编码/作用域不明 | 第9–13行先校验原asset_id及大小写精确usage；只编码asset_id/usage对象，键排序、紧凑分隔、ensure_ascii=false、无NaN、UTF-8无BOM无尾LF、无Unicode归一/trim/大小写转换。前缀b-加完整小写64位SHA256。只解析当前已准不可变plan集合，不跨实例搜键/回退asset_id/截断hash/按列表或最新plan猜。 |
| 同Asset两usage冲突 | 第17–21行(asset_id,usage)和binding_id都唯一；video/音轨同Asset的visual/background_audio是两条不同键、各自原rights/current核验。同usage多剪切用多个timeline引用同一binding，允许多shot/track复用。 |
| 引用错误被默修 | shots只连接visual；audio_tracks只连接narration/background_audio。第27行缺/错键、非exact字段、重复定义即使完全相同、悬空/错usage/算法不符在准入前422，未调Media/provider。 |
| 键取代事实或循环hash | 第11行键不含plan hash；SHA/size/probe/source_ref仍完整进入不可变plan hash，真实资产/权限/current/lease/fence/409拒绝不变。相同ID不是authority，不能替换事实、就地修改旧计划或解锁unknown。 |
| 旧格式/草案兼容不明 | 第29行sole local v1尚未实现；本规则补同设计grammar，不迁移历史业务记录，不自动推导七字段草案，其他旧媒体/生成/修订格式及hash/错误语义保持。 |

未用binding不要求删掉，且不授权额外副作用；最终lineage只登记实际消费的binding/范围。媒体流、源与时间线范围、decode、音轨映射仍由原真实验证完成，合法hash不证明实际媒体可用。这些条件补足原CPSC-I01的连接歧义，不表示合法本地制作已执行。

真实实施职责：Backend唯一schema/canonical方法/parser与资产/current/rights衔接；application/media_registration.py的host/typed/final-context归Backend。Media planner经该方法取得键，workflows/current_engine_production.py及Flow/driver/Bundle只消费已解析绑定，不写第二算法或跨写Backend。原角色后续固定源码审查仍需确认strict duplicate JSON/定义、usage/引用验证和current拒绝真正到达；后续测试另准入，不在本窗口授执行。

最低后继覆盖依合同第33行保持：同Asset不同usage、多shot合法；duplicate/错误ID/悬空/错usage拒绝；同键事实漂移与跨Run权限拒绝；恢复不重新分配或收费。没有执行这组案例，也没有计算/运行任何候选连接函数。0产品/候选/Python/Pydantic/SQL/native/网络/模型费用/安装/测试；原19三失败、三binding、31/105与20元记录不重开，真实ASR、四masters、完整Bundle、安装发行、R1独验后连续R2仍待各原角色。

末源/metadata读取f9e7f5实际自然0无live句柄。最终封存工具以本人实际返回与交接消息记录，不从文件存在预测成功；全部输入读者在自然返回后释放。
