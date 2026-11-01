# S1：Seed→Tree × Genesis 共享接口提案

状态：2026-11-01，v0.1 **设计提案**；输入 `8a069fa` 和用户决定的 Seed→Tree + Genesis 必需范围。父节点 V-STG/S1。本文不批准植物生长、重力系数、落地判定或最终物理容差。

## 1. 现有代码边界

| 现有能力 | 核对结果 | 对新纵切的影响 |
| --- | --- | --- |
| `engine/edgeworld_worker/tree_worker.py` | `Worker` 单写 `tree_world.json`；状态、事件、命令索引在同一 manifest；`advance` 需要环境并只向前一 tick；没有 Genesis 调用 | 可复用树状态转移与观察语义，不能把此 worker 原样称为含物理的权威世界 |
| `engine/edgeworld_worker/worker.py` | `GenesisAdapter` 使用 Genesis 1.4.3 公共 API、Metal、单 Sphere；checkpoint 是内容寻址 blob，`world.json` 的原子替换为提交点；失败时尝试恢复已提交 checkpoint | 可借用适配器/事务模式，现有 `body-1`、重力 phase、单位和场景参数仅为旧单刚体实验，不自动成为“种子物理” |
| 两个 worker | JSONL v1 envelope 相近，却有不同 `schema_version`、状态文件、ID、领域结果和错误码 | 并行启动两个 worker 将产生两个 revision/head，无法证明同一权威因果链 |
| UE `EdgeWorldJsonlClient.cpp` | 通用 Exchange 核对 request ID/protocol v1；树专用 parser 另核对 world/tick/revision/watermark 和版本 | 新组合观察须使用新的领域 parser 或扩展树 parser；不能假设通用客户端验证全部物理字段 |

## 2. 推荐的最小组合边界（待 S4 冻结）

建立**一个新的组合 worker**，保留旧 `tree_worker.py` 和 `worker.py` 的 v1 文件/协议/证据不变。它是一个 `world_id`、一个单写者、一个 revision/tick、一个 manifest 和一个命令索引。Genesis 适配器在该进程内只产生候选物理结果，不拥有另一套 world manifest。树演化仍调用已版本化的实验转移函数；两个候选结果组成同一个提交记录。

推荐最小物理对象是与 `seed_id` 一一关联的**种子代理刚体**，不是树体碰撞或植物动力学。Genesis 的候选位置/速度进入权威记录，UE 只从已提交的观察样本投影该代理。是否把位置变成树根锚点、让落地条件影响萌发或选择其他物理对象，属于 S0 产品/技术语义裁决；在裁决前仅能做接口和实验探针，不能把任一机制写成已批准世界法则。若本版本需要 Genesis 对树生长产生因果作用，S4 必须另写明确输入字段、单位、阈值与失败条件。

### 稳定 ID、单位与版本建议

| 字段/身份 | 建议 | 待裁决或兼容边界 |
| --- | --- | --- |
| `world_id`、`seed_id`、`tree_id` | 沿用树契约；`tree_id` 萌发前为 null | 旧 `body-1` 不等于 `seed_id`；新物理 `body_id` 建议由 `seed_id` 派生并在 manifest 中固定映射 |
| `logical_tick`、`state_revision` | 同一成功命令各增加 1；所有树/物理状态和事件对应同一 `(tick, revision)` | 失败/重试不增加；不能有独立 Genesis tick 对外暴露 |
| 物理时长与坐标 | `dt` 秒、`physical_steps` 正整数；Genesis 候选位置用米、速度用米/秒的**实验提案**；映射 UE 世界坐标时显式版本化比例和轴变换 | 实际 Genesis API 值/单位与 UE 投影转换需实测和 S4 批准，不能直接把旧 Sphere 参数称为真实种子尺寸 |
| 配置身份 | `schema_version=seed-tree-genesis.v1`（建议标识）、Genesis 1.4.3/backend/设备、dt/steps、规则版本、seed、投影版本分别记录 | JSONL envelope v1 可沿用；旧 manifest 不能原地升级或静默加载，迁移另立卡 |
| 物理样本 | `body_id`、position、velocity、物理输入/配置摘要、checkpoint SHA256 | 非有限值/形状错误拒绝提交；误差与跨运行对照规则待 S0/GQ 冻结 |

## 3. tick 内顺序与提交事务

```text
UE 显式 advance(command_id, expected_revision, target_tick, environment)
  → 组合 worker 验证 world/ID/revision/tick/环境并查去重
  → 读取已提交树状态与 Genesis checkpoint
  → 复制或可恢复的 Genesis 候选场景，按固定配置 step
  → 校验候选物理结果；以已批准输入生成候选树状态
  → 生成单条组合事件（两类前态/后态摘要、版本、原因、checkpoint hash）
  → 持久化不可变 Genesis checkpoint blob
  → 原子替换单一组合 manifest（唯一提交点）
  → 返回同一 revision 的状态/事件摘要；UE 再 observe
```

