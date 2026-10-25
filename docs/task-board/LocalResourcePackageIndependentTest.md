# LocalResourcePackageIndependentTest

ACTIVE，独立测试开发角色 `test_local_resource`，只写仓库测试源码/Fixtures/配置/阈值所属 `tests/`、`services/engine/tests/`、`tools/testing/`、`docs/acceptance/criteria/` 与自身 `Test/LocalResourcePackageIndependentTest/` 过程证据；只读实施源码/资源包，不改 Integration/Backend/Media 产品或包、评审/验收报告。与原 R1 真成片验收分开。

固定停止输入：`Integration/LocalOwnedMaterialPackageResources/PackageIndex.json` SHA-256 `c961a30d1713b6d0306a80fdb53b0eca660dbec68bfba20fe6b4fc3b086e7b7d`，203物理件；`ExecutionRoundOne/CommandReceipt.json` SHA-256 `9ff8955f3056fd1994a65ebda96d2d752d524b013fe95ff4eb6bf58eb3138fef`；`Handoff.md` SHA-256 `9ca139b40f689987c237015a223fbaecceed3f5075e446f5357ba989221a6a16`；实际包根 `Integration/LocalOwnedMaterialPackageResources/PackageBuildRoundOne/`。资源包仅停止 Backend134+Media55 source/11 SQL/FFmpeg+ffprobe+7DLL/GPL及4生成文件，无Python环境/Owner/ASR，`ASR=null`必须保持WAITING。

独立实测：先按索引验证203物理文件的路径边界、无链接逃逸/大小写碰撞、长度/SHA与GPL正文；然后仅调用**包内**FFmpeg/ffprobe，在本任务自己临时目录生成短时合成音视频测试素材，实际编码视频+音轨、探测预期codec/帧/时长/声道、全流解码到null、验证输出哈希/失败退出与命令原始stdout/stderr。允许专门的短PNG静图hold加WAV/无音轨/纯音频样本作资源能力试验，明确它们不是产品Flow生成的作品。若无法实际测试某场景，给精确原因，不用已有旧资源/系统ffmpeg替代。

保留原始每进程argv/cwd/exit/双EOF/超时、每产物SHA/探测JSON与失败。可写最小可复现测试入口，不改变现有阈值或用Mock充成功。不要调用Pydantic全量导入或重复原19/三败限制；不得安装依赖、模型收费、读密钥、下载或生产部署。此卡完成只判Windows本地资源包的独立工具/索引能力，不判Python引擎、Owner权限、真实媒体制作、R1三OS/EXE/DMG/Linux或R2。最终报告、测试文件/命令、实际终态及全部读写释放交Root。
