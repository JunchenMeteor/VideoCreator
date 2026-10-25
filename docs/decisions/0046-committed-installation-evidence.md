# ADR0046 — 原安装已提交证据的唯一受保护侧文件

状态：ARCHITECTURE_SOURCE_ONLY，2026-10-10；仅闭合ADR0045 Native seq4后至seq5前的原commit核验。未实现/运行/授资格。Backend固定SourceStageOne证实receipt目前只有SQL；ADR0044/0045没有可直接消费的完整侧件。保持trust8、snapshot6、v214、seq4/5、单Engine、免账号、四profile/full147+24/三OS、独评独验及R1后R2，不增加权限模型。

## 1. 精确既有来源与引用

仅据冻结普通副本：SourceIndex2869783a1f78fc8e50be9e2bfc95baa53a9fd7025c60934f4702f1fde5c45a30。application/installation_trust_consumer.py SHA4c567a3505ffa2da260c1c46b5a4c81908e32a2754f340e986bccea69c155800，78–93行实际source_receipt_json=严格TrustAdmission8；trust_ref.sha256=body_sha(admission)，document_id=SQL admission_id、revision=SQL revision。132–136行首次admission_id='trust.'+body_sha(admission)、revision=1；169–172行trust事件receipt_json为相同8键正文，commands保存原snapshot，不是授权ticket。保持这些实际语义，不把SHA改成SQL整行/请求/文件的SHA。

domain/installation_qualification.py SHAa8c0779b1ff57c84b3c806839899b87a8bba7d4378947c71e291b6950fae5a54，24–32行canonical/body_sha、243–271行trust8/snapshot6、298–317行InstallationRecordAdmission10已经固定。record consumer/seq4持久化仍未实现；下一实现须将原完整record action10正文存events.receipt_json，不能只存成功标记。原native成员/source/instance/build绑定按ADR0044/45，正文引用不替代其来源。

## 2. 唯一文件、私有严格类型

实际原DataDir/Control/CommittedInstallationEvidence.json；staging为同目录CommittedInstallationEvidence.pending。不是Composition/Control的QualificationMaterialsIndex。目录由原Engine DataDir/原native OwnerDirectory/持有目录对象确定，任何locator/record/env不能指定新root。canonical UTF8 sorted compact，无LF/BOM；拒duplicate/unknown/noncanonical/bool-number；body≤4MiB，不截断。I64/Ref/Identifier/完整SHA沿ADR0044。文件不含自hash、密钥、bearer、签名私钥、vault或新的权限字段。

顶层恰format/instance_id/registry_revision/trust_commit/record_commit；format固定installation-committed-evidence-v1。instance_id为实际Engine；registry_revision PositiveI64，为这份已提交trust或record事件的实际registry revision。record_commit在首次trust提交时null，首次record提交后非null。没有ready/approved布尔或其它state，生产状态仍以原真实snapshot/Control/source交叉核验。

trust_commit恰admission_ref/action_ref/request/request_sha256/registry_revision/source_receipt：

- source_receipt=完整原TrustAdmission8（action_id/accepted_at_us/issuer_id/trust_mode/public_key_hex/material_refs/host_build_receipt_sha256/intent_sha256），逐字段/原canonical字节等SQL immutable source_receipt_json与trust event receipt_json。Backend以既有trust_row_admission交叉检查所有SQL列，再导出，不另造receipt。
- admission_ref=原trust_ref(row)，SHA仅canonical source_receipt；首次document_id='trust.'+SHA、revision=1。必须等snapshot.trust_admission_ref及原安装source.admission_ref。
- action_ref为该immutable event receipt的Ref：document_id=source_receipt.action_id、revision=该trust event.registry_revision、sha256=body_sha(source_receipt)。它仅标识原事件正文，不是新增authority或整行DB hash。
- request=ADR0044原五键action_id/kind/trust_admission_ref/record_ref/expected_registry_revision；首次kind=trust_admit、record_ref=null、expected=0；request_sha256=body_sha(request)，等原commands及event.request_sha256。registry_revision=request.expected_registry_revision+1，等action_ref.revision，首次为1。原actor必须是已认证安装source，不由此JSON授准入。

