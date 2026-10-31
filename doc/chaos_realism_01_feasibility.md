# CHAOS-REALISM-01 / P1 可行性与接口提案

日期：2026-10-31。基线 `72b25d8`。本报告是**只读调查和实现提案**，没有构建、启用插件、导入资产或产生 Metal 画面。实施接口由统筹任务审查后冻结。

## 已核实的环境

| 项目 | 本机证据 | 实施含义 |
| --- | --- | --- |
| UE 安装 | `/Users/Shared/Epic Games/UE_5.8/` 含 `Engine/Source/Runtime/Landscape/Classes/Landscape.h`、`LandscapeProxy.h`、`Engine/Classes/Components/SkyAtmosphereComponent.h`、`VolumetricCloudComponent.h`、`Runtime/Foliage/Public/InstancedFoliageActor.h` | 发布版已有地形、植被实例、天空与云组件；源码存在不等于项目构建或 Metal 成功。 |
| PCG | `Engine/Plugins/PCG/PCG.uplugin` 声明 `EnabledByDefault=true`、`IsBetaVersion=false`，含 Runtime `PCG` 模块；项目 `.uproject` 未显式列它 | 可评估 PCG 散布；先由 Editor 构建和单样区运行证明。首轮也可用稳定 seed 的 `HISM` 实例作可控回退。 |
| Water | `Engine/Plugins/Experimental/Water/Water.uplugin` 声明 `EnabledByDefault=false`、`IsExperimentalVersion=true`，依赖 Landmass/Niagara；安装含 `GerstnerWaves_Ocean.uasset` 与 shoreline 内容 | 作为可选实验分支。先在隔离项目副本启用、构建、Metal 运行和水岸线截图。不能把插件文件存在当兼容性证据。失败时用自有水面网格/PBR 材质及河道曲线回退，保留 Water 阶段门未通过。 |
| Landmass | `Engine/Plugins/Experimental/Landmass/Landmass.uplugin` 标为 Beta | 若 Water 需要其依赖，须同一隔离构建验证；不修改引擎。 |
| Nanite / Lumen | UE 引擎渲染能力存在，但本项目 `Config/DefaultEngine.ini` 未配置它们，项目也无 Nanite 网格 | 只作为样区可选渲染设置；需要 Metal 日志、设置回读、画面及帧时间证据。没有网格资产时 Nanite 不构成真实收益。 |
| 项目资产 | `EdgeWorldHost.uproject` 仅显式启用 `EdgeWorldRuntime`，Git 项目无 `Content/` 资产；场景代码加载 `/Engine/BasicShapes/{Cube,Cone,Cylinder}`。`/Volumes/DevSSD/Unreal/MarketplaceVault` 为空；另一个 `EdgeWorldUE` 项目 Content 为空 | 当前没有可合法归属且达到写实标准的树木、地表、岩石或建筑素材。不能把 BasicShapes、插件图标、Editor 工具资产或另一个项目当最终美术资产。 |
| DevSSD | `/Volumes/DevSSD` 挂载，约 954 GiB 总量、722 GiB 可用；专用 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/{Assets,Renders,Logs,Cache}` 已存在、属当前用户 | 大文件可放专用目录。此调查未写入 DevSSD。不要移动或覆盖既有 `EdgeWorldUE` 项目。 |

资产许可边界：本轮仅计划在安装版 UE 内引用其随附内容进行本地原型验证；本报告未审查具体 Epic 许可条款，不建议复制 Engine 内容到 Git 或独立再分发。没有发现已授权的外部写实植被/地表资产；若采购或下载 Megascans/Fab，应另记来源、许可版本、取得日期、允许使用范围和资产 hash，未获得这些材料前不要纳入项目。

## 固定地理输入与最小样区

`models/chaos/initial_world_seed7.json` 为唯一地理输入，原始 SHA-256 `0fa198a9cec8a3cc9b4c5aabba02367e68e05b5e34b144df75882123c8bde629`；世界 `chaos-demo`，范围 `[0,0,100000,100000]` cm。`forest-1` 范围 x=30000–60000/y=30000–60000，`river-marsh-1` x=50000–70000/y=30000–50000，`ocean-1` x=70000–100000/y=0–100000；`river-1` 为 `(40000,55000)→(60000,40000)→(80000,40000)`；`origin-route-1` 为 `(15000,15000)→(35000,20000)→(45000,40000)→(60000,40000)→(80000,40000)`。这些是权威输入中的平面坐标，不应被视觉任务改写。

建议样区实际几何覆盖 x=25000–90000、y=20000–65000 cm，保留到城市路线的入口，视觉焦点为 forest→marsh→ocean。高度、海平面、坡度和植被密度是**非权威呈现参数**，由 T1 给出确定性采样 `HeightAt(x,y)`；海岸线须与 ocean 的 x≥70000 区域接合。若采用 Editor 生成 Landscape，地形 `.uasset` 仅保存在 DevSSD 隔离的 UE 项目副本，Git 保存生成配方/输入 hash/资产索引；运行使用该副本，不要求仓库工作树包含大二进制资产。运行时加载资产方式及 cook 可行性需 T1 实测，不能仅靠软链接假定可移植。

## 文件与接口所有权提案

1. **T1 地形/水体**拥有新 `ChaosRealismTerrain*` 源文件、`doc/chaos_realism_01_terrain.md` 和 DevSSD `Assets/Terrain/`、`Renders/Terrain/`。先做连续高程与海岸/河道，再在隔离副本试 Water；若失败走水面网格回退。向 E1 暴露只读 `HeightAt(FVector2D)`、`NormalAt(FVector2D)`、`WaterMaskAt(FVector2D)`、`SlopeAt(FVector2D)` 或等价 `FChaosRealismSurfaceSample`。所有权仅 T1；不得改 `ChaosWorldActor.*`、Worker 或 `InitialWorld`。T1 提交 API 后 E1 才实现。
2. **E1 生态**拥有新 `ChaosRealismEcology*` 源文件、`doc/chaos_realism_01_ecology.md` 和 DevSSD `Assets/Ecology/`、`Renders/Ecology/`。使用 T1 只读表面采样和固定 seed7 分布森林/河泽植物；如无授权写实网格，先用多层程序化枝叶或 HISM 代理，报告视觉未达写实门。E1 不改 T1 或场景 GameMode。
3. **L1 外观/光照**拥有新 `ChaosRealismLook*` 源文件、`doc/chaos_realism_01_look.md` 和 DevSSD `Assets/Look/`、`Renders/Look/`。仅创建天空、太阳、环境光、曝光和材质参数/本地生成贴图；与 T1/E1 同时工作，不改其文件。材质引用应作为只读句柄由统筹在唯一组装入口绑定，避免两个 agent 改同一 GameMode。
4. **主任务组装**拥有唯一 `ChaosRealismGameMode*` 或 `ChaosRealismWorldAssembler*`，在 T1/E1/L1 的接口已审查后连接三者与现有只读 Chaos Worker。现有 `ChaosObservationGameMode.*`、`ChaosWorldActor.*` 与 `EdgeWorldJsonlClient.*` 由主任务统一裁决；默认不改。三项实现不得各自改 `.uproject`、`Build.cs`、`DefaultEngine.ini`；插件启用和模块依赖由主任务在集成阶段一次性处理并留构建证据。

所有新类名带 `ChaosRealism` 前缀。共享空间使用 Unreal cm 与现有 `InitialWorld` XY，不做坐标交换或缩放。建议镜头：森林 `(25000,17000,12000)→(46000,44000,1200)`；河泽 `(47000,18000,9000)→(61000,40000,100)`；海岸 `(62000,18000,14000)→(80000,40000,0)`；高空总览 `(50000,50000,100000)→(58000,40000,0)`。它们是**待 Metal 调整的起始镜头**，不是验收已通过的相机位。

## 建议的阶段门与预算

先限定 **650×450 m** 样区（65000×45000 cm），避免把 1 km 世界扩张成完整星球。初版资产上限建议 10 GiB（源/导入合计）、单次渲染/日志上限 5 GiB、GPU 峰值和实际帧时间由 V1 记录后再定预算；这些是暂定工程上限，不是已批准性能目标。避免让缓存自动跨越 DevSSD 专用 `Cache/`；UE 默认全局 DDC 仍在用户目录，改向 DevSSD 需明确参数或配置并实测。

V1 独立验证必须包含：UE 5.8.3 Metal 真 RHI 和单 UE/Worker PID；固定输入 raw/canonical hash；tick 0/1 对应画面；森林、河泽、海岸及通城路线至少各一固定镜头；同一镜头截图可辨连续高程、水岸衔接、不同群落密度和路线；每次仅相机/渲染操作前后 manifest 原始 SHA、state/event/head 相同；唯一显式 O1 的前后摘要变化。帧率要采实际渲染帧时间分布（例如 Unreal Insights/CSV profiler 的 GPU/CPU 帧或引擎统计日志），与 `max_fps` 设置回读区分。截图/日志/性能原始数据放 DevSSD `Renders/V1`、`Logs/V1`，Git 只存小型索引与 SHA。若只有程序代理树/纯色地表，应记“技术可见”，**写实视觉门未通过**。

## 风险与裁决请求

- **资产缺口最大**：发布版渲染能力本身不能替代高质量地表、植被、岩石与城镇资产。当前应先实现可接入资产的地形/生态/材质链路，同时把“写实外观”状态保持开放。若要本轮真正验收写实，需要用户可用且授权明确的素材来源或另立资产制作任务。
- **Water Experimental**：只可作为可撤销试验；其项目启用、运行时生成、Landscape carve、Metal 性能都需实测。失败时保留 T1 地形/水面网格方案，不改 UE 源码。
- **运行与存档**：已有用户启动的 UE Chaos 进程不可在调查中关闭。T1/V1 启动前须检查 PID，使用独立 DevSSD 项目副本/隔离 `Saved` 状态目录；不得两个 Worker 写同一个 `world.json`。
- **双次读取**：现有 D3/D4 分开读取同一 `InitialWorld` 的竞态未由视觉项目解决；固定只读输入可降低验收风险，后续仍需接口修复。
- **回退/可移植**：DevSSD 缺席时仅 Git 中代码/配方可用，大型生成资产及画面不可复现；报告需记录路径、文件 hash、UE 版本和生成命令，后续才考虑资产归档或 cook/package。
