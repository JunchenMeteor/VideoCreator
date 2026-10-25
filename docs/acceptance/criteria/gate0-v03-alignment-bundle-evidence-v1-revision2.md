# T17：0.3标准修订2与RV18-P01准入整改候选

新文件revision2；原RV18已准criterion1/58计划全部字段顺序/原6断言及原红绿字节保留，不覆盖原文件。仍not_ready_for_execution，未读/import/启动B11活跃生产，不绑定未发布0.3签名，无生产freeze/fee/key/install/network。整改最多三轮，本轮是第1轮，P2关闭归RV19。

## 导入前实际身份检查

旧guard/adapter12份相关材料在T17OriginalInputs普通字节存档，原T16的27副本/6sanity及0.2旧基线不动。新版使用独立hash固定的BootstrapBinding：source/resource必需闭包非空且与admission声明全集相等，目标及每层package路径规范匹配，每个源和完整对应prelaunch正文与所有资源逐项核hash；不能用completed=true或admission自列小集合代替。ServiceAdapter不接已构造service，先preflight，再核已审批Test bootstrap函数来源/目标解析、拒先前producer import，之后才import真实模块和构造服务。当前没有完整最终绑定和fixture bootstrap，不能据此调用真实服务。

新own文件/loader sentinel验证缺target/empty source-resource/坏targetpath/hash/缺正文或资源时拒绝先于callback；合法own identity只进入sentinel一次，无Fake service或生产模块。它仅说明共享identity算法顺序，不证明完整实际0.3闭包、PathFinder真正加载、真实service构造或OS安全边界。六consumer完整签名、registry/Allocation/producer/bootstrap/MCP host仍pending，不用未来B11接口倒证旧B9。

## ADR0017参考增量

per-work参考是独立kind precision_reference_v03/role precision_reference/PerWorkReferenceDocument，不能把同scope当同grammar或给precision_report_v03加union。report_id作为引用ID不变成测量身份；完整实际音轨/Transcript单位及listener/arbitration正文、issuer权限和当前撤销均要核，hash/HMAC不制造独立性。

三个值分开：签名输入移除signature/content_sha256的canonical全文；内部content_sha256除自身保留signature；readyReceipt对完整实际文件byte算SHA，EvidenceReportRef/Manifest取后者。秘密不进材料/导出，HMAC非公开可验证签名，issuer只在获准scope/criterion/来源内签参考，不获得方法/authority/policy注册权。所有真实字段参与，来源→reference→Alignment→measurement→WorkValidation/Quality/Manifest无环，不以futureSHA/占位修改解决。

| 增量case | 真实判据 | 状态 |
| --- | --- | --- |
| REF-01 | 版本/role/kind三元组严格分派precision_reference_v03独立PerWorkReferenceDocument，precision_report_v03无reference union；旧0.2 audit_summary原grammar/默认/hash保持 | planned/not_run |
| REF-02 | 真实受评原音轨在本run/request准备索引中唯一定位/hash/完整decode/samplePTS，不只接受调用方SHA或mix/脚本；有序units与固定Transcript全量ID，原boundaries每条strict ID/范围/数量/集合先核再map | planned/not_run |
| REF-03 | independent_listener_refs必须定位可得不变正文、真实人员/标注工具与独立性；arbitration_ref含真实争议裁决或无争议完整人口审核，单SHA/不存在placeholder拒 | planned/not_run |
| REF-04 | issuer/authority获准对应scope/criterion/audio-work/listener范围并在registry当前有效未撤销；签reference不授policy/benchmark/资格安装，普通payload/万能sign callback拒 | planned/not_run |
| REF-05 | HMAC签名输入canonical除signature/content_sha256；内部content hash除自身保signature；ready Receipt完整实际JSON字节SHA独立；不能混三个hash或排除units/audio/listener/issuer以解环 | planned/not_run |
| REF-06 | 有效HMAC仅认证issuer声明，不证明独立听审或ground truth；复制被评ASR/Alignment边界再自签不能准入，未配真实资源/可信根仍pending | planned/not_run |
| REF-07 | 来源完成→reference正文/签名/readyReceipt→fileSHA reference_ref→无futureSHA测量locator→Alignment→真实measurement→WorkValidation/Quality→Manifest无环，listener不反引future参考hash | planned/not_run |
| REF-08 | 默认完整测量/投影证据要求reference+measurement+必要listener/arbitration正文及许可闭包，缺授权不删后称完整；合法媒体文本projection另保父包/取得限制，benchmark provenance_reference不替本片参考 | planned/not_run |
| REF-09 | import版本/kind/hash/fullunits/时基/闭包严格保origin原byte/ID/hash，HMAC无本地同issuer/key只能来源声明；origin_snapshot_only即使能核签也需本地registry证据/范围/revoke，导入不安装root/key/authority或授新制作 | planned/not_run |
| REF-10 | qualified runtime无本片参考仍not_measured、reference/N/P95/measurementlocator全null且无reference/reportplaceholder；strict缺参考alignment_required/waiting_user，不换策略或拿benchmark顶替；max/N/200ms/MM05不变 | planned/not_run |

合法无参考qualified路径不改：not_measured且ref/N/P95/locator全null，无参考或报告占位；strict缺真实参考等待。完整测量导出需实际参考/报告/必要listener裁决正文与许可闭包，缺权拒其完整证明；另允许明确受限媒体文本projection，不冒完整证明。origin原byte/IDs/hash保持，origin_snapshot_only，不从包安装issuer/key/root/资格；即使本地能核HMAC仍要registry独立核当前范围/证据/revoke，新制作能力另准。

原max起终/N/完整集合/nearest-rank/200000us/MM05及旧58不降；真实听审/参考/资格和MM05语料pending，synthetic声明不能做positive。新reference纯hash断言不验HMAC或authority。自己纯检查原6加9共15，初轮15pass，再仅把reference IDs类型检查放set之前并补非hashable ID负例，末轮15pass，均actual0且范围内0变化；保存两原收据，不继承覆盖。未运行service、HTTP、MCP、ASR/decoder/DB。

新运行准入Binding完整ABI需独立Review+root再批，标准增量也待RV19；source bodies本轮只存Test正文，真正完整生产正文/库/资源仍必须未来launch前归档，不补T14。自己源码/收据/副本/hash与COMMANDS见T17PreparationHandoff。所有工具终态、候选停写；完整Gate0→R1独立验收三OS/真实自动作品→连续R2不缩。
