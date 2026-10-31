# G1-INTERFACE：4D 世界纵切接口设计

状态：2026-11-01，v0.1 **设计提案**。输入基线 `5cac4a3`。本文件只界定下一版本的开发接口和验证方法，不批准玩法、物理参数、植物规律、AI 模型或产品验收阈值。

## 输入事实与待冻结决定

- [阶段 1 原型契约](phase1_4d_prototype_contract.md)规定 worker 单写者，Genesis 返回候选物理结果，UE 只提交显式命令并观察已提交状态。原型为单世界、单刚体、单机。
- [Seed→Tree 契约](seed_tree_4d_render_slice_contract.md)复用 JSONL v1 envelope：`protocol_version`、`request_id`、`operation`、`world_id`，响应为 `ok/result` 或 `ok:false/error`。树 Worker 与 Genesis Worker 分离。
- [G0 提案](pdca_g0_version_goal_proposal.md)的第 4 节产品范围、平台、性能/视觉/可靠性阈值尚未冻结。AI 和 Genesis 是否进入下一版必要纵切也未裁决。
- 现存 `engine/edgeworld_worker/worker.py`、`tree_worker.py` 和 `engine/chaos/origin_worker.py` 有各自领域语义。共同 envelope 不等于共同状态 schema 或可互换的错误集合；本设计不要求把它们并成一个运行时。

**G0 需先裁决：**本版本固定场景与成功信号；AI/Genesis 是必需、可选还是排除；目标机器、规模、预算；有效视觉/性能/恢复门。裁决记录应给出版本号和 owner。G1 可以做接口设计与探针，依赖这些决定的产品实施和验收继续等待。

## 职责与版本边界

| 边界 | 唯一写入者与输入 | 输出/只读者 | 失败与禁止路径 |
| --- | --- | --- | --- |
| 4D 权威层 G2a | worker 接受显式 `advance`，以 `world_id`、`command_id`、`expected_revision`、`target_tick` 和版本化规则输入形成候选状态；提交状态、事件、去重记录 | `status` 和 `observe` 返回已提交的 revision、tick、水位、稳定实体 ID、状态/事件摘要与呈现样本 | 冲突 revision、重复 ID 不同负载、缺历史、损坏状态须显式错误；渲染帧/查询不写入 |
| Genesis 适配 G2b | 仅由权威 worker 在候选 tick 调用，输入固定求解器版本、设备、单位、步长、子步数、场景和前态 | 返回候选轨迹/状态及诊断，供权威层验证后提交 | 求解失败不产生成功提交；适配器不直接写 world manifest/事件 |
| AI 提案 G2d | 接收版本化观察/目标与模型、提示、数据版本及预算；产出带来源和置信/拒绝信息的候选提案 | 权威规则验证器或人工审批者消费提案；UE 可只读展示提案状态 | AI 不获得权威 state directory 写权；未知模型/超时/不合规输出显式拒绝，不隐式推进 tick |
| UE5 发布版插件 G2c | UI/输入层可发显式 `advance`，但命令 ID 与预期 revision 必须可追踪；其他呈现操作只发 `status/observe` | 把固定 revision/tick 的样本投影到 Actor/Renderer；相机、帧率和暂停只改变视图 | 无响应、错 world/revision、水位不符时显示错误或保留旧画面并标记，不伪造新状态 |

**版本建议：**协议 envelope 保持 v1 兼容现有探针；新增领域 schema 使用独立 `schema_version`，规则/生成器/物理/AI 配置各有显式版本。不要在旧字段下改变语义。`request_id` 标识一次请求/响应相关性，`command_id` 标识权威推进的幂等性；二者不可互代。跨领域状态共享须经后续 ADR 冻结 ID、单位、坐标系、序列化和迁移策略。

## 建议的最小探针与错误矩阵

固定一个已批准的 world 输入和独立 state directory，单 worker、单 UE 客户端。记录准确提交、构建、依赖/配置、请求/响应 JSONL、状态 manifest、event/head 摘要及观察时间窗口。探针顺序：`status` → `observe(tick 0)` → 显式 `advance(command A, expected_revision 0, target_tick 1)` → `observe(tick 1)` → 重放 command A → 历史 `observe(tick 0)` → 关闭/重启后 `status/observe`。每一步比对 world、tick、revision、水位与摘要；每个纯观察动作前后比对权威持久摘要。

错误探针另覆盖：过期 revision、同一 command ID 不同输入、未知/缺失历史、错误 world、未知协议/schema、物理适配失败（若纳入）、AI 拒绝/超时（若纳入）、worker 退出与 UE 响应超时。保存原始结果和预期错误代码映射；当前代码的领域错误名称作为实测输入，统一错误 taxonomy 待 G1 审查后冻结。不能以旧阶段 2 单刚体通过推断 AI、复杂物理或完整混沌世界通过。

## PDCA 卡与拓扑派工

| 项 | 内容 |
| --- | --- |
| ID / parent / owner | `G1-INTERFACE` / `G1` / 接口设计 owner；独立 reviewer 另派 |
| Plan | 固定 `5cac4a3` 与现有契约/代码；先完成接口清单和写入权划分，再列 schema 版本与错误/恢复路径，最后设计探针。依赖 G0 过程门；产品范围阈值待 G0-FREEZE。 |
| Do | 本设计提案；不改运行代码、旧契约和共享 backlog。后续 G2a/b/c/d 各自拥有非重叠实现路径，集成前由 G1 冻结共用字段。 |
| Check | reviewer 对照阶段 1、Seed→Tree 契约与三类 worker，逐项确认写者唯一、版本字段、错误路径、DAG 无环、探针可复现。实际运行探针属于后续集成卡；本轮未运行 UE/Genesis/AI。证据为本文、准确输入提交、审查记录及后续原始 JSONL。 |
| Act | 发现冲突时修改最小接口卡并提升版本，保留旧探针证据；缺 G0 决定则标 `inconclusive` 并仅派不依赖的规划/基准任务。G1 接受须有独立审查及统筹集成裁决；文档提交本身不代表接受。 |

依赖 DAG：`G0 过程门 → G1-INTERFACE 设计 → 独立审查/接口冻结 → 本版本必需 G2 叶卡 → G3 探针与集成 → G4 独立验收`。`G0-FREEZE` 与 `GQ-BASELINE` 可并行推进，冻结阈值在受影响的 G2 实施/G4 判定前接入。各 G2 owner 不得独立重定义共享字段；接口变更须回到 G1 形成新版本。
