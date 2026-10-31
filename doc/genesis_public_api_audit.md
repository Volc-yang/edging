# Genesis World 1.4.3 公共 API 审计（P2）

日期：2026-10-10
状态：已完成 API 源码审阅与小型运行探针；仅限单自由刚体 / Metal PoC
基线：`203e632969b4c835c3c2b914a1becd03c7e6705c` (`codex/stage2-genesis-api`)
输入契约：`doc/phase1_4d_prototype_contract.md`

## 结论

可以去掉参考 PoC 中的私有访问 `scene._sim.set_gravity()`。Genesis World 1.4.3 暴露有文档的 solver 属性 `scene.rigid_solver` 和公开方法 `scene.rigid_solver.set_gravity(gravity, envs_idx=None)`。将参考调用改为：

```python
scene.rigid_solver.set_gravity((0.0, 0.0, gravity_z))
```

这是与重力规则最贴合的公开入口。`scene.sim` 也是公开的 `Scene` 属性，`scene.sim.set_gravity(...)` 在 1.4.3 中同样可用；它把值传播给所有启用且支持 gravity 的 solver。worker 仅驱动刚体重力时优先用 `scene.rigid_solver.set_gravity(...)`，避免无意改动同一 Genesis 场景中的其他求解器。

Genesis 的公开 `Scene.step(update_visualizer=True, refresh_visualizer=True)` 支持调用方显式步进；创建 scene 时传 `show_viewer=False` 并调用 `scene.step(update_visualizer=False, refresh_visualizer=False)` 可在无交互 viewer 情况下推进。公开的 `Scene.save_checkpoint(path)` 和 `Scene.load_checkpoint(path, show_viewer=False)` 支持保存和恢复 Genesis 场景状态。本次探针在同一进程中创建新场景并从磁盘 checkpoint 恢复；没有验证新 OS 进程重启、其他后端或复杂求解器。

Genesis 不提供 edgeWorld 逻辑时钟、规则版本、命令幂等或因果提交语义。Genesis checkpoint 是物理模拟状态的一部分，不等于 edgeWorld 世界事务记录。worker 应继续把逻辑 tick、规则/参数版本、下一 tick 待应用参数、command ID、revision/event head 和 Genesis 版本/配置写入自己的原子持久化记录。恢复后根据 edgeWorld 的下一条已提交规则重新应用参数，再执行固定步数。

## 版本与证据位置

| 项目 | 结果 |
|---|---|
| Distribution | `genesis-world==1.4.3` |
| Python | 3.12，隔离环境 `.venv-genesis` |
| Backend | Apple Metal (`gs.metal`) |
| 安装代码根目录 | `/Users/yangacan/edgeWorld/edge-world/.venv-genesis/lib/python3.12/site-packages/genesis/` |
| Scene 实现 | `engine/scene.py`：`step` 约 1060 行；`save_checkpoint` 1694 行；`load_checkpoint` 1710 行；`sim` 属性 1917 行；`rigid_solver` 属性 2005 行 |
| Simulator 实现 | `engine/simulator.py`：公开 `set_gravity` 约 514 行 |
| Rigid solver 实现 | `engine/solvers/base_solver.py`：公开 `set_gravity` 约 265 行（运行时类实现来自该 solver 家族） |

上表路径相对于安装包根目录。版本来自该环境的 `genesis_world-1.4.3.dist-info/METADATA`。包中的 `Scene.rigid_solver` 属性和 solver `set_gravity` 实现已核对；`set_gravity` 文档说明该方法接受 `(3,)` 或 `(n_envs, 3)` 重力向量，单位为 m/s²。

官方 API / 指南：

