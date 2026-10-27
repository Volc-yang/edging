# ChaosWorld 静态投影（D3）

这是 `doc/chaos_origin_contract.md` 的六类场所 UE5 发布版**静态视觉代理**。它不连接 Worker、不执行 O1、不推进逻辑时间，也不改变现有树演示的默认 GameMode。

## 启动入口

使用独立 GameMode URL 覆盖默认树演示，例如在项目的独立游戏启动命令中指定：

```text
/Engine/Maps/Entry?game=/Script/EdgeWorldHost.ChaosGameMode
```

`AChaosGameMode::StartPlay` 默认使用 P0 固定 `chaos-demo` fixture。可追加 `-ChaosWorldData=/absolute/path/to/initial-world.json` 载入 D1 的清单；`-ChaosInitialHash=<sha256>` 只是调用方提供的预期值，**D3 不核对规范 JSON 哈希**。D4 必须把它与 Worker 的 `initial_manifest_hash` 校对后才能把场景与 Observe 结果绑定。空/无效清单会报错并销毁投影 Actor。

`AChaosWorldActor::BuildFromInitialWorldJson(Json, ExpectedHash, Error)` 可由后续观察 GameMode 使用。`SetWorldSpiritVisible(true)` 只显示整片区域的视觉边界；D4 必须先验证 tick 1/watermark 1 的已提交 `ONE` 样本，才能调用它。Actor 没有 Tick。D4 可继承 `AChaosGameMode`，通过受保护的 `ChaosWorld` 访问投影，不需修改树演示入口。

## 场景与审查边界

- 一块连续地面承载城市、蛮荒、原野、森林、河泽、海洋。固定俯瞰镜头大致沿城市→原野/森林→河泽→海洋方向；蛮荒在镜头另一侧。水路与观察路线按 P0 fixture 的 `polyline_cm` 绘制。
- 几何由 UE `/Engine/BasicShapes` 的 Cube、Cone、Cylinder 与可调颜色材质组成；无外部美术、二进制地图、实验性 Water/Landmass 插件或 UE 源码修改。场所多边形目前用外包矩形作视觉代理，`elevation_cm` 未用于高程网格。
- 这个代理只能核查初态字段接线、六类场所可辨认和连续路线。它尚未达到“近乎完美”的美术目标；真正的 RHI 画面、可游览性、帧率与观察只读证据由 C2 独立验收。编译成功不能替代该阶段门。
