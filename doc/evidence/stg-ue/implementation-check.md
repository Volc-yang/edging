# G2-UE 实现检查（2026-11-01）

输入：`48cf26d`、`doc/fixtures/abstract_seed_genesis_v1.md`。本卡仅新增 UE C++ 的抽象因果观察解析器、代理 Actor、GameMode/Controller 和定向自动化测试；没有运行组合 worker、Genesis 或真实 Metal 场景。

## 实际检查

- UE 5.8.3 / CL 58210709 发布版 `EdgeWorldHostEditor Mac Development` 构建成功。包含新 Runtime parser、Host Actor/GameMode 和 UHT 生成类。
- NullRHI `edgeWorld.CausalObservation.StrictIdentity` 成功，进程退出码 0。有效 tick 1 fixture 被解析；错 world、水位、因果边、派生值范围、phase 与物理 hash 的负例被拒绝。完整原始日志在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/stg-g2-ue-nullrhi.log`，SHA256 `f5ad741fdfb621ad6d296063316a4b36e1bdf25e2d07ab42a78cb7ac0ffded4b`。
- `git diff --check` 通过。自动生成的 `DefaultInput.ini` 未纳入提交。

审查修复：Status/Advance 的 head 先进入待验证槽；只有对应 Observe 样本的 world/tick/revision、Genesis 配置、当前 checkpoint 和 state/event 摘要均通过后才发布为本地最新 head。拒绝样本保留旧代理及旧 head，阻止下一次 Advance；`R` 可重新读取 Worker head 对账。定向测试覆盖错误配置/检查点/state/event 摘要不发布 head。Head 的四个摘要均要求 64 位十六进制字符。

审查修复后再次运行 UE 5.8.3 Editor 构建成功；NullRHI `edgeWorld.CausalObservation.StrictIdentity` 成功、退出码 0。新原始日志 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/stg-g2-ue-nullrhi-review.log`，SHA256 `467a55a32b24d19990df350743a8d0ca36616696e88e6124a0e4e4e21a660f1b`。新增拒绝检查确认错误 Genesis 配置或 checkpoint 不会发布待验证 head，下一次推进保持阻塞，匹配的 Observe 才提交本地 head。

最终复核又将 Observe 的 `state_hash` 与 `event_hash` 绑定到待验证 head；当前最新切片的历史重读也核对这两个摘要。UE Editor 构建再次成功，NullRHI 测试含错误 state/event 摘要的拒绝用例并通过，进程退出码 0。原始日志 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/stg-g2-ue-nullrhi-final.log`，SHA256 `90103cc4ce4ee987675127f896e6dbcec03803e473f9561b8060bca6b4af3d64`。

## 开放门

新 GameMode 由 `?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode` 选择；通过 `EDGEWORLD_CAUSAL_PYTHON` 与 `EDGEWORLD_CAUSAL_WORKER` 连接单一权威进程，状态目录在本项目 `Saved/EdgeWorldCausal/stg-demo`。此启动/连接路径尚未与组合 worker 实测。Metal 三时刻画面、输入焦点、权威只读哈希、错误响应时 Actor 保持、性能和产品视觉标准留给 G3/G4。当前 BasicShapes 节点/边是抽象因果图的技术代理，不是最终世界外观。

本 UE 技术切片最多呈现 10,000 个发展节点；解析器超过该数量会拒绝样本，避免无界创建 Actor。WASD/QE/方向键均为单次按键移动一步，不是持续按住移动。生产级规模与持续导航另立任务。
