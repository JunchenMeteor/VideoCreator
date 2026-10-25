# ADR 0006：媒体拒绝415的公开契约准入

2026-10-08；状态：批准接口方向，B5实现、集成生成及T6真实HTTP验证待交。不冻结B4工作中源码，不修改实施/测试/标准，无费用或key读取。

## 依据

RV2-P01为P2：W4最终ffmpeg.py SHA256 `36a13bb084228e1e1b1021da8812688720192c71560340a4951ad6595a201a5d`的APNG与MP4外部dref拒绝抛EngineError415；ERROR_RESPONSES及生成的assets/import responses缺415。原生成manifest使用API SHA `90ca70480c8b245ba08717d1d89092e626a62cf703a38a9805509c18276228b1`；A3观察API SHA `d15655ec3c622c2f62b6b76fa5e3a0819de2553434a49c4d1b3a21eeace15b92`已有B4私有生命周期WIP，415仍缺；这只标记观察版本，不是固定通过源。

T5普通APNG11、dref16—18收据显示领域415、decoder_processes为空、asset为空和暂存仍ready，属于实际AssetService调用，未证明真实HTTP415。T5原58/新25免费机制绿按各自固定源保留，不能继承给未来B4/B5或生成SDK。

## 裁决与兼容

1. 保留现有415：`media_format_denied`用于已识别的APNG不支持；`media_reference_denied`用于已识别的外部或不支持的MP4引用。复用唯一Pydantic ErrorEnvelope的code/message/retryability/request_id；这两类retryability保持`never`，同一输入不因网络重试得到支持。不能降级到200、吞安全拒绝或把所有媒体验证失败统改415。
2. B5在唯一API源ERROR_RESPONSES补415声明，引用现有ErrorEnvelope，说明媒体格式或媒体引用政策不支持；确保assets/import实际OpenAPI继承该声明。现有EngineError handler保留原status/code，禁止前端/媒体手写第二份Schema。无需增加请求/成功响应字段或复制类型。
3. 原垃圾内容/解码失败422（含原`media_process_failed`）、请求/内容完整性422、缺资源503以及权限/大小等原错误约定保持。格式政策拒绝与解码失败是不同分支，不能为填契约修改旧反例期望；不能扩大W4格式支持范围。
4. 这是候选契约补全，不声称稳定版冻结。保持API v1及候选版本方向；集成按真实固定源重新生成OpenAPI、schemas、SDK及source/output manifest哈希，不手改生成结果、沿用旧source manifest或把B4尚未稳定的代码写成已验版本。将来稳定契约变更遵守既有版本规则。

## 唯一owner与完成界限

B5与B4同一永久后端owner，顺序处理同一api/app.py，先完成并交B4固定源，再实施本窄声明；不并发写同文件或覆盖生命周期修改。T5冻结批已结束，仅解除该批写入等待，不解除随后独立验证的源冻结。B5保存精确源hash及免费检查证据；集成消费其稳定源生成契约/SDK，前端只消费。

T6独立在固定B4/B5源和真实受控媒体decoder下，经实际HTTP暂存/导入复验APNG、网络URL/目录外URL/URN dref：状态415及唯一ErrorEnvelope/code/retryability/request_id与声明一致，拒绝前无decoder/外部读取、无Asset成功。另核原垃圾422与原错误回归、合法真实媒体成功及生成manifest一致。只直接调用AssetService或只断言OpenAPI不关闭本P2；由RV独立复审，产品/安装/作品验收另行。

ADR0005私有协议不改公开Schema的范围限定不禁止本ADR明确的415公开补全；本裁决不认可B4运行结果，不改变原AV0 exit3，不调整ADR0003三轮或新付费Crew限制。Gate0、生产框架、R1/R2均未因此通过。
