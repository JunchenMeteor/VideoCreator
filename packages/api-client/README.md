# VideoCreator API client

公开契约集为`0.3.0-candidate`，API info仍为`0.1.0`；既有0.2默认与显式0.3行为保留。类型和路由从唯一后端CLI/OpenAPI生成：schema.d.ts、routes.generated.ts、native.routes.generated.ts及NativeRouteManifest.json，不要手改或维护第二套领域/原生路由。当前包仍为仓库内private源码包，不是已发布npm包。

```ts
import { createApiClient, ApiError } from '@video-creator/api-client';
import type { components } from '@video-creator/api-client';

const client = createApiClient({
  mode: 'direct',
  baseUrl: trustedRuntime.engineOrigin,
  getToken: () => trustedRuntime.sessionToken,
});

// 本机开发宿主的受管代理：必须使用已可信工作台页面的同一个 origin。
// 不提供 getToken，不创建假 Bearer，不从 VITE_ 或模型输入取得连接资料。
const localClient = createApiClient({
  mode: 'managed-proxy',
  baseUrl: trustedRuntime.workbenchOrigin,
  trustedOrigin: trustedRuntime.workbenchOrigin,
});

const manifest = await client.request('GET /api/v1/bundles/{revision_id}/manifest', {
  path: { revision_id },
});
const semanticPage = await client.request('GET /api/v1/bundles/{revision_id}/semantic-segments', {
  path: { revision_id },
});

async function exportBundle(request: components['schemas']['BundleExportRequest'], idempotencyKey: string) {
  return client.request('POST /api/v1/bundles/{revision_id}/exports', {
    path: { revision_id }, body: request,
    headers: { 'Idempotency-Key': idempotencyKey },
  });
}
async function importBundle(request: components['schemas']['BundleImportRequest'], idempotencyKey: string) {
  return client.request('POST /api/v1/bundle-imports', {
    body: request, headers: { 'Idempotency-Key': idempotencyKey },
  });
}
```

`routes`列出全部实际OpenAPI操作，可调用制作请求/状态/决定，作品manifest与artifact content，semantic分页，grants/revoke，export journal/status/content，import/status/manifest/content及import export。path/query/body类型引用生成的`operations`；HTTP头保留Range、If-None-Match、Idempotency-Key等接口用途。JSON保持调用方给出的字段，不自动补版本/默认值、主体或权限，重试与幂等key由调用方明确管理。

连接只接受无用户密码/query/hash/path的HTTP(S) origin。session bearer仅由可信连接的getToken在内存取得；禁止把模型key放前端/VITE/本地存储。SDK不记录token、不允许调用方覆盖Authorization/Host/Cookie，不携带cookie，不跟随跨端点重定向；服务端仍负责principal/scope/资源授权。SDK不是请求权限或模型授权来源。

`direct`（为兼容既有调用而默认）取得可信会话 Bearer；`managed-proxy`只接受精确的`http://127.0.0.1:<port>`工作台 origin，并在浏览器中再次比对当前页面 origin，生成路由限定在`/api/`。它仅设置`X-Video-Creator-Client: workbench`，不发 Authorization。该标识不是授权凭证：实际 DevRuntime 启动 API 与 Vite，随机会话令牌只由宿主传到两个子进程；Vite 还检查 Origin/Sec-Fetch-Site/Host，然后向 API 注入 Bearer。没有配置宿主、跨 origin、调用者覆盖 Origin/Host/Cookie/Authorization/客户端标识时拒绝。普通静态网页无法由此获得桌面 owner session。`trustedOrigin`是可信宿主的 ready 消息或已打开可信工作台页的 origin，不接受模型 payload 提供的连接地址。

返回`{status, headers, data}`。JSON按生成类型消费；非JSON媒体返回ArrayBuffer、文本返回string，204/304 data为undefined。Range等头由调用方显式传入。HTTP错误抛`ApiError`，保留status和原公开payload（JSON或框架纯文本），不把不合法JSON/未知数据强行签成ErrorEnvelope。公共ErrorEnvelope类型来自唯一生成模型。AbortSignal只停止本次HTTP等待，不等于取消制作或导出job；需要取消时调用明确的production cancel端口。

