# G2-UE 实现检查（2026-11-01）

输入：`48cf26d`、`doc/fixtures/abstract_seed_genesis_v1.md`。本卡仅新增 UE C++ 的抽象因果观察解析器、代理 Actor、GameMode/Controller 和定向自动化测试；没有运行组合 worker、Genesis 或真实 Metal 场景。

## 实际检查

- UE 5.8.3 / CL 58210709 发布版 `EdgeWorldHostEditor Mac Development` 构建成功。包含新 Runtime parser、Host Actor/GameMode 和 UHT 生成类。
- NullRHI `edgeWorld.CausalObservation.StrictIdentity` 成功，进程退出码 0。有效 tick 1 fixture 被解析；错 world、水位、因果边、派生值范围、phase 与物理 hash 的负例被拒绝。完整原始日志在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/stg-g2-ue-nullrhi.log`，SHA256 `f5ad741fdfb621ad6d296063316a4b36e1bdf25e2d07ab42a78cb7ac0ffded4b`。
- `git diff --check` 通过。自动生成的 `DefaultInput.ini` 未纳入提交。

## 开放门

新 GameMode 由 `?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode` 选择；通过 `EDGEWORLD_CAUSAL_PYTHON` 与 `EDGEWORLD_CAUSAL_WORKER` 连接单一权威进程，状态目录在本项目 `Saved/EdgeWorldCausal/stg-demo`。此启动/连接路径尚未与组合 worker 实测。Metal 三时刻画面、输入焦点、权威只读哈希、错误响应时 Actor 保持、性能和产品视觉标准留给 G3/G4。当前 BasicShapes 节点/边是抽象因果图的技术代理，不是最终世界外观。
