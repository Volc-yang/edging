# S1：抽象 Seed→Tree × Genesis 共享接口提案

状态：2026-11-01，v0.2 **设计提案**；输入 `ac5ec2f` 和用户修正：seed/tree 是抽象初态与因果发展结构，并非植物实体。父节点 V-STG/S1。Genesis 物理为本版必需路径；具体物理对象、法则和发展映射未批准。

## 1. 旧实现可复用的技术边界

| 来源 | 已实现事实 | 本版复用与禁止推断 |
| --- | --- | --- |
| `engine/edgeworld_worker/tree_worker.py` | 单写 `tree_world.json`，记录 revision/tick、事件链、命令去重和历史精确观察；不调用 Genesis | 可借事务、历史与 JSONL 机制；其 `seed/seedling/mature`、健康、生物量、水分和植物形体均是旧实验语义，**不进入新契约** |
| `engine/edgeworld_worker/worker.py` | `GenesisAdapter` 使用 Genesis 1.4.3 公共 API、Metal、单 Sphere；checkpoint 为内容寻址 blob，manifest 原子替换是提交点 | 可借候选步进、checkpoint 与恢复模式；旧 `body-1`、Sphere、phase 重力及参数不定义本版物理对象/法则 |
| 两个 worker | 共享 JSONL v1 envelope，但拥有不同 manifest/schema、head 和领域结果 | 同时运行两进程不构成同一权威世界；须有单一提交边界 |
| UE `EdgeWorldJsonlClient.cpp` | 通用 Exchange 校验 request ID/protocol；旧植物观察 parser 校验精确 world/tick/revision/watermark | 新抽象观察须新领域 parser；旧植物渲染组件只能作为渲染技术参考 |

## 2. 唯一权威与抽象状态模型

推荐新增一个**组合权威 worker**，保留两套旧 worker、存档和探针不变。一个 `world_id` 对应一个单写者、一个逻辑 tick/revision、一个 manifest、一个事件链和一个 command 去重表。Genesis 只计算候选物理结果，不直接写权威状态；UE 只发送显式命令和读取已提交观察。

新状态 schema 的候选分层如下，字段名在 S4 冻结：

```text
WorldHead {world_id, schema_version, tick, revision, rule_version,
           genesis_config_hash, state_hash, event_head_hash, checkpoint_hash}
SeedState {seed_id, seed_payload_schema, seed_payload_hash, ...已批准初态字段}
DevelopmentStructure {root_id, node_ids, causal_edges, structure_version,
                      ...已批准发展态字段}
PhysicsCandidate {object_ids, physical_input_hash, output_hash,
                  checkpoint_hash, genesis_version/config_hash}
TransitionEvent {tick, command_id, previous_state_hash, seed_input_hash,
                 physics_candidate_hash, development_result_hash,
                 rule_version, reason_ids, previous_event_hash, event_hash}
```

`SeedState` 是可标识的初始信息/状态，不是物体“种子”；`DevelopmentStructure` 是由因果影响形成的可观察结构，不预设枝、叶或生命阶段。`causal_edges` 是否严格构成树、允许分叉/合流的规则、节点增删和物理候选怎样影响转移，都须 S0/S4 明确。为避免 Genesis 成为无因果作用的旁路，**每次声称物理参与的发展转移必须在事件中引用实际物理候选摘要，且转移输入包含该候选**；它影响结果的具体函数和可观测差异须在批准的规则版本与反事实检查中定义。仅把物理 hash 与发展结果并排存储，不足以证明因果作用。

### ID、单位和版本

- `seed_id` 标识抽象初态；`root_id`、结构节点 ID 和因果边 ID 使用稳定、版本化推导或事件分配。Genesis 的 `physical_object_id` 是另一身份域，是否与某个抽象节点关联需显式映射；不能沿用旧 `body-1` 假装它就是 seed。
- 物理输入/输出保留 Genesis 原始单位、坐标系和设备/求解配置身份；到 UE 投影的比例、轴向和视觉单位另作版本化映射。米、秒、步长、容差等实际数值由 S0/S4/物理 owner 确定，不能从旧 Sphere 复制。
- 建议独立 `schema_version=abstract-seed-tree-genesis.v1`；JSONL envelope v1 可以沿用。旧植物 `tree_world.json` 与旧刚体 `world.json` 不原地升级；若需导入，另立显式迁移卡，记录来源版本与哈希。

## 3. 单 tick 候选、提交与恢复

