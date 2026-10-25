# RV30 — W15 两原上下文方法与 T25 独立结果复审

结论：**SOURCE_REVIEW_FINAL_LIMITED_METHOD_UNIT_SUPPORT**。可支持 W15 两方法的固定源码、原完整 validator 保护及限定真实方法 unit 行为；新显式 None 单例与独立 XML parent 映射机制有窄范围通过证据。**原10组仍 NOTPASS，不能改称全绿。** 本轮未新增该限定切片的生产阻断 finding；实际 Backend journal/恢复、安装资源、ASR精度/资格等仍未测。本结论不批准 RuntimeBinding、真实ASR/P95、68、三OS、Gate或R1/R2。

## 固定输入与身份

T25 普通根：`G:/开发测试/Codex/VideoCreatorImplementation/TestDevelopment/ReviewHandoff/T25OriginalAsrContext/`。自身过程：`G:/开发测试/Codex/VideoCreatorImplementation/Review/OriginalAsrContext-RV30/`。

- 当前 AGENTS `6de878f514b02788f8af5ba512f71c56bb053f6800d76cf19f3cdd955b7f6a0d`；RV30卡 `9a96646653a8b0be362b80172402d60909c850343bd7c95d60271ad99fd39e89` 已全文读。
- T25Handoff MD `35bad9c8c54f4db0c70245b95ad1a96b5512c960e181909847fe66a9238ce704`，JSON `b428d484b352e6510b2c2312e74b0bcf67ce82b2752b99a2a00e4ac6fa413785`；Terminal `26650d89f9f8d5605951b04b440c0c9e91286ae98b7417fde26fbfedc64b0177`；FinalSnapshot `442a4b559eeb2e4b829b1aece50ffffb085074142fd492120392a60dc3a3f3b3`；OrdinaryManifest `864f888c3389025dd60f22a1c3ea61339be62724a4ab22073311fbdb6f1491d5`。
- 实际153普通源码/raw/fixture副本及999原解释器prelaunch归档逐文件核SHA/大小。含正式文件和W15接口/保护源补充，共1160 pins，匹配、前后变化0；不读取实际执行路径中的当前生产/WIP以倒填历史。
- W15接口 `ffef6eeabde1ae4e7b68f59f3246704f66b388241dd1af339ed142588b0af5bf`；provider `ad9dbd7c6037a6dcd4bf075b71371e733e103cd7b1114b13e419e08d0443b058`，旧完整provider `25a5bb707e9f3e42b3c525735d652fba19fe61a51349c6581a4fddb4edc2d04c`，worker `7811c33e6947a1091d1a03ed03cb5fff1b9767135ed141a7851788f119ac53c3`，真实 errors 全文均固定。loader `ecb693dc7adb98426d62138ebfdee20b20feea230a4838fc74c7c788ae31be74` 用同SHA历史普通 `AgentMedia/IndexedAsrLaunch-W16/BeforeCopies/asr_resources.py` 核身份，只作 W15 保护源，不审W16方案；它未被T25实际加载/安装验证。

完整路径/hash与必要正文、原证据见自有 RV30InputPins/Snapshot/FactsCheck/SourceAfter。

## 真实源码、保护与方法作用

以下行号均为普通 `FixedSources/local_asr.py`。

1. 418–426 `_original_context_bytes` 使用当前 provider/worker实际文件hash和原request，冻结 UTF8排序紧凑canonical bytes。463–493 真正 LocalAsrDriver constructor 构造原八字段及存在时三项manifest事实，随后冻结；不从result补期待值。
2. 495–500 `validation_context_bytes` 重算当前request/provider/worker并比较原bytes，变化拒绝 asr_original_context_changed，返回冻结bytes。511行在原route/audio检查后调用；本次未执行 __call__ 或推理。
3. 429–459 `validate_original_asr_result(result, bytes)` 限严格bytes/2MiB/UTF8、duplicate/非有限JSON、精确四key/version、64hex来源SHA语法、canonical及request field-set，随后直接调用原完整 `validate_asr_result`。返回None是符合该原数据约束，不是bool准入。
4. 独立文本提取旧25a5与ad9的 `_rational_us`（163–166）、`_time_base`（169–174）、完整`validate_asr_result`（177–270），三项正文逐字相同；结果/文本、半开时码与word顺序、实际样本/PTS精确有理数、音视频origin/offset、模型/runtime/configuration仍是原验证逻辑，未用抽取的假方法或宽松替身。

T25 `TestBodies/ProbeT25.py:28–33,53–104` 实际复制完整provider/worker到自身 SourceLayout，并用 importlib 执行完整provider和真实EngineError源码；只用空父包隔离无关Engine依赖。29–32没有AST抽取方法；profile计数和拒绝run_local_asr/__call__实际边界在41–50。真正constructor执行，但音频是静音WAV、模型是明确DUMMY非权重文件、manifest是明确未准入fixture、结果是结构JSON；这些均不证明实际decoder/ASR/资源或精度。

## 原10红、新None与XML分别成立

