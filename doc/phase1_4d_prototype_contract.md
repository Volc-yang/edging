# 阶段 1：4D 最小纵切原型契约

版本：0.1
状态：统筹任务锁定的**实验原型范围**；不等于生产架构定案
依据：`edgeworld_4d_engine_execution_plan.md`、`phase1_4d_core_contract_draft.md`、UE5 发布版纵切审查，以及用户明确的“UE5 发布版优先”原则。

## 1. 原型目标

用一条可观察、可存取、可重演的时间因果链证明：edgeWorld 逻辑时间推进权威世界状态，规则内核调用 Genesis 物理适配器，UE5 发布版 Runtime 插件经显式协议发出推进/观察请求，并使用现有 UE Renderer 呈现返回的状态。

```text
UE5 发布版 UI / Runtime Plugin
       │ 显式 Advance / Observe 请求；非阻塞
       ▼
edgeWorld worker（权威状态、逻辑时间、规则、持久化）
       │ 已批准的规则参数、固定物理步数
       ▼
Genesis adapter（单体自由刚体 PoC）
       │ 候选物理状态
       ▼
worker 校验、记录因果并提交 ──► Observe 结果 ──► UE5 现有 Renderer
```

UE5 发布版的具体版本先用本机 Launcher **UE 5.8.3 / CL 58210709**。此前 UE 源码树是 5.8.2，不能替代发布版结果。UE 编辑器/插件的 API、Cook/打包和跨进程集成尚待实测。

## 2. 原型固定范围

- 单一 `world_id`、单机、一个确定性规则集版本、一个自由刚体和有限逻辑 tick。
- 使用 edgeWorld 显式逻辑 tick；第一版 tick 为整数序号。四象周期由固定、版本化映射得到。
- Genesis 采用固定版本、设备、步长、子步数和场景配置。规则只给出占位物理参数用于验证接口，不声称其为最终世界法则。
- UE 插件作为命令/观察客户端。Actor、UObject、Game/Render Tick、相机、TimerManager 和表现缓存都不是权威状态；优先复用当前工程的 StaticMesh/Material/Light 表现方式。
- 不在此原型实现通用规则热插拔、复杂空间传播、多人、无限实体、跨硬件逐位一致、流体/软体/碰撞 solver 完整恢复、闭式离线快进或 UE 源码修改。

## 3. 最小权威状态与推进接口

worker 是权威写者；Genesis 返回候选物理结果，不自行提交 edgeWorld 世界状态。UE 只可发送显式命令并显示已提交结果。

建议原型状态至少包括：

```text
world_id, schema_version, state_revision, logical_tick,
ruleset_id/version, genesis_version/config, seed,
body_stable_id, body_state, event_head_hash,
processed_command_ids
```

JSON Lines 请求/响应是原型传输格式，消息应带 `protocol_version`、`request_id`、`operation`。`advance` 请求额外带 `command_id`、`world_id`、`expected_revision` 和 `target_tick`；`observe` 带 `world_id`、`logical_tick` 和 `view_spec`。

- 同一 world 同时只有一个逻辑写入序列。`expected_revision` 不匹配时拒绝推进并返回当前 head，不静默覆盖。
- `target_tick` 必须大于当前逻辑 tick；重复的 `command_id` 返回同一已提交结果，不重复步进。
- 每个 tick 先在候选状态运行固定规则和 Genesis 步进，然后形成提交记录。规则失败、Genesis 失败或持久化失败时，该 tick 不得表现为已提交；worker 返回明确错误并从持久状态恢复/重建求解场景。
- 本原型每个成功提交记录 `command_id`、tick 范围、规则版本、Genesis 版本/配置、固定步数、稳定实体 ID、输入/前态/后态摘要及因果事件 ID。第一版不使用随机源，但固定 seed 仍记入状态元数据。

具体 JSON 字段/数值编码可以由实现任务细化，但不得放松单写者、逻辑时间显式推进、幂等命令和清晰失败状态。

## 4. 存储、恢复与观察

- 原型提交边界包含当前权威状态、逻辑 tick/revision、事件/因果记录、Genesis 版本配置和 command 去重记录。小型 PoC 可使用一个版本化状态文件包裹检查点与有限事件记录，以临时文件写完校验后原子替换；不得假设当前 snapshot 和 history 分开落盘已经构成跨文件原子事务。
- 关闭 worker 后从最后完整提交恢复，再推进至目标 tick；与同一机器、同一运行时/配置下不间断执行的逐 tick 状态/事件摘要对照。仅单自由刚体结论，不外推至复杂 Genesis 求解器内部状态。
- `observe(world_id, logical_tick, view_spec)` 只读取已提交的当前或历史状态，不推进时钟、不运行 Genesis、不写状态、不消费随机数。响应包含 `source_revision`、请求 tick、稳定实体 ID、表现数据和 head/state hash。历史缺失时返回显式错误，不回退成当前值。
- 每帧/相机刷新只消费观察结果。改变渲染帧率、暂停渲染、切换视点、重复 Observe 都不得改变 worker head hash。UE 操作须使用异步/后台进程接口，Game Thread 不等待 worker 阻塞 I/O。

## 5. 原型验收门

必须提供可重复输入、环境与逐步结果摘要。原型通过要求：

1. UE 5.8.3 发布版 Runtime 插件可以构建并在目标编辑器/运行形态启动；没有 UE 源码改动。
2. 从 UE 显式发出推进请求，逻辑 tick 和 Genesis 物理步进有结果，进程/Actor 生命周期不成为状态权威。
3. worker 存盘、完全关闭、重启续算成功；每步 state/event hash 与不中断轨迹一致（限同机同版本同配置）。
4. 至少观察两个历史 tick；缺失时间明确报错。观察操作本身不改变 worker 的状态摘要。
5. 改变 UE 帧率/视角/渲染暂停，不改变相同显式命令序列的最终 tick、状态和事件摘要。
6. 失效 revision、重复 command、Genesis 错误、损坏/未知 schema 均返回明确结果；不伪造提交或静默新建/重置世界。

插件不能构建、启动或满足其中某项时，先提交可重现缺口、发布版 API 限制和插件/旁路替代尝试。**只有该证据链成立后**，主任务才评估是否需要 UE 源码改造；单纯静态判断、实现不完整或尚未批准的生产契约不构成源码修改理由。

## 6. 暂不锁定的生产决策

本原型不决定时间现实单位/暂停策略、分支时间线、通用规则冲突仲裁与注册协议、跨平台确定性级别、生产事件日志后端/保留策略、世界分区与实体迁移、复杂物理 checkpoint、离线闭式结算、商业许可归类及目标规模。这些议题需结合原型证据和产品决策另行审议。