```text
显式 advance(command_id, expected_revision, target_tick, external_inputs)
  → 验证 world、命令去重、revision、tick、输入 schema/版本
  → 读取已提交抽象状态与 Genesis checkpoint
  → Genesis 从已提交前态计算候选物理结果 P（具体对象/法则待批准）
  → 发展规则 F(previous_abstract_state, P, other_approved_inputs, rule_version)
       产生候选结构、原因及对 P 的引用（F 的语义待批准）
  → 校验 P、结构约束和事件因果引用
  → 保存不可变 Genesis checkpoint blob
  → 原子替换一个包含抽象状态、物理引用、事件、去重表的 manifest
  → 返回同一个 tick/revision 的组合 head；Observe 只读这个已提交版本
```

验证、Genesis、规则或 checkpoint 写入失败时 manifest 不变；进程内 Genesis 场景须恢复到已提交 checkpoint 后才能处理下一命令。若 manifest 替换已开始而持久结果不确定，返回 `commit_status_uncertain` 并停止写，重启核对磁盘后再应答/重试。恢复时检查 checkpoint 内容哈希、Genesis 配置、抽象状态与事件链，以及同一组合 revision 的物理候选引用。未被 manifest 引用的 blob 不是提交。

旧 Genesis adapter 的 `advance()` 会改变内存 scene，故组合实现必须用候选副本或在每条未提交路径重载已提交 checkpoint。旧植物 worker 的精确 schema 校验不能直接承载抽象字段而不变更版本。

## 4. Wire 草案与可执行检查边界

保留 JSONL v1 的 `protocol_version/request_id/operation/world_id`，命令保留 `command_id/expected_revision/target_tick`。新增领域输入的具体字段由 S4 冻结；以下只固定**形状**，不伪造物理法则：

```json
{"protocol_version":1,"request_id":"stg-a1","operation":"advance","world_id":"stg-demo","command_id":"tick-1","expected_revision":0,"target_tick":1,"external_inputs":{"schema_version":"<approved-input-v>","payload":"<approved-fixed-fixture>"}}
```

`observe` 须绑定准确 tick/watermark、结构观察范围和投影版本；响应包含 `world_id/logical_tick/source_revision/watermark`、抽象状态样本、因果结构样本、物理候选摘要与 `state_hash/event_hash`。UE 在更新画面前核对上述身份和版本。`request_id` 是往返相关 ID，`command_id` 是持久幂等 ID。完整请求/响应字段、错误码和物理候选—发展结果映射须在 S4 冻结后才能生成真正可执行 fixture。

| 后续检查 | 判定与原始证据 |
| --- | --- |
| 正常推进 | 固定已批准 seed 状态、物理配置和因果规则；0→1→N 的每步都有单一组合 revision、物理候选引用、结构变化原因；保存完整 JSONL、manifest、checkpoint、配置和哈希 |
| 因果区分 | 固定其他输入，按批准的反事实方案改变一个物理候选输入；预先定义应改变/不改变的结构输出，不用事后解释替代规则；若无可区分效果，不能声称 Genesis 驱动了发展 |
| 拒绝/幂等 | 同 ID 同输入返回同 result；同 ID 异输入、过期 revision、未知版本、缺历史、非法物理候选和规则失败不得产生新 head；记录错误码和前后持久哈希 |
| 恢复/只读 | 从同一 checkpoint 和 manifest 重启续算，和不中断轨迹按已冻结容差对照；历史观察、UE 相机/帧率/暂停/显隐不改变 head |

这些是**设计中的 Check**，本 S1 未运行抽象组合 worker、Genesis 或 UE。旧植物和单体刚体的证据仅证明各自实验版本。

## 5. PDCA 与 S4 放行

- **Plan：**先固定唯一写者与组合事务，再由 S0 裁决抽象 seed/发展结构、Genesis 物理候选及其因果映射；S1 与 S2/S3 设计可并行。
- **Do：**本文是接口提案；组合 worker、UE parser 与测试写路径须由 S4 分配。无 UE 引擎源码修改。
- **Check：**独立 reviewer 对照旧实现和用户语义修正，检查无植物/刚体身份偷换、无双写或孤立物理结果，且未来 fixture 能区分因果作用。当前为设计待审，运行门 `planned`。
- **Act：**S0/S4 未批准物理对象、输入字段、发展规则和可观察结果时，只可调查/探针，不放行依赖语义的实现。若 Genesis 候选无法纳入同一提交，先修适配或事务设计，不降低单写者门。