| 证据层 | 原MethodRoundOne | 新NoneContextRoundOne |
|---|---|---|
| 原工具/包装 | 542549/session53508 →03a28e，自然1 | 327cf4/session7516 →389d87，自然0 |
| 实际子PID / CreationFileTime | 53356 /134359613343226706，自然1 | 25436 /134359618053928482，自然0 |
| 外层PID /实退出 | 6912 /1 | 49148 /0 |
| unittest | 10项、1fail、0error/skip；原stderr0.675s | 仅1项、0fail/error/skip；stderr0.083s |
| profile事件实求和 | context55 / standalone66 / full50 | context0 / standalone1 / full0 |
| 实际强制/终态 | forced=false / terminal=true | forced=false / terminal=true |
| 固定源/运行record数 | 1005 | 1005 |
| before/after实际观察路径map | 3014 /3014，原字节SHA相同 | 3013 /3013，原字节SHA相同 |

1005是源/运行record维度，观察map含original/copy/execution_original及测试源路径。不能把其与path数混同；统筹先前3009摘要是不同/不完整计数视图，不能说明完整观察路径，也不构成源变化。原InputBefore/After及receipt保留：原 `5dfb6ae218f6fc9dd93a543132f3e61b16ad144de7a47a29679202ce9fbdd0ae`；新 `55e9dad3b9afaba4d95d3955c86f458de2ecf6fa57af94e93956962abf052d3b`，各批前后相同。

原 `ProbeT25.py:150–151` 的context=None会自动调用driver accessor取得有效context，194–217的case0本想传None，实际未把None传给standalone。原stderr准确报该subTest“预期异常未抛”；它是Test helper故障，不是provider接受None。原10其余group的raw状态可分项引用，整批继续NOTPASS。

原XML SHA `aba97f68c7f0d95d2b271c79f8b15d8384aa5787a96b6259ce86a1710eb43837`：suite failures=1，但实际failure child=0。源316–323用subTest完整ID索引，不能对应parent testcase。真实raw已提供失败信息，历史XML没有被重写green。

新 `ProbeT25NoneContext.py` SHA `48fba8c57378d7c0dced3efcc7b750c6f137d77fe221c92628467e7a0167d61c`，17/151–168用独立sentinel区分省略与显式None，321只运行唯一None用例；实际standalone1、full0、default accessor0，确认在原bytes门拒绝。新JUnit `d5e506c38dbd334c7d8140f86a3f0106bbaf8ba3be5cfc8dce49cb3d3588efea` 只支持该case。

新325–354把subTest归到 `.test_case.id()`，另透明故意失败的unittest/XML自探针实际1test/1failure且有parent下failure child；ExpectedRed XML `96d81145e35dce7afaf9a4e974e9df5d58ac3a3e91dc1ffaeb1d1dfe671223f5` 与其raw失败文本一致。该expected-red是XML机制证据，既不是provider红，也不能派生修改原XML。新helper/runner/index为新身份；原Probe `4f5f87ee153c3dd6f56715f21e13ae8e1b33af17423db98872767dd2b6dbeb06`、原index `1b89ac5bc82497907e7b88296af952276dcc9e9c573450e2fb1d44e1546f8cb0` 与新index `085f034002dcbce170796c737b88257225f8f35630cfa2be8a661290eb3c9b79` 分开保留。未重跑其余9或完整矩阵，不给新源中未执行的其余methods授通过。

## 来源SHA与Backend责任

原实际 `test_source_hash_syntax_is_not_journal_commitment_authority` 将context的provider/worker SHA替换为格式正确f/e64hex，standalone返回None；driver accessor仍保持其原context。这与源446–447只检查语法一致，并明确证明**wellformed SHA不等真实原commitment/安装授权**。不是同一真实Operation已被核实成功。

Backend必须在调用standalone前从原账本核原context bytes与commitment、Op/run/step/input/dedupe/route/current允许核实fence、资源/config/audio/当前准入安装、完成文件SHA/size；不能从result、新driver或调用者格式正确hash重建旧期望。缺原context的历史unknown保持unknown，不补假commitment、不重跑ASR。上述真实journal/dispatch尚未在T25运行；W15文档当时503只是旧源阶段状态，不能推定未来Backend永久503。本轮不读B19活源或代签其接线。

## 真实执行范围、失败保留与交接

两批实际解释器为固定Integration便携CPython3.13.16，实参 `-I -S -B -X utf8 <对应Probe> --output <自有Cases>`；env只固定系统位置、该解释器/System32 PATH、任务TEMP/TMP/PYTHONUTF8。它不是正式root.venv或完整已准生产加载闭包。Python unit child与PowerShell外层原exit已分别核，不吞原1。

`RunT25NoneContext.py:78–107` 持有原Popen/handle并以90s等待，超时方案是核创建身份、最多一次terminate、仍持原handle轮询实际终态，强制结果永久red。实际两批没有进入该分支；准备revision2的AST/文本检查不是超时/强杀实测，不授此机制OS资格。原准备revision1、runner修订、候选hash和read定位无匹配退出均只历史过程，不当provider/runtime红。

有限unit支持范围已固定，没有新的生产修复请求。Test仍负责保原helper/XML失败与今后单独获准完整矩阵；Backend负责真实journal/安装/dispatch，Integration/Media负责真实资源/启动/ASR。MM03/MM05独立authority、实际转写/音视频听审、恢复、完整68、三OS及商业R2仍待独立证据，不因这些unit提前通过。

本轮自身未运行产品/测试/ASR/native/网络、未读key、费用0、实现/期望/阈值/标准修改0。全部工具与input reader终态、live[]、已释放；正式SOURCE_REVIEW_FINAL。完整R1独立验收后连续R2不缩，W16/W17监督与I28全loader另卡。
