# RV55：F7 恢复源码与 T38/F6 UI 机制证据独立评审

结论：**FINAL_LIMITED_REVIEW；F7 存在 RV55-P01（P2，OPEN_SOURCE_STATIC）；T38 支持固定 F6 的 19 项有限 UI 机制通过。** 两份结论版本分开，F6 绿不能授 F7 恢复通过。未运行产品、数据库、API、UI或测试；不授 RuntimeBinding、真实宿主持久性/跨窗口原子性、作品/ASR/三OS或 Gate/R1/R2。

## 固定身份

F7正式MD a5f0cf744ffdb89fb48faf66b99985e800fa97adfbe0a1409dc49cff3fd42430；JSON 9f3ed24db52cbc5e30fe926b91187cfbf86cbf0ebfbeadda65f06064ec244f9e；Snapshot 41115d97e9e402e93a37e611b1c2bae5490a35c26e0b45449b15f7a1996218ea；Delta 710697ed82314fea061f9d3b749d46eca6cc0d59685cddf09bd4201566ff27f0。

T38正式MD 11d506c6d4c70ecb184e4a17a97f211adf744620298b5d9285bbb136043f0008；JSON 1919af8cb62498034b5faf956d356a103784cbed53eea18b26206a8de999e68b；59普通副本manifest 3f3000ee002d943044cf6b8b8b34a3aafdae72a18f9dffbb41dc9bb135a39401。

本次83个去重固定路径：F7十一普通源、T38五十九有限普通副本、正式卡/规则/接口及I33三SDK普通源。全部大小/hash匹配，结束83项无变化；具体原路径/完整SHA见自身 RV55Snapshot.json 和 RV55SourceAfter.json。未读取当前生产源、F7活验证、T39/I43/F8，也未重复制/重核8712份环境；T38原索引只作为固定 artifact。身份核十一源不代表逐行审查全工作台，语义审查限相关恢复、编辑、列表、事件、持久化与传输链。

## RV55-P01 — 列表 effect 将恢复定位重切回当前编辑项目（P2，Frontend）

固定普通源：[Workbench.tsx](G:/开发测试/Codex/VideoCreatorImplementation/Frontend/ProductionRecovery-F7/OrdinarySources/Workbench.tsx:122)，SHA d58ed8ec5bdf0aaa258c9f3fd6a8cbcf7a1d9ddd6d41de85bcbf590971016c95。主位置122–127；相关85–87、108–115、190–242、316、327。

最小静态触发：同一实例保存原项目A的unknown意图，当前编辑器是B（或新草稿null）。recoverProduction 198–209验证原body/key/instance/project，保存完整匹配ACK后，214选择A任务，215保留当前编辑器并转任务中心。225–227刷新列表；当响应实际改变productions.data引用（例如A首次出现/状态变化），122–127的既有effect按**当前editor.project B**筛选，自动把productionId改成B候选；B无任务或null项目时改成null。

85–87详情/修订query和Run订阅因此离开A；316“刷新任务”也跟改写后的ID走。223给A写入最新详情缓存不会反向恢复productionId。239–240仍声称保留原回执/定位，327又在B表单dirty/保存中时禁用任务行，不能马上用A任务行绕回。108–115只在instanceId变化时把A locator记到A项目的storage键，不解决当前编辑项目B选择。这是源码确定的状态覆盖链；实际effect调度/界面/请求影响尚未UI实测，不能记actualHTTP红。localStorage中的原body/key/receipt并未删除，也不是后端账本丢失或数据损坏。

修改条件：把明确恢复的production/project/instance定位与当前编辑项目分开保存，列表自动刷新不能悄悄替换它；最新GET、Run订阅及错误重读保持同一个原A身份。后续明确用户导航可按一致上下文改变选择，但不能通过载入A覆盖脏B表单来修，不能放宽unknown原body/key或跨实例边界。

独立Test最小后继：A首次回执含原Run，GET返回后续Run；B已有不同任务且dirty，刷新列表返回新增A/状态变化。核原POST完整body/key不变、恢复/GET/事件/错误重读始终A、新旧Run分开、B输入不变；再核B无任务/null项目、GET失败后列表变化、已保存receipt重开只能GET，以及实例切换不把迟到A完成写到B。测试属于Test，Review本轮未写/运行。

## F7 其余相干机制支持范围

