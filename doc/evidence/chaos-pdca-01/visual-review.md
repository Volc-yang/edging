# PDCA-CHAOS-01 / C2 真实画面与只读隔离核查

日期：2026-10-27。结论：**部分通过**。UE 5.8.3 Metal RHI 的同一运行中，CHAOS/tick 0 与 ONE/tick 1 的画面、Worker 往返及显式 O1 有证据；历史/重复 Observe、重复 Space 和进程挂起/恢复没有改写权威 manifest。相机参数变化、帧率变化、UE 游戏内暂停、六类场所的完整连贯性以及“近乎完美”的视觉质量未通过本轮阶段门。

## 固定输入与运行边界

- 实现基线：迭代集成分支 `2bbc3aa`，含 P0–D4 与 C1；本任务只写此报告。UE 5.8.3 安装版构建 `EdgeWorldHostEditor Mac Development` 和 `EdgeWorldHost Mac Development` 均成功。
- 初态：`models/chaos/initial_world_seed7.json` 原始 SHA-256 `0fa198a9cec8a3cc9b4c5aabba02367e68e05b5e34b144df75882123c8bde629`；规范摘要 `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3`。运行期间原始 SHA 未变。Worker 状态目录仅为 C2 工作树的 `engine_platforms/unreal/EdgeWorldHost/Saved/EdgeWorldChaos/chaos-demo`，未复用树/Genesis 目录。
- 有效运行：一个 `UnrealEditor.app` 进程 PID 97664（`-game`，窗口移到第二显示器），一个 `origin_worker.py` 子进程 PID 97875。日志确认 `rhiname="Metal"`、Apple M4 Pro、`ChaosObservationGameMode`、`places=6` 和 tick 0/1 Observe；结束后两进程已退出。
- 启动环境：`EDGEWORLD_CHAOS_PYTHON=/usr/bin/python3`，`EDGEWORLD_CHAOS_WORKER=<C2 工作树>/engine/chaos/origin_worker.py`。项目参数为 `?game=/Script/EdgeWorldHost.ChaosObservationGameMode -game -ChaosWorldData=<上述 seed7 JSON> -ChaosInitialHash=<上述规范摘要> -windowed -ResX=1280 -ResY=720`。`UnrealEditor` 命令先委派到 `.app`，故 shell 返回码不代表渲染进程结果；以 PID、日志及窗口采图判断实际运行。
- 预检时曾误启动两个进程并指向同一 C2 状态目录；二者只到 tick 0，均已停止，**不纳入有效证据**。随后确认仅一个 Editor/Worker 组合，再执行以下 O1 和观察。原型无跨进程 writer lock，该预检不构成并发安全证据。

## 画面与权威状态

两张原始窗口截图（1348×820，含窗口边框）及完整运行日志保存于主工作区独立的 `engine_platforms/unreal/EdgeWorldHost/Saved/ChaosC2Evidence/`，不随 C2 工作树清理；大型文件未纳入 Git。

| 时点 | 画面文件 / SHA-256 | manifest 原始 SHA-256 | 权威摘要 |
|---|---|---|---|
| CHAOS，tick/revision/watermark 0 | `chaos_tick0_metal.png` / `59ea46d77a8fd56e338e75154c6cbf473ffe9e162d8d196a3417bf2e7917fb99` | `a889d9400fcbada2e6aafb977665f12a0d227fc700bac6ac4123fdd45dabb36d` | state `e2030df396ae7f1f5c1466e475ac467d09daf397be52d3b983386402d88f3d0f`；event 全零；commands 0 |
| 明确按一次 Space 后 ONE，tick/revision/watermark 1 | `one_tick1_metal.png` / `f641637e22d822c3bf787ca36a2c72bcd98f7586b61d8e3689b8466195388a7e` | `5b9311df6cf84dfa36fba8f961566367a91a02c49ae1da7a58c2ffac4d381057` | state `d6b6ec5b7543fe9dfa486708f4013425b4a63c9c734ec8da3720552c552cbb8c`；event `3b7a8899f219bde5207c2e754391b54c9212e56b04dece2b4acbb8aa4450548f`；spirit `spirit-597eac36f6d6c494`；commands 1 |

`chaos_metal_run.log` SHA-256 为 `f7cc74187cd08d015aab4b17ac49c67b522064fddff5d32b3515e9630b9b2592`。日志在 12:20:48 记 tick 0、12:23:42 记 tick 1，之后 12:24:26/27 记历史 tick 0/1；运行日志与 manifest 均指向 `chaos-demo` 和 seed7 规范摘要。图片只证明 Metal 画面及可见边界变化；没有截图内嵌状态文字，时间/摘要绑定依赖同一 PID 的日志和同步采集的 manifest。

## 只读操作矩阵

O1 后基准为 manifest 原始 SHA `5b9311df…81057`，state `d6b6ec5b…2cbb8c`，event `3b7a8899…4450548f`，tick/revision/watermark 均为 1。每项后直接读取同一 `world.json`；除截图外未写该状态文件。

| 操作 | 实测结果与裁决 |
|---|---|
| 按 `0` 历史 Observe，再按 `1` 当前 Observe | 日志分别新增 `observed committed tick 0/1`；两次后 manifest 原始 SHA 均与基准相同。通过。 |
| 再按 `1`，随后再按 Space | manifest 原始 SHA 仍与基准相同；head 和 command 数仍为 tick 1 / 1 条。重复观察和 ONE 以后 Space 不引发第二次 O1。通过。 |
| `SIGSTOP` 挂起 UE 进程约 2 秒，再 `SIGCONT` | 前后 manifest 原始 SHA 均与基准相同，Worker 保持运行。仅证明进程挂起/恢复，不冒充 UE 游戏内 Pause。 |
| 相机参数/位置、帧率、UE Pause/Resume | 尝试游戏控制台按键，但未观察到可靠的控制台命令执行证据；未验证。 |
| 世界之灵边界显隐 | `0 → 1` 历史观察让场景切换两种已提交状态；tick 0/1 截图可见浅色边界线差异，manifest 不变。仅此有限显隐操作通过；UE 任意组件显隐矩阵未验证。 |

## 场景审查与后续门

`InitialWorld` 数据列出 city、wildland、plain、forest、river_marsh、ocean 六类；UE 日志确认建造了 6 个 place。固定俯视镜头可辨海面、山地、少量树形、平原/城镇代理与一段线状边界，但河泽及连接路线在两张画面中不能独立辨清，也没有逐区走查证据。大范围地形和 BasicShapes 代理仍明显粗糙，不能称为近乎完美的初始混沌世界。C2 的 **Metal 可见/显式 O1/有限只读门通过，完整视觉质量、六类连贯性、相机/帧率/UE 暂停隔离门保持开放**。

建议下一轮提供可自动驱动的 UE 测试入口，以固定相机位和可记录的帧率/暂停/显隐操作重新采样，再逐区截图核验六类场所与路线。D3/D4 两次读取同一路径仍存在文件替换竞态；本轮固定文件 SHA 且运行期间未更改输入，但没有消除该架构风险。
