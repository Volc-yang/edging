# CHAOS-REALISM-01 写实样区方案树

状态：用户已要求执行，并允许世界渲染产物放在 `DevSSD`。固定基线 `6697512`；统筹分支 `codex/chaos-realism-01`。目标是 UE5.8.3 发布版上的**森林—河泽—海岸写实样区**，连接通往城市的路线；这是视觉纵切，不宣称六类完整世界已达到最终美术质量。世界状态仍由现有 Chaos Worker 提交，UE 只读投影，O1 仍仅显式触发。

## 存储与验收边界

- Git 仓库保留 C++、配置、配方、小型证据索引和来源记录；不提交大型贴图、缓存、截图、视频或 UE 二进制资产。
- `DevSSD` 实际挂载为 `/Volumes/DevSSD`（区分大小写），可用约 722 GiB。专用目录 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/`，分 `Assets/`、`Renders/`、`Logs/`、`Cache/`。所有任务只在该专用目录下创建文件，不覆盖既有 DevSSD 内容。任务各用独立子目录，最终证据由主任务汇总。
- 不自动下载许可不明的外部资产；优先 UE 5.8.3 自带 Landscape、Water、PCG、Foliage、Nanite、Lumen 与可确定生成的本地素材。Water 插件当前位于 UE Experimental 路径，实际可用性需先构建/运行验证。
- 阶段门：真实 Metal 画面能辨认连续地形、森林、河泽、海岸及路线；同一 world/tick/watermark 的观察前后权威 manifest/state/event 不变；记录画面、来源、帧时间或明确未测。只有已执行的检查可标通过。

## 方案树

```text
R0 森林—河泽—海岸写实样区
├── P1 资产/插件/DevSSD 可行性与视觉标准 [只读研究+小型报告]
├── T1 UE 地形/水体样区 [实现，依赖 P1 接口裁决]
├── E1 森林/河泽生态呈现 [实现，依赖 T1 场景坐标接口]
├── L1 材质、天空与光照 [实现，可与 E1 并行，独立路径]
├── V1 Metal 画面、只读与帧时间独立核查 [依赖 T1/E1/L1]
└── A1 主任务审查、集成、复盘、提交 [依赖 V1]
```

### P1 可行性与接口冻结

只写 `doc/chaos_realism_01_feasibility.md`。清点 UE 5.8.3 内置插件、现有项目资产、DevSSD 目录及授权来源；提出地形与水体可实现的最小范围、T1/E1/L1 不重叠源码与资产命名、镜头/坐标、预算与真实画面判定。不得改实现或下载资产。主任务审查后冻结接口，才派实现任务。

### T1 地形与水体

新建 `ChaosRealismTerrain*` 专属源码与对应说明；不改 Worker、InitialWorld、树/Genesis、UE 引擎源码。用 UE 发布版能力从固定 seed7 地理输入构造森林→河泽→海岸连续样区，确保水体/道路不被模板 Landscape 遮挡。输出真实运行画面或明确失败证据。大型中间资产进 DevSSD `Assets/Terrain`，渲染进 `Renders/Terrain`。

### E1 生态

新建 `ChaosRealismEcology*` 专属源码/配方，消费 T1 冻结的坐标与地形采样接口；按区域确定性放置树木、草、河泽植物代理，说明树种差异尚属实验表现。不得推进 Worker。大型资产进 `Assets/Ecology`。

### L1 材质与天空

新建 `ChaosRealismLook*` 专属源码/配方，使用 UE 发布版 PBR、Sky Atmosphere、云、曝光和光照；不改 T1/E1 文件。大型贴图/预览进 DevSSD `Assets/Look`、`Renders/Look`。不得把 BasicShapes 改色称为最终写实。

### V1 独立验收

只写 `doc/evidence/chaos-realism-01/review.md` 和小型索引。单 UE Metal + 单 Worker、隔离状态目录，固定 tick 0/1 镜头采图；记录截图 SHA、进程/构建、world/tick/watermark、manifest/state/event、资产来源与实际帧时间。真实画面不达标时保留失败证据，不把编译或 NullRHI 当视觉通过。

### A1 收尾

逐 PR 审查、CI 和本机证据；集成到统筹分支，更新 backlog/register 并提交。主工作区原有未提交改动与旧 PIE worktree 不触碰；不将本轮自动合并到 `feature/edge-world`。
