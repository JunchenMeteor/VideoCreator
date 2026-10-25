# ADR0076：本地音频时间映射目标

状态：APPROVED_CONTRACT_ONLY，待独立窄评；没有实现、运行或质量通过。只补0075的audio-only类型冲突，0075及旧0.2/0.3字节保持，不增加权限/资格/账本或改变precision标准。

## 唯一类型与适用分支

仅 `BundleManifestLocalV1`（0.4.0-candidate、local-material-bundle-v1）的 `audio_mappings` 改为 `tuple[LocalAudioTimelineMappingV1,...]`。Backend在原sole contracts维护该新型，恰含以下11字段：

| 字段 | 类型/语义 |
| --- | --- |
| `format` | Literal `local-audio-timeline-mapping-v1`。 |
| `mapping_revision_id` | 原 Identifier，指真实持久不可变映射记录。 |
| `target_media_role` | Literal `video` 或 `mixed_audio`，指实际最终时间线目标；不是读取或生成权限。 |
| `target_media_asset_id` | Identifier，必须是本次实际Manifest/selection对应role的已提交master Asset。 |
| `target_track` | 原完整 `c.AudioTrackRef`，必须是该目标Asset的实际音轨，含原SHA、stream_index、kind、duration、clock、method_ref。 |
| `target_coordinate` | 原 Literal `work_timeline`。 |
| `timeline_duration_us` | 原 PositiveInt，恰等于实际Manifest工作时长。 |
| `pieces` | 原 `tuple[c.AudioMappingPiece,...]`，非空、piece_id唯一；不另造piece DTO。 |
| `encoding_origin_offset_us` | 原 strict `int|null`；保真实编码/时钟来源。null表示未声明，不暗当0，不由无video猜填。 |
| `method_ref` | 原 Identifier，指本次真实MethodEvidence/Operation闭包。 |
| `content_sha256` | 原 Sha256语义，按原完整record的规范编码/self-hash投影规则核新body；不能复用旧型SHA。 |

旧 `c.AudioTimelineMapping.target_video_asset_id` 不改为nullable，不改旧parser、0.2/0.3关系或任何存量字节。新local parser严格拒旧target_video_asset_id、未知/重复字段和角色，不在解析时补ID/换SHA/猜video。已保存记录仍原不可变冲突与复用规则；不能在同ID下覆写另一body。

## 目标与实际master的唯一关系

- audio-only：有音频时目标只能 `mixed_audio`；target_media_asset_id、target_track.asset_id/SHA必须等于selection实际mix及Manifest Artifact；kind必须mix_master。旁白作为真实source_track（kind=narration）映射进mix并可独立交付，不能借旁白独立Asset冒时间线mix目标；不生成video/cover。
- video且有音频：可以映射实际mixed_audio音轨，或实际成片的encoded音轨。后者target_media_role=video、target ID/SHA指真实video master，target_track.kind=video_encoded且stream_index/clock来自实际该视频解码；前者与audio-only同样精确指mix。只存在video Asset不证明存在encoded音轨。
- narration_audio、cover、输入素材、ASR解码子Asset均不能冒target master；它们作为原真实source/证据保持。任何其他Asset、role/track错配、未settled输出或另一Run准备结果均拒绝。mix master与实际视频音轨作为最终时间线目标，保原工作时长及原decode/sample/PTS容差；不允许以补零时长/改duration挤过检查。
- no_speech但实际有audio：必须保实际mix/encoded音轨及完整source映射，不能因为无CTC单位就删音频来源。0075的真实ASR/gaps/no-speech证据及不适用分支原样。
- no_audio_observed：audio_mappings恰为空，仍须0075的实际decode无音轨证据与无audio tracks/master；若有实际音轨或音频输出则空映射不是合法absence。旧格式仍不接受空映射。

每个真实最终音频目标及其用于ASR/字幕/RAG的时间线关系必须有原实际映射；不能附一条无关mapping就算完整。所有mapping_revision_id及piece_id在Bundle内唯一。target Asset、音轨和源piece均由原受控preparation/master/source reader取得，数据相等/新role不扩大原leaf用途、版权祖先闭包或wholeManifest披露。