190–242只使用原保存意图，verifySubmissionIntent 67–70重算原JSON哈希；不flush当前表单、不构造新body/key。已有receiptId分支204–210不POST；33–39验证ACK实例/项目、IDs、版本/status/非空路径并通过saveSubmissionIntent原key记录保留定位，成功保存才213解除unknown。这里保存的是经过完整校验的receiptId定位，不能冒称保存了后端完整不可变回执所有字段。

218–224显式GET原production_id，核实例/项目/IDs/status后填当前详情；首受理Run/status没有注入当前进度。恢复失败catch不clearSubmissionIntent；包括not_sent、后来拒绝、409/408/5xx、无Envelope、网络、不完整ACK和存储失败均不能洗掉原unknown。GET/刷新失败在本地保留已知回执；但当前展示/重读定位受到P01影响，不能以这几行证明完整闭环。

B28原受理权限/事务/原Run/latest区分只消费已正式接口与RV54有限源码结论，本轮无SQLite/API/并发实证。F7 noEmit/build/UI未测；现有I33生成description未重导；单窗口storage源码也不证明跨窗口原子性或native可信持久性。

## T38：原字节核实的 F6-only 机制范围

固定F6 Workbench SHA af1f408ffd050f4c669fae93e38985e90e1afc6506669fc6fa94fbddd00fb61f，与F7不同。Harness/Entry 4–20挂实际F6 Workbench/ReactDOM/Query/I33 SDK，显式TEST bootstrap，HTTP返回由本次loopback浏览器route夹具控制；不冒真实Owner/native握手/Backend。RunT38 70–77 alias指固定F6及新唯一ViteCache，84–86恰一次公开Entry warmup，随后真正首abort例；没有旧用例预演、reload或反复热身求绿，原因也不能据此推定原useState-null根因。

独立解析 Result/JUnit/1386条原Events：19个case_started、19个case_terminal与19个JUnit节点逐名顺序一致，19 passed、0 failure/error/skip/not-executed，runner errors空。首production_unknown_abort实际观察1次POST；九种unknown响应各1次原POST后阻止修改身份；明确拒绝控制2次不同key/目标，缺连接控制在重连后才1POST，staging失败0 import。

import正向与反向实录：普通重试/重选保护/实际卸载重开各2次import；项目A→B→A共3次，首次与第二/第三完整serialized body/key/instance相同，project/staging/ZIP SHA/origin全部字段一致且staging始终1次；跨实例往返2次import均原实例，B不派发；unknown→后来拒绝→再重试3次仍同身份。这准确落实RV53两个语义原则：精确恢复按钮映射，以及同实例B视图显式恢复A允许；没有删回A或跨实例反向检查。原T37十九/十四NOTPASS不改、不回填，新增localStorage不可用/损坏哈希故障不在这19项动态覆盖内。

原Events保留27条console error：ERR_CONNECTION_RESET 10、502 3、503 8、408 1、409 1、422 4；均为受控网络fault文字，pageerror/Vite error均0。不能写“console无错误”。完整消息、每例请求原字段及逐名结果见 RV55T38FactsCheck.json；没有从汇总绿色抹掉raw。

原时间层次：Result起止09:14:53.117Z至09:15:24.443Z，区间31.326秒；19例duration总和27.874秒，非包装墙钟。原session49718→7043c1自然tool0，Node实际0，Browser原close event0且同creation观察HasExited=true；forced=false，stdout/stderr双EOF。原保留PID/creation为Node41044/09:14:51.1754270Z与Browser22688/09:14:53.8489841Z。Vite.close记录true，59488/59494 loopback关闭探针记录true（源码portClosed以socket error返回true，未记录具体errno，不能再声称独立核出了ECONNREFUSED代码或全后代退出）。这只支持本次保留进程与有限清理证据，不授真实desktop Job/host生命周期。

InputBefore/After均8712 records、528 links、changes[]是原runner实录；本Review不重扫这套环境，只核普通证据身份。COMMANDS旧字节保留的追加、透明夹具与清理记录，不替代实际SQLite、合法Bundle/音视频/ASR精度、跨窗口或三OS验证。

## 工具与责任

Review仅使用自有stdlib读取/hash/JSON/XML解析既有artifact；没有import/call产品或测试。自有解析首次4b3537因SDK source字段实际是dict触发AttributeError；纠正命令7ca17e又产生PowerShell ParserError，未执行。原分析器与错误记录保留，完整纠正fc8be2自然0、原证据解析152854自然0；这些是Review工具错误，不产品/测试红。所有固定源reader已结束，费用/密钥/网络/产品/测试/DB/API/ASR/native执行均0。完整R1独立验收后连续R2保持，真实媒体与平台条件不缩。
