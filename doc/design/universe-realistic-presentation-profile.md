# Universe 写实只读呈现 profile v0.1

2026-11-10；I20-B；基线6c533af。状态：**设计/CPU合同交付，UE实现与画质未验收**。父计划：[I20](universe-i20-realistic-pdca-plan.md)。本文件与固定合成fixture不修改v0.2 authority/parser/worker/I0A、Actor或GameMode。

## P：两种版本与两条来源链

当前权威记录明确使用`basicshapes-proxy.v0.2`。其asset条目、Python/C++校验器、I0A四根九文件闭包及GameMode installed-graph equality都限定技术代理。真实材质/植被不能换进原authority资产清单，也不能把旧资产的`use`重写为写实。历史原件、I18 exact3和I19失败保持。

本轮提出独立呈现模式 **`realistic-readonly-sidecar.v0.1`**。它消费已验证的`FEdgeWorldUniverseObservation O`及由启动器独立固定SHA的本地profile；不重新解释或修改O的旧projection版本，不创建世界存在、推进tick、运行Genesis或成为另一writer。启动器的profile/SHA不能从Observe响应、HUD、Actor名或未经审查环境回显取得。

profile格式`edgeworld.universe.realistic-presentation-profile.v0.1`记录：target、authority静态绑定、固定region、源文件与许可引用、资产依赖、角色/几何/材质recipe、明确实例列表、无fallback/无碰撞/本地展示时钟。默认产品写实入口缺必需profile即显错；原技术入口可以保持既有行为，必须明确属于旧技术模式。写实入口不得用BasicShapes或别的tick填缺。

来源链分开记录：

1. 权威链：public pins → 独立status trusted head → 原始Observe proof → world/Manifest/State/Event/selected triple/Transform/权威asset manifest。
2. 呈现链：独立启动pin → 原始profile文件SHA → 源资产/许可引用/依赖 → 导入原件及Native evidence → 精确renderer源码/Host/plugin二进制身份。

SHA绑定的是**实际文件字节**，不是把JSON重新序列化后的“等价”数据。文件内容摘要不证明许可或Native真实性；这两项由独立来源/导入审查确认。profile中出现`native-observed`是待核对的声明，不是放行布尔值。

## D：最小profile和ViewBinding

结构schema与合成例位于[fixture目录](../fixtures/universe_realistic_presentation_profile_v0_1/README.md)。三个evidence class分别为`synthetic-contract-only`、`source-inputs-pending-native-import`、`native-observed-proposal`；前两者的Native unit/pivot/bounds/slots/evidence必须为unresolved/null。后一类必须给真实引用、尺寸和完整slots，但仍须真实UE producer及独立审查，CPU合同检查不能授权运行。

`ViewBinding`格式`edgeworld.universe.realistic-view-binding.v0.1`同时保留：

- world、Manifest、State、Event、tick/revision/watermark与unit_transform；
- `authority_projection_version=basicshapes-proxy.v0.2`；
- `presentation_mode=realistic-readonly-sidecar.v0.1`、实际profile SHA和独立renderer build SHA；
- 本地单调`view_generation`，用于拒绝旧异步完成覆盖新选择。

因此真实资产画面不冒称“按旧BasicShapes绘制”。产品UI只显示有意义的当前/历史时间、加载/失败状态；上述hash、来源细节和诊断字段默认写开发日志，不把实现细节堆入用户流程。

### 角色、几何和实例身份

当前六个Decoration都是`asset-cube`场所marker，没有树种/地表/水面角色。新profile用明确`place_id + place_kind + binding_id`及稳定`instance_id`映射vegetation/rock/ground/water；不能把所有cube统一替成树，不能由材质颜色或帧数产生世界实体。首个20m×20m lookdev只裁取已验证forest矩形的一个region，属于测试切片，不是新世界起源或整座森林完成。

