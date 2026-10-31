# PDCA-CHAOS-02 / C4 地形遮挡修复后独立 Metal 复测

日期：2026-10-28。结论：**固定 seed7 的六类场所代理与城市至海洋路线可辨门通过**。V1R 消除了上一轮 C3 在森林、河泽、海洋和路线上的模板 Landscape 遮挡；这仍是 BasicShapes 的技术代理，**不代表“近乎完美”的最终世界美术质量**。逐镜头命令回执、权威状态前后快照和截图 SHA 在同目录 `visual-retest-index.jsonl`；原始大图、ack、脚本与完整日志在主工作区 `engine_platforms/unreal/EdgeWorldHost/Saved/ChaosC4Evidence/`，未纳入 Git。

## 固定输入与运行

- 基线 `a187366`，包含 V1R PR #11；UE 5.8.3 / CL 58210709 `EdgeWorldHostEditor Mac Development` 构建成功。全新单 UE Metal RHI 进程 PID 14589，单 `origin_worker.py` PID 14875；进程结束后均退出。状态目录仅为本 C4 worktree 的 `engine_platforms/unreal/EdgeWorldHost/Saved/EdgeWorldChaos/chaos-demo`，没有复用 C3/Seed→Tree/Genesis。
- `models/chaos/initial_world_seed7.json` 原始 SHA-256 运行前后均为 `0fa198a9cec8a3cc9b4c5aabba02367e68e05b5e34b144df75882123c8bde629`；P0 canonical hash `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3`。日志确认 Metal、`chaos-demo`、六类 place、`river-1` 与 `origin-route-1`，启动 tick 0 Observe 和显式 O1 后 tick 1 Observe。
- 启动时日志 `Chaos template landscape hide complete: map=/Engine/Maps/Templates/OpenWorld count=45`，即初始模板 Landscape 45 个对象隐藏。随着相机移至局部区，日志另有 **39 次** `Chaos streamed template landscape hide: count=1`，对应流入关卡 Landscape 再次隐藏。启动后 tick 0 截图 `chaos_tick0_after_stream.png` 可见海面、森林、河泽、城市/原野代理和路线，没有旧的大块灰褐地形；七镜头与额外总览及迟后总览均未见其重新遮挡。
- 原始 Metal 日志 `chaos_c4_metal.log` SHA-256 `46335520e1aca07d9b7c468d6b0c09b4ba5f4d5907fef4dfec4171029cb65618`；原始 Saved `retest.jsonl` SHA-256 `1343f7c8f4b18e0f0e61087f9622dd823fea89e57d02f801746ce46680338131`。窗口级 `screencapture -l 52383` 采图，后台运行未要求用户输入；机器当时只检测到内建显示器。

## 命令与权威摘要

序号 1 为**显式** `reveal`：ack `applied=true`，之后日志出现 committed tick 1；manifest 原始 SHA `a889d9400fcbada2e6aafb977665f12a0d227fc700bac6ac4123fdd45dabb36d` → `5b9311df6cf84dfa36fba8f961566367a91a02c49ae1da7a58c2ffac4d381057`，state `e2030df396ae7f1f5c1466e475ac467d09daf397be52d3b983386402d88f3d0f` → `d6b6ec5b7543fe9dfa486708f4013425b4a63c9c734ec8da3720552c552cbb8c`，event 全零 → `3b7a8899f219bde5207c2e754391b54c9212e56b04dece2b4acbb8aa4450548f`；tick/revision/watermark 0→1，commands 0→1。

序号 2–8 为 V1 文档的六个局部镜头和路线总览；序号 9 是补充的高空总览 `(50000,50000,125000)`、FOV 65，使城市到海洋的整条路线同帧可见。每项 camera ack `applied=true` 且回读位置/FOV；每项前后解析的 manifest 原始 SHA、state/event hash、world/head tick/revision/watermark/phase、commands 均**逐项相同**，一直是 tick/revision/watermark 1、commands 1。每次镜头切换后等候 3 秒再采图，包含 World Partition 流入窗口。原始截图与快照由同一 seq 紧邻记录，图像自身没有内嵌摘要文字。

## 逐区独立目视裁决

| 固定镜头/图 | 复测可见事实 | 裁决 |
| --- | --- | --- |
| `city_tick1.png` | 方体建筑、中央高塔及连接路线清楚；相邻田块可见 | 代理可辨 |
| `wildland_tick1.png` | 土色场所边界、中央高峰与周围小岩锥完整露出 | 代理可辨 |
| `plain_tick1.png` | 黄色田块条带与穿越路线可辨 | 代理可辨 |
| `forest_tick1.png` | 整片绿色地块、规则树阵、横穿路线与河道可见 | 代理可辨；C3 遮挡已消除 |
| `river_marsh_tick1.png` | 青绿色水面、苇秆/岛块、路线桥和河道交接可见 | 代理可辨；C3 遮挡已消除 |
| `ocean_tick1.png` | 蓝色大面积水域与多条浅色浪带可见 | 代理可辨；C3 遮挡已消除 |
| `route_overview_tick1.png` 与 `route_full_tick1.png` | 近总览看路线/河道穿过森林河泽；补充高空图同帧可追踪 city→plain→forest→river-marsh→ocean 的黄色路线和 forest→marsh→ocean 的蓝色河道 | **代理连续可见**；迟后 `route_full_late_tick1.png` 仍未被流入地形重新遮挡 |

各图 SHA-256 与相机 ack、tick 1 的逐项摘要见 `visual-retest-index.jsonl`。补充迟后图 `route_full_late_tick1.png` SHA-256 `773708534b189338489d23e86a8f0c9122e1ff67e7ddbea7327e688456d85982`，其后最终 manifest/state/event/head 仍为 tick 1 黄金值。该复测确认**固定模板地图、固定 seed7 与当前单机 Metal 条件**下六类 BasicShapes 代理可逐区辨认、路线和河道可见；不证明真实地形生态、资产质量、跨平台视觉一致性或其他地图的遮挡处理。D3/D4 初态文件双次读取竞态仍未消除，macOS canonical hash 不代表跨平台通过。