- [Scene API：step、save_checkpoint、load_checkpoint](https://genesis-world.readthedocs.io/en/latest/api_reference/engine/scene.html)
- [Simulator API：set_gravity](https://genesis-world.readthedocs.io/en/latest/api_reference/engine/simulator.html)
- [Genesis 约定：运行时重力修改与单位](https://genesis-world.readthedocs.io/en/latest/user_guide/configuration/conventions.html)
- [Checkpoint 与模拟状态指南](https://genesis-world.readthedocs.io/en/latest/user_guide/configuration/checkpoints.html)

官网 `latest` 文档可能随上游变化；精确到 1.4.3 的结论以隔离环境内已安装发行版源码与探针为准。没有找到/确认固定到 1.4.3 的 Read the Docs 版本 URL，故不将 `latest` 页面冒充为版本快照。

## API 分类

| 能力 | 1.4.3 API | 公开性 / 适用边界 |
|---|---|---|
| 初始化配置 | `gs.Scene(show_viewer=False, sim_options=gs.options.SimOptions(dt=..., gravity=...))` | 公开构造参数；配置初始 timestep 和 gravity。 |
| 配置对象 | `scene.options.sim.gravity` | 公开 `SceneOptions` 配置值；它描述场景创建配置，不是建成后用于实时改 solver state 的 runtime setter。不要靠修改该配置模型代替 solver API。 |
| 运行时重力（刚体） | `scene.rigid_solver.set_gravity(gravity, envs_idx=None)` | 公开 Scene solver 属性 + 公开 solver 方法；优先推荐给本 PoC。 |
| 运行时重力（全场景 solver） | `scene.sim.set_gravity(gravity, envs_idx=None)` | 公开 Scene 属性 + 公开 Simulator 方法；会作用到所有启用且支持 gravity 的 solver。 |
| 刚体输入 | `RigidEntity.apply_links_external_wrench(...)`、公开 DOF 控制方法 | 面向外部力/力矩或关节控制；不是任意求解器规则参数的通用 setter。Gravity 比较直接时不必把重力伪装成外力。 |
| 逻辑步进 | `scene.step(update_visualizer=False, refresh_visualizer=False)` | 公开；每调用一次推进一次 Genesis step。逻辑 tick 和“一 tick 多少物理步”由 worker 负责循环，不由 Genesis 自动知道。 |
| 无 viewer | `show_viewer=False`；checkpoint 加载也可传 `show_viewer=False` | 公开参数；本次确认加载后 `scene._visualizer.viewer is None`。该检查只作为探针观察，不应写入 worker 业务逻辑访问 `_visualizer`。 |
| 物理场景 checkpoint | `scene.save_checkpoint(path)` / `gs.Scene.load_checkpoint(path, show_viewer=False)` | 公开；`.gstraj` 保存 Genesis 场景定义和求解状态数组。适合恢复物理 continuation，不代替 edgeWorld 事务存档。 |
| 不应使用 | `scene._sim` 及其成员 | 下划线属性为私有实现细节。已有 PoC 的 `scene._sim.set_gravity(...)` 应替换为上述公开 solver API。 |

Genesis API 暴露的是各求解器各自支持的参数/输入控制，不存在一个可对所有物理规则泛化的 `set_rule_parameters` API。新增规则参数需按具体 solver 选其公开 API、公开 force-field/entity 输入或在 worker 侧定义明确 adapter；每一种能力都要单独检查 checkpoint 覆盖和恢复语义。

## 探针方法与结果

探针脚本位于 `/tmp/edgeworld_genesis_rigid_solver_probe.py`，不在仓库；运行命令：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-genesis/bin/python /tmp/edgeworld_genesis_rigid_solver_probe.py
```

结果概要：

1. 运行时报告版本 `1.4.3`，`Scene.rigid_solver`、`RigidSolver.set_gravity`、`Scene.step`、`Scene.save_checkpoint` 和 `Scene.load_checkpoint` 均可用。
2. 创建 `show_viewer=False` 的单球刚体场景，用公开 `scene.rigid_solver.set_gravity(...)` 分别设定两个逻辑阶段的重力；每阶段调用 8 次 `scene.step(update_visualizer=False, refresh_visualizer=False)`。执行 16 次物理步成功。
3. `Scene.save_checkpoint()` 写出 `/tmp/edgeworld_genesis_api_probe.gstraj`，`Scene.load_checkpoint(..., show_viewer=False)` 建立可继续步进的新场景，viewer 关闭。
4. 从 tick 1 checkpoint 继续时显式应用 tick 2 规则参数，得到的位置、速度和物理 step 计数与不中断执行完全相等：位置 `[0, 0, 0.9446840286254883]`，速度 Z `-0.9448000192642212`，steps `[16]`，`EXACT_EQUAL=True`。
5. 另一个探针故意恢复后不应用下一个逻辑 tick 的参数，轨迹不同（恢复结果 Z=`0.9728000164031982`，不中断结果 Z=`0.9446840286254883`）。保存 checkpoint 时生效的重力随 Genesis 运行状态恢复；差异来自恢复后继续沿用 checkpoint 时的旧规则参数，而不中断路径已为下一 tick 设置新参数。worker 必须在继续推进前应用下一 tick 的规则输入。这不表示 Genesis checkpoint 丢失了状态。

探针使用简化自由刚体和 Metal 单环境；没有尝试复杂碰撞、MPM/SPH/FEM/PBD、batched envs、跨设备/跨精度确定性，也没有执行整套工程测试。官方指南声称 checkpoint 保存 step 间所需模拟数组，并按版本/类布局验证兼容性；本任务没有自行验证官方所述 bit-for-bit 全面保证。

## 给 worker 实现的建议

1. Genesis adapter 对外只暴露受限方法，例如 `set_gravity(vector)`、`step_physics(count)`、`read_body_state(id)`、`save_physics_checkpoint(path)` / `load_physics_checkpoint(path)`；内部使用公开 Genesis API，不泄漏 `scene._sim`、solver 私有字段或 `_visualizer`。
2. 只在 Genesis scene 初始化时设置不变量配置；每个 edgeWorld tick 先根据已提交规则决定参数，在候选推进前通过公开 adapter API 下发，再执行明确数量的物理步。
3. edgeWorld 状态文件记录当前已提交 tick 的 Genesis checkpoint 文件标识/hash、Genesis 精确版本、backend/device、dt/substeps、scene/ruleset 配置、当前状态摘要，以及下一步需要应用的规则输入。Genesis checkpoint 文件与 edgeWorld 日志之间需由 worker 通过临时文件、校验和原子提交协调，避免一边写成功另一边失败却伪报 tick 已提交。
4. 恢复顺序建议：校验 edgeWorld 包版本/哈希 → `Scene.load_checkpoint(..., show_viewer=False)` → 校验 Genesis 版本和配置兼容 → 读回稳定实体 → 重新计算/应用下一 tick 的参数 → 固定步数推进 → worker 形成候选提交。Genesis checkpoint 成功加载本身不提交 edgeWorld tick。
5. 由于 Genesis Scene/entity 通常按其当前场景对象索引访问，edgeWorld 稳定 ID 到 Genesis entity 的映射应由 adapter 自己维护并存入 edgeWorld 元数据；不要把 Genesis 临时索引当持久身份。
6. 本次结果足以支持 P3 worker 继续使用 Genesis 1.4.3 的发布 API 路径，不支持扩展到复杂物理完整恢复、所有 solver 参数可运行时调节或跨平台逐位确定性；这些需要按目标 solver 新增专项证据。