- vegetation/rock必须引用完整已声明StaticMesh；ground/water可以引用已声明mesh或由已验证区域按固定算法派生几何。水面不是Genesis流体模拟。
- 首版`explicit-list.v0.1`明列派生实例，不用本地随机/FrameTime。位置为UE cm，旋转为mdeg、缩放为ppm，避免没有单位的浮点倍率；导入单位、pivot、bounds尚未知时不推测实际物体尺寸。
- 原Genesis两体的sphere/support、单位反射与config尺寸保持；真实boulder或植被不替换其碰撞形状。写实装饰禁UE模拟、重叠/世界因果碰撞；后续本地导航另卡。
- CPU初始fixture仅支持源矩形内region和已验证elevation；ground正例的`geometry_source=verified-place-region`、`mesh_asset_id=null`明确声明派生平面角色，不引用预览球。这只是矩形平面规划声明，没有实际生成或导入几何，也不证明Native地表通过；D3必须固定平面拓扑、尺寸、法线/切线、UV和高程后实测。它不是一般GIS/非平面地形求解；后续斜坡或复杂footprint需明确版本化算法和原始几何测试。

### 材质recipe与实际I20A输入

每个material声明唯一texture role、source_file_id、channels、sRGB、normal basis、blend mode/cutoff与two-sided。schema只能检查字段，CPU语义检查只能检查引用/重复/缺项；真正PBR节点接线及UE sampler必须Native审查。

I20A[文件索引](../evidence/universe-I20A/asset-index.json)摘要`d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7`已被本任务实际重读核对；其[verification](../evidence/universe-I20A/verification.json)记录真实来源检查。D3接线时必须保留这些事实：

| 输入 | 必需处理 / 尚未证明 |
| --- | --- |
| fern_02四clump、6232 triangles；源material为MASK/doubleSided | BaseColor JPEG没有alpha，独立`fern_02_alpha_2k.png`必须明确连接OpacityMask、clip0.5、TwoSided。仅导入glTF默认材质不能算正确覆盖 |
| boulder_01、66122 triangles | 先验证单位/pivot/Native bounds再决定visual实例尺度；不能改变Genesis sphere/support或产生新权威碰撞 |
| forrest_ground_01、107390 triangles | glTF是预览球，不是世界地形。使用其PBR纹理到获准派生ground，不能把球作为地表 |
| glTF原始GL法线、额外`*_nor_dx_2k.jpg`与ground ARM | glTF保留原始GL法线依赖与摘要；额外DX图只能由版本化UE材质recipe显式指定override，记录原/选中source_file_id及转换/采样约定，不静默替换原始来源。Native核对DX法线方向与颜色空间；ARM R/G/B分别AO/Roughness/Metallic，数据纹理不得作sRGB |

本任务没有创建实际CC0资源profile或伪造导入metadata。正例仅用临时synthetic `.fixture`字节，所有Native字段unresolved。真实UE object path、class、material-slot索引/名称、法线/pivot/尺寸、texture参数和最终许可review必须由后续导入原件填入并审查。

## 事务和失败语义

现有GameMode在`ApplyVerified`前更新Session.Observation/bHistory；加载失败可能新HUD配旧画面。D3同一owner须实现：收到并验证O → 固定generation/ViewBinding → 隐藏预加载全部mesh/material/geometry → 验证完整输入/slots → 游戏线程同一次提交切换可见集合与“已呈现”HUD绑定 → 回收旧集合。已接收观察与已呈现观察必须区分。

任何必需项失败都销毁未提交的新集合，保留最后完整已呈现切片和其时间身份，同时显式报错/加载失败。旧请求晚到只可丢弃，不得覆盖新generation；相同profile但不同历史水位的内容不能混用。观察拒绝、场景一致性、authority不变分别验收，不能用空画面或map没变替代视图正确性。

## C：本轮实际CPU合同边界

[check_contract.py](../evidence/universe-I20B/check_contract.py)提供两个证据目录内的有界检查API，不导入产品模块、不加载UE/Genesis：

