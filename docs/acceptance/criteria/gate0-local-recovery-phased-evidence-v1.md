# gate0-local-recovery-phased-evidence-v1

实际版本化候选标准；永久测试owner。ADR0011方向已批准，RV14对本标准/拟case/fixture固定hash的独立批准尚待。未运行产品、冻结B7/W7 WIP或关闭RV11-P01，不签Gate0/R1/R2。

范围：新隔离实例首Run，gate0-local-render-v1，原授权音频、10秒9:16三镜头、无feedback/approve；kill固定shot1 finish_output真实成功后且observe未落账。数值不泛化其他driver/窗口。

| 阶段 | 必需实际判据 |
| --- | --- |
| K | 原1Op submitting/unsettled、1allocation、ready完整文件无partial；input/binding/资源固定。原renderer shot1生成一次。先持久PID/Creation/树及file/hash/size/mtime，再真实自有树kill、真实墙钟越lease。 |
| R | 包装真实finish_reconciliation，先原方法实际成功返回再有界只读闩；正常调度前原1Op/1allocation唯一、原allocation_fence不变、原Op完整真实decoder后成功settled0元/confirmed_no_charge/完整manifest，原文件保持。R新增render/allocation/Asset/Step均0，已有input/plan/shot1不是总量0。queued/workerNULL/lease0/idle槽来自真实后端。 |
| N | 新normalfence严格大于Rfence，同Run/binding/FlowUUID继续quality waiting_user且workerNULL/lease0。5Step=plan+三shot+compose；4settled0元Op=各shot/compose1；5allocation=三shot各video1+compose(video,mixed)2。真实Asset/Step/媒体/Flow关联和独立解码。 |

真实原renderer调用记录与decoder/版本调用分开：K shot1实际一次，R所有render增量0，N原shot1增量0而shot2/shot3/compose各一次。wrapper先后记录真正原调用，不替结果、不mock视频、不代执行恢复。仅Operation数/文件hash相同不够证明不重render。

原Op/dedupe/allocation一直唯一，id/run/step/input/route/created identity/原allocation_fence保持；R成功manifest在N不覆盖，文件path/hash/size/mtime一致。N允许staging ready→imported/asset_id和Step正常新fence，不误将合法可变字段固定。5输出Asset加1原输入；每Step关联对应输出，真实probe核720×1280/v+a、单镜4/3/3秒、compose视频及混音各10秒。

原03966测试及T13三夹具/观察红、补观察绿和真实kill产品红完全保留。原47行最终全表1/1移至R；N允许正常完整4/5且原目标唯一，原48行quality目标保持。此是字面计数阶段的版本变更，新绿不能称旧字面所有断言原样通过。逐旧断言映射、固定hash和所有数值见同名JSON。

拟case：tests/gate0/test_t14_recovery_phased.py；判据：t14_phased_assertions.py；新PhasedTrace/PhasedWorker包装真实finish返回和真实renderer原调用。T14PhasedFixtureVersions.json固定所有拟执行文件。先RV14实际核固定标准/拟case，再最终B7/W7停写/精确源资源beforehash与统筹准launch，才运行。每个观察即时JSON fsync/rename，真非空HTTP兄弟及创建身份保护，实际自有树/端口终态；普通副本/argv/raw/JUnit分层留存。

运行界限明确版本化：旧12秒观察和原红不改；拟Worker每次70秒、N等quality55秒、K/R闩各30秒、真实lease等待40秒、natural wait85秒。免费实验有界窗口不是生产性能SLA；CLI0不代业务恢复。

回滚：RV14不批准则原候选保留不执行，显式修订并新hash重新评审；源漂移/夹具失配保原raw/退出并停止交owner，不擦unknown、SQL补业务、降阈值或覆盖旧红。测试角色不回滚生产数据。partial/多输出/缺损/fence/cancel/幂等/公平性/另一Step-Flow窗口各有后续独立批，不能由本case绿外推。模型自主作品、完整Bundle/RAG、Portal/MCP、三OS安装、R1独立验收→R2保持原要求。


## 候选修订2：RV13两项测试证据缺口

候选1已按原字节归档，criteria JSON4e6c10f8/MD b732ecfe、manifest1b752948和原9文件保持历史；RV13报告3928fb12决定NOT_APPROVED_FOR_EXECUTION。当前是同v1规范的候选修订2、新固定hash，待RV14重新独立批准，不称已关闭P01/P02或产品通过。

R必须把真正原probe的规范输入path、实际hash/size/mtime、target Run/PID和唯一调用ID前后关联到K唯一attempt/staging完整文件及manifest。before/after一致、真实decode_requested、返回decoded video/mp4/4秒/720×1280/v+a；manifest MIME/source/rights/staging一致。错文件即便同字节/规格、文件变化、失败probe都不能满足。ProbeTrace只被动hash/stat且不读受限staging外文件，原probe恰调用一次、不额外运行FFmpeg，原异常重抛。

N逐项贯通有序Operation.generated_files→allocation attempt/staging/output_key/input→imported staging.asset_id→Asset owner/hash/size/MIME/source/rights→Step有序asset_ids与result manifest，五个输出Asset不能共享或用孤立记录凑数。Flow逐checkpoint核实际run/binding SHA/derived UUID/plan revision和真实Plan Step，shot有序prefix、compose video/mixed refs、quality refs及waiting revision逐项匹配。shot2/3同为3秒也不能交换或共用来满足判据；错Flow run/binding/顺序也拒绝。

自有纯关联sanity已有限执行4 tests/actual0；使用synthetic字典、非视频纯文本字节、fake callable，只证明判据能拒该类关联反例，未import产品、SQL业务、真实decoder/CLI/Worker。它不是产品红绿或标准批准。原R0增量、K真kill/墙钟、N完整生成/newfence/70秒与55秒窗口、原T13红及其他反向要求均未降。