**失败规则：**验证、Genesis step、非有限值、树规则或 checkpoint 写入失败时，manifest 不变，恢复已提交 Genesis checkpoint 后才接受下一命令。若 manifest 替换已开始而持久结果无法确认，返回 `commit_status_uncertain`、停止写入，重启后从磁盘 manifest 判定；不能直接重放一条可能已提交的命令。恢复时校验 checkpoint 内容哈希、树状态重演/事件链、组合 manifest 与 checkpoint 的物理摘要，且配置/版本一致。只有完整组合记录可被 `observe` 返回。未被 manifest 引用的 blob 可之后安全清理，不视为提交。

**关键实现风险：**旧 Genesis adapter 在 `advance()` 中会改变进程内 scene；组合 worker 须用候选副本或在任何未提交路径重新加载已提交 checkpoint，不能让失败后的内存物理状态成为下次候选的前态。旧树 worker 的存档校验依赖精确 schema，不能直接把物理字段塞进旧 manifest 而保留旧版本号。

## 4. 版本化 wire 接口草案

保留 JSONL v1 的 `protocol_version/request_id/operation/world_id` 和 `ok/result` 或 `ok:false/error`。新领域结果加 `domain_schema_version`，不要求旧 worker 理解它；UE 必须在应用样本前核对世界、tick、revision、水位、规则/投影版本、物理样本身份与状态摘要。`request_id` 只关联本次往返，`command_id` 才标识幂等推进。

```json
{"protocol_version":1,"request_id":"stg-a1","operation":"advance","world_id":"stg-demo","command_id":"tick-1","expected_revision":0,"target_tick":1,"environment":{"phase":"shaoyang","moisture":0.8,"light":0.7}}
```

候选 `observe` 请求沿用树的精确 `view_spec`，但 `rules` 增加组合领域版本/物理投影版本；响应同时给 `tree_sample` 和 `physics_sample`、相同 `source_revision/watermark`、`state_hash/event_hash` 及 `checkpoint_sha256`。字段名和哈希覆盖范围由 S4 固定；现有树 UE parser **不接受**此草案作为既有 schema。错误码尽量保留现有 `revision_conflict`、`command_id_conflict`、`history_missing`、`watermark_mismatch`，组合新增的 Genesis 故障与 checkpoint 损坏需在负例卡冻结，不静默归为成功。

## 5. 最小 fixture 与检查矩阵

| 序列 | 固定输入与可判定结果 | 证据 |
| --- | --- | --- |
| 正常 0→1→5 | 新独立 state dir、固定 seed/环境序列、Genesis 版本/backend/dt/steps；每次 `status→observe→advance→observe`，tick 0/1/5 精确 watermark | 原始 JSONL、Genesis 配置、单 manifest、checkpoint SHA、树/物理/组合 state hash、事件链、UE 样本身份 |
| 幂等/拒绝 | 同 `command_id` 同 payload 返回原 result；同 ID 改环境、旧 revision、跳 tick、错误 world/规则/水位、Genesis 注入失败均无新提交 | 每项前后 manifest/checkpoint 引用和 event head；错误码与退出状态 |
| 恢复/历史 | tick 1 后关闭进程、从同一 manifest/checkpoint 重启续算至 tick 5；与不中断固定轨迹对照，历史 tick 0/1/5 查询不改 head | 两个独立 run 的完整状态/事件摘要、checkpoint 内容哈希、请求响应及时间窗 |
| UE 只读 | UE 相机、帧率、暂停、显隐、重复观察前后无权威摘要变化；只有显式 `advance` 改变 | UE Metal 画面/日志及各操作前后组合 manifest/head 哈希 |

上表是**未来检查设计**，本 S1 没有运行 Genesis、UE 或组合 worker。旧树/刚体两套 worker 的现有通过证据只能作为基线对照，不能作为组合门通过。

## 6. PDCA 与拓扑

- **Plan：**依据 S0 已选 Seed→Tree + Genesis 必需，先界定写者和状态事务，再裁决物理对象/因果接点、单位、schema、错误和恢复；S1 与 S2/S3 可并行提出设计。
- **Do：**本文件只给接口提案。新组合 worker 的实现路径、UE parser/Actor 和测试目录由 S4 分配，禁止两个 agent 同时改共享协议。
- **Check：**独立 reviewer 对照三份现有代码/两份旧契约，核对没有双写、物理孤立提交或隐式 tick；审核固定输入能区分正常/拒绝/恢复。实际组合进程探针属于 G3。当前结果：设计待审，运行证据 `planned`。
- **Act：**若 S0 决定物理不作用于树形/生长，记录该限制，仍须有同一权威事件/呈现来源；若要求作用，先批准明确因果字段再扩展。Genesis checkpoint 无法满足原子边界时先调整适配/持久化，不修改 UE 源码。S4 冻结后才能派 G2a/G2b/G2c 实现。