## 原sample、PTS、clock和内容校验保持

沿原 `AudioMappingPiece.raw_coordinates` 与 `BundleService._check_mapping_piece`：正且约分的播放速率、source范围在实际intrinsic duration内、成对sample边界且不超过decoded_sample_count、完整且递增的signed PTS/timebase、有真实sample或PTS证据；保实际origin_pts、half_up_us及原(-1,1) rounding error、精确有理数变换和原1微秒关系容差。不得以新target类型放过任一原校验，不能从计划时长造AudioClock或origin。

原受控audio clock方法核实际源文件和目标真实音轨的SHA、decode sample count/rate、stream/PTS/timebase；缺该真实方法/资源沿原具名NOT_READY，不把dict/签名/True字段当clock证明。每piece.timeline_range仍在本工作时长内，实际crop/place/resample/time_stretch/encode方法与原成功settled Operation保持；同Run/current/fence/hold/source前后与两authority、unknown/预算/限次完全不变。

字幕的mapping_revision_id和semantic音频spans/ASR validation context必须指上述同一实际mapping/piece及对应实际transcript输入/源音轨；只有目标角色变化，不改变intrinsic→work_timeline坐标、字幕序列化/量化或200ms/MM05。video的语义video_asset_id另按0075核实际video，audio-only保持null；不能从segment的null推断或伪造映射目标。受控编码解码ASR子Asset仍经原父Operation/音轨来源闭包核，不因为它有音频就成为master。

## 实际caller与下游切片

1. Backend sole新类型/显式local schema dispatch；BundleService的local关系验证替换旧“每条必须target_video”的这一谓词，改核上述role/actual master/track关系，同时复用原record、piece、clock、source、Operation和rights验证。旧verify及旧mapping关系不变。
2. 同local分支的preparation/assembly/持久readset、共享ASR runtime/alignment verifier、import/export/引用projection必须消费该唯一类型及完整SHA；按真实已绑定profile选择新/旧，不能在内部再次强转旧型或把普通keyword当可信profile。不新开调度或恢复权限，缺旧context保真实missing，不重ASR/改pointer来补映射。
3. Media只构造并持久该后端型，从真实local edit输出/解码、原source tracks/pieces和原method构造，音频作品直接target实际mix；不能自造公开DTO或填假video。原已有video路径可按真实目标音轨事实使用local新型；旧模型profile继续原型。
4. Integration在Backend冻结后由sole源生成0.4客户端/包数据类型；reference/export/import用同原Manifest/record字节、SHA、purpose、expiry/revoke和实际本机receipt，不借origin授票。Frontend无需新增权限字段。实现/测试各由原角色完成，不由这份合同授运行。

独立窄评/测试至少核：audio-only实际mix及旁白source、video的实际mix/encoded两目标、no-speech保mapping、真no-audio空tuple；以及fake video/空音轨、track SHA/Asset/role错配、source sample/PTS越界/缺对/伪clock、量化/速率/offset错误、另一Run/unknown、旧型误入0.4及0.2/0.3误入新型、冷恢复同SHA与不可变409。精度真实超阈值仍原拒绝/有界修复，缺资源不宣成片。

固定来源：任务卡SHA `3dd1f602ab7a1e51aec879f389c701b977fea7a76f4d554c7b201db41068f762`；0075 `776a1bb058bc79d9beee04aa9da129219e786c33707a01732a1c9b942a071091`；正式独评 `54b550e100b4ed75e496b7a6c65ecba66433ab21fa915464cd60526075ef7061`；停止Backend134 contracts `3562a76f3082953b67cbecd60989a3d891a574473255c21895188806bc3624fb`，AudioMappingPiece/AudioTimelineMapping约第789—842行，旧Bundle消费者2650—2685及2753—2787。有限绝对路径、普通副本和真实读取终态见过程InputPins/Handoff；未读取活动候选。完整R1独验后连续R2与三OS目标保持。