record_commit恰record_ref/action_ref/request/request_sha256/registry_revision/source_receipt：

- 首次source_receipt=完整已认证InstallationRecordAdmission10（action_id/accepted_at_us/kind/trust_admission_ref/expected_registry_revision/record/record_sha256/host_build_receipt_sha256/intent_sha256/material_index_sha256），原canonical字节等record event.receipt_json；record正文与immutable records.record_json逐字相等。kind首次严格record_admit；其trust_ref必须等trust_commit.admission_ref。record full SHA包含签名，按原typed validator核。
- record_ref.document_id=record.record_id、revision=record.revision、sha256=record_sha256，等DB记录及snapshot.current_record_ref。action_ref.document_id=source_receipt.action_id、revision=record event.registry_revision、sha256=body_sha(完整10键source_receipt)。action_ref和record_ref不可混用。
- request=原五键，action_id/kind/trust_ref/record_ref与receipt相符，expected_registry_revision与receipt相等；request_sha256等canonical request、commands及event.request_sha256。registry_revision=expected+1且等action_ref.revision、实际event/current。文件顶层registry_revision=record_commit.registry_revision；record为null时等trust_commit.registry_revision。原trust event revision不回填为新的record revision。

source_receipt的持久私有RecordReceipt另只允许已经批准的升级kind=replace，仍上述精确10键（类型与first InstallationRecordAdmission区分）；它只能由原实际升级installer+既有Owner管理source导出，不能改首次record wire的kind闭集、不能从sidecar建立升级入口。当前没有该真实producer就拒qualified升级。source_receipt始终是原event原字节，不“把旧receipt的kind改为replace”。文件保存最近真实record准入及其原trust准入，不假冒所有后续revoke事件的镜像。

## 3. 唯一提交与持有顺序

在ADR0044/45原安装或日常控制锁序内，Backend：

1. 原strong安装action/current guard及完整材料在事务外核验；QualificationControl.reserve先写原floor/pending/fsync。
2. 同SQLite connection短writer实际commit immutable trust/record/event/commands/current及前后local source guard；不读文件/OS/RPC/crypto。record准入不取生产lease。
3. 从实际已commit immutable row/event/command核对构造本侧件；atomic写.pending、flush/fsync、replace正式file、按原平台安全durability语义完成目录同步。必须保原DataDir/Control Owner/祖先保护。Windows沿原fsync/替换设施，不能宣称未测的断电保证；POSIX原目录fsync。
4. 再原atomic/fsync写六键QualificationTrustSnapshot.json，最后QualificationControl.complete同revision/requestSHA，pending=null。任何一步失败不发成功、不切native qualified。
5. 首次trust seq3 committed也在侧件trust-only+snapshot+complete后才发；record seq4 committed在完整侧件+snapshot+complete后才发。Native实际持有并验证下节三个文件和原action，才切Registry并发原seq5；Backend仍正常v2认证current，不用seq5 JSON造issuer。

原typed snapshot.commands result_json不改。未知已commit事件的侧件只按真实SQL immutable事实重建，不能从接收帧、预期输出或pending marker写出“已提交”。拒link/reparse/UNC/目录逃逸/alias；.pending已存在只接受完全相同canonical bytes及原保护，否则qualification_unknown，不覆盖不同动作残留。正式现有文件只有同原控制锁、真实下一event/准入guard或exact恢复可替换；较高revision/异instance/不能解释的字节不降级覆盖。固定filename允许atomic版本替换，Native必须保持原打开对象，不能按后来同路径/同SHA重开冒原held来源。

## 4. Native核验、current与释放

