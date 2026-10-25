# RV57：F10 跨实例编辑状态与取消身份独立源码评审

结论：**RV56-P01、RV56-P02 可按各自原触发链 CLOSED_SOURCE_STATIC；本片未发现新的阻断源码Finding。** 本轮没有运行React/UI/API/DB或测试，两项动态关闭仍须独立当前版本验证。F10 source-only、原三区字节相同及T38/F6绿都不能授完整恢复、宿主/并发/三OS/Gate/R1/R2。

## 固定身份

F10 Handoff MD aa1d8a4e987e8d6ab037770293070feaea00766499da76c99fb48fb68ba54451；JSON 03bbdada4d9b3723b669090e51879edcc60a754d8558de577e770c139dd25e08；Snapshot 480e257504d689ad78a19d20cabb7a652e8245504c28c0b60b83b8ff1cf2cfd4；Delta 09ed42c5aaa2c45e863011882a54391f847144adf05d3dddb83b5df0a8a9647f。

本Review39固定路径＝F10六正式文档、规则/卡2、原九公开/历史ordinary输入、F10十一普通源及F9十一普通源；全部hash/大小匹配，after39无漂移。不是owner此前31pins的重计数，也未去读生产原路径/复制环境；本批增加F9完整普通源码作为字节基线。完整路径及SHA见RV57Snapshot/SourceAfter，完整两文件diff与原方法对照保存自身目录。

实际仅两处变更：useProjectEditor.ts b1c085fcce215a2e90b035f6df45091bc5276661ffdb1991c6856e9f8ef8f573（F9原6ef1cf47a7bb881795aed17621e47896096bd2a5be120b41eb994e2aca0d9ad8）；Workbench.tsx 6cc07b96c542668dbf3378efd88dcf8d3f0e64d7148fb21cf582cb6a5bad9b39（F9原6a2abf795ce6a92e708b4dac7c9234633c86d56254a1871670b63d0d04678980）。其余九份普通源保持。I33 OpenAPI/SDK只读历史ordinary，未读取I44活源或当前SDK；其相干性需后继另核。

## RV56-P01：helper内部在写入前守卫，原迟到覆盖链关闭

固定 [useProjectEditor.ts](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/InstanceActionIdentity-F10/OrdinarySources/useProjectEditor.ts:30)。24–36：实例/连接变化替换context对象并递增generation；isCurrent使用对象身份及mounted，commit在任何stateRef写入前核当前对象和状态实例，排队state updater也重核。39–64挂载/卸载与实例/断连layout维护上下文，不再把守卫放在已写表单的调用方await之后。

77–97：每次load建立新context，回包86先核仍当前，87核project_id；88才统一提交project/form/edited/phase/error/ref和createIntent。90写项目locator及92导航callback前再核。旧成功/失败返回不提交新上下文，95仅对有效context提交错误。Workbench182–185把成功导航作为helper有效上下文内的onLoaded回调。原A请求→切B→A迟到，不再由旧A将B表单/dirty清除；A→B→A同样不能用相同instance字符串使旧对象复活。只读任务/返回当前创作175–181调用cancelLoad，使待载入项目失效，不主动load或保存编辑B。

108–145：save按context复用同一promise，保存发起时project/revision/表单快照及createIntent body/key；回包126先核，再核已有project_id，128才写当前项目。locator、列表刷新和返回均重核；136错误和139–143 finally只处理原有效context和同一promise，不清新保存ref/serial。已发送请求可能在后台完成，以上不是服务器回滚。155–166 flush在循环与await后都核原context，失效不能接着使用另一个实例/导航的保存结果。148–153自动保存timer也绑定其context。

171–186 cancelLoad/newDraft替换context；旧load反序到达不覆盖新草稿/后导航。更新输入167–170走同一个commit。46–64 Map按实例保存/恢复内存草稿，loading/saving中断转idle并阻自动保存；初始离线草稿首次连接可转给首实例。其范围仅当前组件生命周期，不能冒跨刷新/应用重启持久性；恢复旧实例的未知保存是否实际已受理需后端原key事实。这里关闭的是原本地迟到写入漏洞，不授所有保存/重放服务语义。

## RV56-P02：确认目标与世代固定，原改按B取消链关闭

