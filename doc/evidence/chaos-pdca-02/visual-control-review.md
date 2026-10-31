# PDCA-CHAOS-02 / C3 Metal 呈现与权威隔离独立核查

日期：2026-10-27。结论：**技术控制/只读门通过，六类场所及路线视觉门未通过**。本报告只审查固定 seed7 的 CHAOS→ONE 代理。逐项原始记录见同目录 `matrix.jsonl`；大型图、控制脚本、ack 与完整日志在主工作区 `engine_platforms/unreal/EdgeWorldHost/Saved/ChaosC3Evidence/`，未纳入 Git。

## 固定运行

- 源码基线 `dffaccc`（已集成 H1/V1）。UE 5.8.3 / CL 58210709 `EdgeWorldHostEditor Mac Development` 构建成功。一个真实 Metal RHI `UnrealEditor.app` PID 45422 和一个 `origin_worker.py` PID 45733；运行后两者已退出。日志含 `rhiname="Metal"`、六个 place ID/坐标、`river-1`、`origin-route-1`、`places=6`、tick 0/1 committed Observe 与 `ChaosValidation` 命令回执。
- 输入 `models/chaos/initial_world_seed7.json` 原始 SHA-256 `0fa198a9cec8a3cc9b4c5aabba02367e68e05b5e34b144df75882123c8bde629`（运行前后相同）；P0 canonical hash `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3`。隔离状态目录仅为 C3 worktree 的 `Saved/EdgeWorldChaos/chaos-demo`，不复用 Seed→Tree/Genesis。
- 窗口级 `screencapture -l 52303` 采图；机器当时只检测到内建显示器，后台启动并未要求用户操作。第一次预检把 `?game` 拼入项目文件路径，启动器拒绝、未产生 Worker/状态，**不纳入有效运行**；随后用独立参数重启为上述单 UE+单 Worker。
- 原始日志 `chaos_c3_metal.log` SHA-256 `58156695e9ba52ce95500c437c5f0679765fe5f92a662b701fe2d28da3dff811`；Saved 原始 `matrix.jsonl` SHA-256 `63102dfe3ba4e919c0c2cb28aaedb0ac10bcb7519cc69b09d4e996a9c20f7b04`。每一行保留 seq/action/ack、前后 manifest 原始 SHA、state/event hash、world/head tick/revision/watermark/phase、command 数、异步观察日志是否增加及截图 SHA。采样器在每次 ack 后读取同一 `world.json`；Observe/reveal 另等对应 committed observation 日志。

## 逐项权威矩阵

| seq | 实际操作及回执 | 前后权威结果 |
| --- | --- | --- |
| 1 | camera 总览位置/FOV 65，`applied=true` 且回读实际 transform | manifest/state/event/head 不变 |
| 2 | `max_fps=30.0`，`applied=true` | manifest/state/event/head 不变；这是引擎帧率上限设定，**未测实际渲染 cadence** |
| 3–4 | UE `world_paused=true` → `false`，均 `applied=true`，暂停时仍收到 resume ack | 每项 manifest/state/event/head 不变 |
| 5–6 | 世界之灵边界显隐 true → false，均 `applied=true`，两图已采 | 每项 manifest/state/event/head 不变；组件实际显隐有 ack，画面差异仍属于代理呈现 |
| 7 | tick 0 历史 Observe，ack dispatch 且 committed tick 0 日志增加 | manifest/state/event/head 不变 |
| 8 | 唯一显式 `reveal`，ack dispatch 且 committed tick 1 日志增加 | manifest `a889d940…d36d` → `5b9311df…1057`；state `e2030d…3d0f` → `d6b6ec…bb8c`；event 全零 → `3b7a88…0548`；tick/revision/watermark 0→1，commands 0→1 |
| 9–12 | tick 1、历史 tick 0、tick 1、重复 tick 1 Observe；每项 ack + 对应 committed 日志 | 每项 manifest/state/event/head 不变 |
| 13 | 重复 `reveal`，`applied=false`、`O1 unavailable` | manifest/state/event/head 不变，commands 仍 1 |
| 14–20 | 六类局部镜头及路线总览，位置/FOV 均回读且截图 | 每项 manifest/state/event/head 不变 |

20 项都有独立 pre/post 解析；除 seq 8 外，原始 manifest SHA 与 state/event/head 均逐项相同。tick 0 状态为 SHA `e2030df396ae7f1f5c1466e475ac467d09daf397be52d3b983386402d88f3d0f`，event 全零；tick 1 状态为 `d6b6ec5b7543fe9dfa486708f4013425b4a63c9c734ec8da3720552c552cbb8c`，event 为 `3b7a8899f219bde5207c2e754391b54c9212e56b04dece2b4acbb8aa4450548f`。这些结果证明本次单进程提交 manifest 的隔离；不证明跨进程 writer 安全或未采样的内存状态。截图与状态绑定依赖同一进程日志、seq 顺序及紧随 ack 的状态快照，图片本身没有内嵌 hash。

## Metal 逐区视觉判定

截图均为同一 Metal 窗口，局部镜头来自 V1 文档的固定位置和焦点，截图 SHA 见 `matrix.jsonl`。tick 0/1 总览 `overview_tick0.png` / `overview_tick1.png` 可见城市/原野/海面及 O1 边界变化；独立原始 `chaos_tick0_metal.png` SHA `e1ca5fd8225248dd799c11c15f8ce70c8b400291506b9871679c5af5902087ac`。局部检查：

| 区域/路线 | 可见事实 | 裁决 |
| --- | --- | --- |
| city | 建筑方体、中央高塔可辨；旁边原野田块侵入镜头 | 有限代理可辨 |
| wildland | 地形起伏及中央锥峰可辨，峰体与地形贴合不佳 | 有限代理可辨 |
| plain | 黄色田块条带可辨，但部分条带似浮在灰褐地形上 | 有限代理可辨，质量差 |
| forest | 固定镜头大部分是灰褐起伏地形，只有少数绿色树尖在边缘 | **未通过**逐区可辨 |
| river_marsh | 固定镜头几乎全是灰褐地形，看不到河泽水面、苇岛 | **未通过** |
| ocean | 固定镜头几乎全是灰褐地形，看不到海面浪带 | **未通过** |
| origin-route-1 / river-1 | 总览可见部分色带，但中央地形大块覆盖路线及区域；无法目视确认 city→plain→forest→marsh→ocean 连续路线或河道连海 | **未通过**连贯性 |

构造日志列出六类 place 和路线数据，但实际画面表明地形与局部 place/路线代理存在严重遮挡/层级冲突。此缺陷属于 V1 场景表现，应由实现所有者另行修复后重新独立复测；C3 不修改实现源码。当前仍是 BasicShapes 代理，明显不达到“近乎完美”的初始世界美术目标。

## 开放边界

实际 Metal rendered FPS/cadence 未有可靠采样，只确认引擎 `max_fps` 设置为 30；若要判帧率变化下的渲染性能/节奏门，需增加帧时间计量。D3/D4 双次读取初态文件的竞态仍在，本次输入固定且 raw SHA 前后相同，未消除架构风险。macOS canonical hash 的实现不证明跨平台。真实 RHI 下相机/暂停/显隐/历史 Observe **对提交权威状态只读**这一有限门通过；六类场所与路线完整视觉门保持未通过。