```python
validate_profile(profile_path, *, file_root, expected_profile_sha256, expected_authority)
validate_view_binding(binding, *, profile_sha256, expected_observation,
                      expected_renderer_build_sha256)
```

先用JSONSchema2020-12检查精确字段/类型/版本，再另做实际文件size/SHA、路径/链接安全、依赖图闭包/环、角色/PlaceKind/slot声明、实例边界及跨字段绑定检查。外部独立expected值不是从待验profile或binding提取。正例只返回`source_contract_consistent_requires_native_review`/`binding_consistent_requires_native_review`，明确`runtime_authenticity_verified=false`、许可真实性false、HUD原子性false、visual gate not_run。

这些检查不能证明资源真实授权、真正UMaterial/StaticMesh类型、材质节点、引擎依赖完整性、加载器实际fail-closed、HUD原子提交、画面或性能。它们只使下一owner能重现输入边界及错误拒绝；不能扩大I18 exact3，不能替代I19实际进程/只读/PNG门。

## Act：可独立执行的后续D3/D4任务卡

| Card / owner / 排他路径 | 固定输入与顺序 | 实际Check / 判定证据 |
| --- | --- | --- |
| D3-IMPORT / 资产导入owner；新`Content/EdgeWorldRealism`与版本化导入recipe、专用Native producer/test；不改authority | pin I20A实际index/SHA/许可；只导入fern/boulder和ground纹理；固定UE版本/单位/法线/材质recipe；导出所有真实.uasset/sidecar/纹理依赖SHA、class、mesh bounds/pivot及slot映射 | 在真实UE下读取源/import包及依赖闭包，收集Native evidence；负例缺.alpha/错slot/缺依赖/替换文件应失败。特别核fern独立alpha→OpacityMask/Masked/0.5/TwoSided；地表用固定PBR图与明确平面/地形profile，禁止预览球；保留glTF GL源法线，DX仅经显式UE override并核对方向/采样，ARM通道另验。JSON检查不替代这些producer结果 |
| D3-ADAPTER / 单一呈现owner；新profile loader/realistic Actor、`EdgeWorldUniverseGameMode.{h,cpp}`事务接线及相关tests | 固定上述profile与Native导入证据SHA，独立启动opt-in，保留原parser/worker/I0A。先纯投影规划与校验，再隐藏装配、原子提交HUD/ViewBinding；保持Genesis配置尺寸和无UE模拟 | Native故障注入：缺asset/错class/错slot/旧generation晚到/错误world或历史切片。抓取真正呈现的Actor集合与HUD binding，而非只返回success；必须旧集合+旧HUD一致或新集合+新HUD一致，无混合/代理fallback。保存精确source/build及test结果 |
| D3-BUILD / root唯一构建owner | 审查以上独立PR和集成差异；固定准确Host/plugin源和官方Build命令、DevSSD输出、预算 | 实际parent wait/完整Build日志、source/binary SHA与退出码；未编译、不完整或失败均不授平台门。旧5a6cca0 build不能替代新C++编译 |
| D4-LOOKDEV / root唯一实机owner，独立reviewer | 运行前固定真实视觉参考、Mac/Metal、实际像素、观察点/光照/资产LOD、明确预算；先TTY/stdin握手再clock；新卡、新run、NoTrace、独占DDC、完整写域。当前→历史→当前，实际相机/隐藏/暂停动作按批准短卡 | 原生PNG及实际shader/material/instance身份与Native import/profile/renderer SHA绑定；每动作全authority map不变、无Genesis求解或提交。保存全actor/HUD来源、正常退出/quiet/frozen证据。视觉/正确性/平台/性能各门单列，缺证inconclusive；新Observe仅匹配原件的Native回放可解除其parser差距 |

未定输入是Dot候选分支/commit、最终视觉参考、UE导入metadata、目标画质/性能阈值。缺Dot补丁不阻塞本轮源资产和合同检查；后续取得时按差异复用，不重写其植被/PBR实现。本轮没有运行以上D3/D4测试；新实现审定后才派发，失败仅重开对应节点。