固定 [Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/InstanceActionIdentity-F10/OrdinarySources/Workbench.tsx:324)。83–87根据实例、连接、定位project/production变化替换CancelContext对象；110–112要求打开时context仍是同一对象、mounted/connected及三目标身份一致。114–123卸载/失效关闭旧intent并释放失效操作自己的busy。A→B→A即使编号相同也得到不同对象，因此旧确认不复活。

324–327打开时从已核selectedProduction复制instance/project/production，保存项目显示名和当时context；412显示原项目/任务，并按cancelValid禁确认。329–335确认只取intent.target.production_id，不再从后来自动补选B构造path；相干源先守卫连接/世代和当前已核详情。

336核回包三身份；337/339才写原目标缓存/刷新，341关闭只处理该intent；342旧错误不进入新UI，343 finally要求原context有效且cancelOperation仍是同一个intent，不清后来新操作。context失效时120–121只释放仍登记的失效取消；不能从旧finally洗掉新操作标记。这支持原A确认在切B/断连/目标变动后不可发送给B，且已发送A的迟到结果不写新上下文。没有执行一次真实取消，也未声称后端已停任务或完整后代结束。

## F9恢复、原body/key及最新Run保护

57–59/154–166仍保独立三身份locator与背景列表补空规则，原RV55-P01修正保持。97–107详情回包与消费核三身份，事件取最新GET的run_id并再次过滤production/run；跨项目提示与任务行只看任务仍不载入B表单。chooseProduction/returnToEditor对待载入项目新增cancelLoad，未在无pending load时修改保存任务。

独立提取F9/F10完整三段均byte相等：receipt SHA d73cd616f6975db8e7702e120260c464d5a5165a27e695aa666991de1c6af496；create SHA cc3978cdf929933225a09070f9b5cf904dbb049cfb13d728f3b57d072f8fd3a4；recover SHA 15641e702efef038ad4a836960660dfcd6c59b15b16fa86b17e031dcc51316a5。调用现在消费受guard的flush/选中locator，完整匹配ACK保存receiptId定位后才解除unknown，已知receipt只GET，后来拒绝/存储失败不洗原unknown，原受理Run/status不冒当前进度。这里仍只保存经校验定位，不冒完整后端回执全部字段。

本片未将其它继承的工作台动作扩成“全动作跨实例合格”，也不按普通React unmount凭空构造原组件写入新组件state的路径。layout世代、草稿恢复、busy与真实React调度尚须独立实测；源码上下文对象不是native授权/后端权限凭据。

## 必要独立动态后继

Test应使用正式当前版本React链核：load/save的成功、错误与finally延迟，实例A→B及A→B→A，B编辑后旧A到达；同实例连续项目导航/新草稿/离开pending load逆序；保存中继续编辑与flush不改原body/key，旧完成不清新ref/phase/dirty，组件内实例草稿恢复保持输入且中断禁止自动保存。记录实际请求，不能从UI守卫推已发送请求撤销。

取消需核：打开A→切B/断连/目标换B→回A旧确认仍失效，B取消POST为0；正常重新打开A只向原A发一次；已发送A后上下文变化，再开始新合法操作，旧成功/错误/finally不得写新缓存、notice或清新busy。恢复还需B dirty＋列表变化、ACK保存失败/GET失败/已知receipt只GET、最新反馈Run事件与原受理Run分离。只列验证条件，Review没有写/运行测试或批准未固定runner/RuntimeBinding。

## 原失败与工具终态

完整F10Handoff JSON已stdlib全文消费并保存Parsed副本。owner误探旧MD/接口/索引、同文件delete+add拒patch、元数据array(...)错误皆保；正确读取/修正有独立记录。这些不是产品/编译/API失败，未借owner同步hash绿作动态通过。本Reviewa84d73（原cell1）、471add、b2e399、60e563均真实自然0，只有自有stdlib读取/hash/JSON/字节diff，无产品或测试import/call。

39 inputs结束无漂移、源readers全释放；费用/密钥/网络/Node/产品/UI/DB/测试/ASR/部署执行0，未读活T41/I44。完整真实媒体/ASR/权源/宿主与三OS仍待，目标完整R1独立验收后连续R2保持。