Native不开SQLite。先持原DataDir/Control目录及实际三个文件：InstallationQualificationControl.json（原canonical+LF五键）、QualificationTrustSnapshot.json（canonical六键）、本侧件（canonical五键），并保原材料/host/build/目录/child guards。Control namespace/format/instance核原值；pending必须null，minimum_revision必须等snapshot.registry_revision及侧件registry_revision。snapshot.state=qualified要求record_commit非null、current_record_ref完全相合；trust-only即使文件齐全也not_ready。

逐项验本侧件strict类型/canonical、全部Ref/request/bodySHA、两原event revision关系，以及原held材料/source index/trust anchor/签名/期限/完整许可证/report/profile/target/build/maps；action_id/accepted_at/intent/request/ref必须对应Native原retained安装action/member及sameinstance/原child。原action成功帧只是关联，不能替代真实输入成员。restart/exact恢复按原受保护installer action来源重建live强source，不Deserialize侧文件成member；原来源不可恢复即unavailable/unknown，不用此文件独立授权。public_key_hex只与原已admitted原锚交叉比，不读取candidate key自动信任。

随后保持实际侧件+snapshot+Control/原来源的current观察，在原Registry读lease及epoch生命周期中绑定；writer仍只同Engine member/epoch/同connection行检查，不新增RPC/文件核验。观察间更新/pending/保护失败拒新lease。升级/替换沿原Registry barrier及控制锁序失效旧epoch，新holder核新文件后才授新current；旧文件HANDLE/FD和已受理driver资源保到各原scope真实终态，不能提前force-close其它holder。平台文件共享不允许replace时明确busy/pending，不能放松保护或把失败写当成功。

revoke/trust_revoke/expiry关闭新lease并沿原guard/floor/source语义拒：旧侧件可能仍保存原准入事实，不为revoke伪造新准入receipt/抬高其header。snapshot.revoked/not_ready或Control更高/pending/原source epoch撤销优先拒；低revision侧件不能带来qualified。下一真正record准入/升级才写新匹配准入证据，未知/未完成不能改floor补绿。已accepted媒体/预算/unknown保原语义，不因receipt侧件删除或重提。

## 5. 失败/恢复的精确边界与交接

| 中断点 | 行为 |
| --- | --- |
| reserve后、SQLcommit前 | pending保留；没有已提交侧件，原exact source/request/key核实，不能伪写receipt |
| SQLcommit后、侧件前/写一半 | 不发seq3/4 success；DB可能已接受，保原ID/key/request。原source恢复核immutable rows/event/commands后写exact侧件 |
| 侧件后、snapshot前 | 原floor pending阻生产；按同真实receipt补exact snapshot，不把侧件单独当current |
| snapshot后、Controlcomplete前 | pending仍拒；同revision/request的原exact恢复补complete |
| complete后、成功stdout/seq5丢失 | 原commands/event核已提交；不换action/重做人审或重收费，恢复原侧件/snapshot/current结果。无法重建真实source则unknown，不默认ready |
| 正式/暂存字节、ref或高floor不符 | changed/unknown，保较高事实，不删除来源或用较旧body覆盖 |

Backend下一唯一实现：私有CommittedInstallationEvidence strict模型/同目录atomic helper；trust consumer在当前install_snapshot前插入侧件、exact retry亦重建并先写侧件；新record consumer写完整原10键event receipt并同顺序导出。维护实际既有trust_ref SHA语义与commands结果，文件导出不产生新权利。

Integration下一唯一实现：原实例Control retained读取/strict验证上述文件及两action/ref/request/member；实际current barrier/epoch后seq5，无SQLite、不从marker发lease；原Composition材料根及十purpose/caps不变。Linux headless实际OS installer/原FD/peer来源按ADR0045保留，Windows HANDLE不是所有平台前置；未有真实平台/source/license报告仍not_ready。

Test/独Review/Acceptance核完整写序与每个崩溃点、字节/ref/instance/保护/较高floor、未恢复强source、revoke/expiry/replace、Native无DB及writer无外部I/O。本文只读固定普通源/写架构，未DB/签名/key/OS授权/模型/安装/费用执行；source设计不算qualified或R1/R2完成。
