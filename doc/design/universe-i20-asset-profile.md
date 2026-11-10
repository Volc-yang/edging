# I20-A：写实自然资产输入 v0.1

2026-11-10；父计划：[I20 PDCA](universe-i20-realistic-pdca-plan.md)。状态：**实际源文件取得与有界 CPU 检查通过；待独立审查/PR 集成；UE 导入、平台构建和画质未验收**。

## 固定输入与本轮结果

工作树 `codex/i20-assets`，基线 `6c533afb537a9c45bd471eb83887cdcd87b42052`。源文件仅在新独占目录 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets/`；没有修改原资产目录、UE Content、旧 authority 或 worker。

取得三个 Poly Haven 资产的完整 2K glTF 源依赖，并补齐 UE 材质接线所需的 DirectX 法线、蕨叶透明遮罩和地表 ARM。不是网站预览图、占位形状或模板截图。

| 资产 / 源页面 | 实际角色与格式 | 固定源版本 `files_hash` | 已检查几何 |
| --- | --- | --- | --- |
| [fern_02](https://polyhaven.com/a/fern_02) | 完整蕨类模型，glTF + BIN + PBR + Alpha PNG | `36e2a53d7f23f422640ad368c1f27745de2fef82` | 4 个蕨丛，共 6,232 三角形；材质 `fern_02` |
| [boulder_01](https://polyhaven.com/a/boulder_01) | 完整岩石模型，glTF + BIN + PBR | `83e2b16d6a089f8077d3eebe0462615c2ba0e7f6` | 1 个模型，66,122 三角形；材质 `boulder_01` |
| [forrest_ground_01](https://polyhaven.com/a/forrest_ground_01) | 森林地表 PBR；随附 glTF 球仅作材质预览 | `ea3ef3539e362d9a9ffa409ecd467d08028569d5` | 预览球 107,390 三角形；不得把它当世界地形 |

源版本由原始 API 元数据摘要、`files_hash`、下载 URL、源 MD5 和本地 SHA-256 共同固定；不是提供方承诺的语义版本。20 个实际文件逐项大小/哈希见 [asset-index.json](../evidence/universe-I20A/asset-index.json)，其 SHA-256 为 `d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7`。全部 14 张贴图经文件头检查为 2048×2048；未执行完整图片解码。

## 许可证与来源

[Poly Haven 官方许可](https://polyhaven.com/license) 将下载的模型/材质/HDRI 资产以 **CC0-1.0** 提供；网站文字/预览呈现及项目代码许可分别处理。保存的官方许可 HTML 及 [CC0 法律文本](https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt) 均在 DevSSD 的 `metadata/`，其原始响应 SHA 见 [metadata-receipt.json](../evidence/universe-I20A/metadata-receipt.json)；CC0 文本也随本交付保存。未取得网站预览图、购买资源或接受 EULA。

来源署名：Powered by Poly Haven。Fern 02：Rob Tuytel（scanning）、Rico Cilliers（modeling）；其余作者以 [原始 info JSON](../evidence/universe-I20A/metadata/) 为准。未来运行只读本地文件，不依赖在线 API。

Electric Dreams 保留为视觉参考，官方 DX12 要求尚不能直接等同于 Mac/Metal 支持；未作为开放许可资产引入。`pine_tree_01` 大包、FBX/Blender 包、无明确完整美术许可的“开源森林模板”延期。此组合尚无林冠、河水或完整生态场景，不代表 3A 世界画质通过。

## 后续 UE 导入与角色/材质接线输入

相对路径均以 DevSSD 资产根为基准：

| 项目 | 固定文件 / 接线 |
| --- | --- |
| 蕨类 glTF | `assets/fern_02/fern_02_2k.gltf`；节点依次 `fern_02_b`、`fern_02_c`、`fern_02_a`、`fern_02_d`；每个 primitive 材质索引均为 0 |
| 岩石 glTF | `assets/boulder_01/boulder_01_2k.gltf`；节点 `boulder_01`；材质索引 0 |
| 地表贴图 | `assets/forrest_ground_01/textures/forrest_ground_01_*_2k.jpg`；应用到另行批准的 ground mesh，不能实例化预览球替代世界地形 |
| Base Color | 各 `*_diff_2k.jpg`；颜色纹理采用 sRGB |
| UE Normal | 各 `*_nor_dx_2k.jpg`；数据纹理、Normal 压缩；固定 DirectX 约定，不同时叠加 glTF GL 法线或盲目再次翻转绿通道 |
| ARM | 各 `*_arm_2k.jpg`；线性数据，R=AO、G=Roughness、B=Metallic；自然介质的源材质 metallicFactor=0 |
| 蕨叶 Alpha | `assets/fern_02/textures/fern_02_alpha_2k.png`；显式接 Opacity Mask，Masked、cutoff=0.5、two-sided；后续还需独立决定 foliage shading model |

**实际源缺口：**官方 fern glTF 虽声明 `MASK`，Base Color 却引用 JPEG，无法携带透明通道。依赖闭包完整不证明自动导入后的叶片遮罩正确。已额外取得独立 Alpha PNG，后续 owner 必须显式接线并检查叶缘；不能用自动导入“成功”代替该门。

glTF 原始位置遵循米、Y-up。蕨类的四个源节点排列成约 1 米间隔的资源展示组，不代表权威世界的四个实体；应按 profile 明确选择节点/网格。原始几何 AABB、节点变换、材质名/索引和实际三角形数见 [verification.json](../evidence/universe-I20A/verification.json)。UE 导入后的真实 class、material slot 名称、轴变换、100 cm/m 换算、pivot/地面接触和派生 `.uasset` SHA **尚未观察**，需在 D3 固定，不能用源 glTF 名称冒充 UE 验证结果。

此输入只供独立、显式 opt-in 的本地 presentation profile；不能替换 authority 的 BasicShapes 清单、赋予物理身份，或将所有 Cube marker 统一变成蕨类。可在后续批准的 20m×20m lookdev fixture 验证材质，再做 Universe 稳定实例/角色绑定。资源缺失或哈希不符应显错并保留上一完整 ViewBinding；本轮没有实现 UE 加载器。

## Check / Act

资产门自检通过：20 文件、41,949,796 资产字节；全部响应体合计 42,116,535 字节（约 40.17 MiB），包含 166,739 字节元数据/许可；最终树 34 文件；首次元数据至网络结算 145.219 秒，28 次请求均成功且无重试/redirect/partial。固定 256 MiB / 64 文件 / 20 分钟 / 每文件 60 秒上限均未扩大。

检查包括源 size/MD5、本地 SHA-256、真实贴图文件头、glTF 外部依赖闭包、buffer 长度、bufferView/accessor 范围、有限数值和三角索引。缺文件、损坏缓冲区、路径越界三个负例拒绝。原始请求账、固定清单、可复查命令、检查范围和限制见 [I20-A 报告](../evidence/universe-I20A/report.md)。这些是文件/结构检查，不是完整 glTF conformance、UE 导入、渲染或性能检查。

Act：请求独立审查后集成当前输入；D3 从固定 index SHA 出发，导入为有明确资产身份/slot 的持久 UE Content，补齐 Alpha 和 PBR 接线，冻结新 profile；D4 再检查真实 Metal 图像、原子 HUD/画面切片和 authority 只读。保留原有未通过门及 Dot 候选交接状态。