`requestRaw(key, args)`沿相同生成路由、path/query/body MIME 与认证规则返回未消费的原始`Response`，包括错误状态、206、304；它不调用 json/text/arrayBuffer，不复制大媒体、不静默重试，也不把 HTTP 错误改成 JSON。调用方先判断`status`/headers，再读取`response.body`流或`arrayBuffer()`。例如 JSON artifact 的 SHA 应对完整原 body 字节计算，禁止`JSON.stringify(await response.json())`重建后校验。206只校验实际部分的字节，304没有完整 body，二者不能证明全文件 SHA。便利`request()`仍保留原来的解析和`ApiError`语义。

桌面现有真实I20壳有来源守卫，但get_engine_session明确unavailable，尚无Rust broker/API会话。新增native SDK只接实际invoke/非秘密descriptor，不返回假bootstrap、Bearer、API baseURL或本机路径。开发代理证据不代原生联调或三平台安装。

历史I19 SDK有本机真实API有限读/缺资源/错误路径传输，不能继承为当前I25/native通过。当前31操作含源声明raw staging、Bundle/material/semantic/grant/export/import、Range/SSE。Asset条件304未实现，HEAD未注册。Portal权限/MCP/full-eight作品/ZIP/完整权限矩阵与三OS仍pending，路径覆盖不当能力交付。

编译器为既有TypeScript7.0.2 native CLI，ES2022/NodeNext/strict/noEmit/allowImportingTsExtensions。openapi-typescript7.13.0内部JS TS5.9.3是生成工具实现。I25实际当前CLI来源/公开差异、strict TS、原失败与纯协议机制见Integration/NativeContracts-I25正式交接，不外推Frontend/Native实测。

## NativeTransportV1

```ts
import { createNativeTransportV1 } from '@video-creator/api-client';
// invoke必须由真实Tauri入口提供；现壳尚无broker会明确unavailable。
const transport = await createNativeTransportV1({ invoke });
const nativeClient = createApiClient({ mode: 'native', nativeTransport: transport });
```

初始化实际调用无参get_engine_session，核instance/generation/版本/唯一manifest SHA/private wire format/有限资源参数；未知字段拒绝，构造器不能绕握手。非秘密descriptor不授owner，宿主须每次核实际main WebView完整URL/capability/generation/owned child/health；页面origin不能自行授权。native配置禁止混入baseURL/getToken/fetch/trustedOrigin。

native只传operation ID与源声明path/query/headers/body，broker构造实际loopback HTTP。无renderer URL/method/Authorization/Host/Cookie/Origin。逻辑path段由宿主编码一次；参数必填/类型/枚举/长度/native header pattern取生成源，Content-Type来自唯一requestBody.content，staging */*默认application/octet-stream。域JSON/principal/grant/purpose/rights/资源授权仍由后端执行。

64KiB seq/offset帧有限拉取，ReadableStream highWaterMark0，在真实EOF核长度/release；单消费者禁止clone/tee。非2xx保原body，204/304空body，206不全文件SHA，不透明解码/重定向/重试。401使会话不可再开；NativeTransportError固定code/phase/may_have_been_accepted，不造ErrorEnvelope/HTTP状态，不echo秘密或本机异常。AbortSignal/reader cancel只abort HTTP，不制作cancel。

上传只用已知长Blob/Uint8Array/ArrayBuffer，Blob逐slice最多64KiB，ack核seq/offset，总长finish；同时等response head，early拒绝停读body，head timeout从完成上传开始。服务端raw staging是512MiB有界bytearray，不恒定内存落盘。SDK不加128MiB下载截断；request()可整体读取，大文件用requestRaw/save。

transport.saveResponse仅本transport未消费full200文件Response，委派host真实dialog/delivery-ref授权/有限流式size+SHA/atomic partial/取消，不收renderer OS路径。mediaOpen/Close委派delivery-ref/purpose，返回private native-media URI和逻辑handle；host每段重新授权、单范围<=1MiB/4并发。broker、对话框、>128MiB/RSS、seek/撤销均not_run，SDK方法/模拟返回不当交付。

readEngineEvents(response,{maximumEventBytes})是可选SSE解析：保data_raw/event/十进制ID，忽略heartbeat、严格增加不要求连续；caller显式保最后消费游标再恢复。raw transport不重建SSE/自动重送；event上限caller明确给出，来源无retention-gap/futurecursor错误，断帧拒绝不假完整。

generation.manifest绑定真实export closure，partial错误先标generating，旧manifest不可当当前。自有private-wire检查明确synthetic，不是实际Rust/API/媒体通道证明；精确候选private ABI见NativeSdkConsumption.md。
