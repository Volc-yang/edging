# U1：世界身份与因果状态设计提案

状态：v0.1 **proposed**，2026-11-01；父节点 U，固定输入 `5a5fe11fc2c452de2aace7e8cc7c05d2fe5834c9`。本卡只设计身份与状态边界，不批准世界法则、灵域分配或生产 schema，不运行 UE/Genesis。下游 U2、U3、U6、U7 应引用本文件的身份域及开放问题；U4 才合成事务与恢复。独占交付为本文件。

## 1. 输入身份与判断状态

| 来源 | 当前可用结论 | 本卡处理 |
| --- | --- | --- |
| 用户决定，经 [G0 记录](../pdca_g0_freeze_decision_record.md) | Seed→Tree 是**抽象初态经因果影响形成发展结构**，非植物；本纵切 Genesis 必需；AI 与载具不是本版必需门 | **已定范围**；不导入旧树的萌芽/枝叶语义 |
| [总设计树](../universe_architecture_design_plan.md)与根 `AGENTS.md` | 单一权威写入、逻辑时间与 UE 渲染帧分离；优先 UE5 发布版插件/适配 | **已定架构边界**；观察/镜头/视觉流送不产生权威提交 |
| [S4 实验契约](../seed_tree_genesis_slice_contract.md) | 组合 worker 用一个 manifest、tick/revision、事件链、Genesis checkpoint 和去重表；中性刚体影响 `influence_mm` | **已审技术 fixture**，不是生产世界存在、物理规律或通用拓扑 |
| `engine/edgeworld_worker/abstract_causal_worker.py` @ 输入提交 | `world_id:seed:0`、`world_id:node:<tick>`、`world_id:edge:<tick>`、`physical:0` 是现有实验 ID；同一 manifest 中提交 head/事件/命令结果，历史可观察 | **代码观察**；线性节点和 tick=revision 是实验事实，不推广为世界约束 |
| `engine/edgeworld_worker/tree_worker.py` @ 输入提交 | 旧植物 worker 有独立 manifest、植物阶段及命令历史 | **隔离参考**；不得把两个 manifest 拼成一个权威或将植物阶段升级 |

## 2. 基础单元比较与推荐

**proposed：**以“可标识、可关联、可追溯变化的世界存在”作为逻辑建模入口，简称 `Existence`。它是权威记录的单位，**不是** UE Actor、三角形、方块、Genesis 刚体或自动拥有意识的个体。一个存在可由多个 UE 视觉实例呈现；一个视觉实例也可以聚合多个存在。该映射由 U7 版本化管理。

| 候选单位 | 适用之处 | 不足及 U1 建议 |
| --- | --- | --- |
| 物体/实体 | 适合可移动、可碰撞或可持久引用对象 | 城市、河流、区域不能都压成刚体；`Existence` 可有类型化状态，物理参与者另设身份映射 |
| 区域/场所 | 适合城市、蛮荒、原野、森林、海洋、河泽的持续边界 | 区域边界随时间变化；区域本身可是一种 `Existence`，其几何与包含关系由版本化状态/关系表达 |
| 关系 | 适合归属、连接、因果与组合 | 关系有独立 `RelationId` 和有效时间；不能仅作两个对象的可变字段，否则难追溯来源 |
| 灵域/“世界之灵” | 承认用户“万物有灵”的世界设定；可表达世界内主体的持续身份与能力 | 何时取得**独立可追踪**灵域记录、意识和权能、灵域如何变化仍待产品裁决；可选的是单独记录方式，不是“有灵”本身，不强制拟人化 |

上述比较不决定可见形状和演化函数。混沌初态六类场所共存是用户目标；其精确接壤、归属、法则与何时成“灵”由 U5/G0 裁决。玩家**世界内化身**可作为存在；外部账号和一次登录会话必须留在另一个身份域，由 U6 设计映射与权限。

## 3. 候选身份域与稳定性

以下是 **proposed logical identifiers**，不是新的 wire 字段定义。编码、长度、分配器、跨世界迁移由 U4 合成并经后续契约冻结；展示字符串不应成为语义来源。

| 身份域 | 用途与不可混用边界 | 建议稳定性 |
| --- | --- | --- |
| `WorldId` | 唯一权威世界/命名空间；不等于 UE 项目、用户账号或一次运行目录 | 存档生命周期内稳定 |
| `ExistenceId` | 存在的持续身份；种类与名称是可变属性，不编码到 ID 中 | 同世界内不复用；消亡后仍可从历史引用 |
| `RelationId` | 连接、包含、归属、因果等关系实例；引用存在或其他已批准端点 | 不因端点状态变化复用；变更有事件 |
| `EventId` | 已提交转移的不可变身份；记录原因、输入与结果摘要 | 提交后稳定并可按事件链追溯 |
| `CommandId` | 调用方的幂等意图；同 ID/不同规范化输入为冲突 | 与世界及调用方作用域绑定，保留去重结果 |
| `PhysicalObjectId` | Genesis 候选所求解的参与者；到 `ExistenceId` 的映射显式、可版本化 | 不把旧 `physical:0` 直接当抽象 seed |
| `ProjectionId` | UE 资源/视觉实例的派生引用；不具权威写权 | 可重建，不能决定 `ExistenceId` |
| `AvatarId` / `SessionId` / `AccountId` | 世界内化身、一次访问和外部身份分离 | `AvatarId` 如单列，须以版本化关系绑定同一世界的 `ExistenceId`；U6 定义安全与生命周期，不把会话 ID 写成世界存在 ID，也不预设玩家身份在何阶段出现 |

**proposed minimum invariant：**每个可提交的存在/关系 ID 都属于准确 `WorldId`；历史 ID 不回收；关系端点若引用存在，必须在声明的有效时间内可解析（可指向已消亡但有历史的存在）；物理/视觉映射不得偷偷赋予外部系统写权。无需假定所有关系形成数学树。跨世界因果引用、复制、迁移另立显式契约，当前不隐式允许。

## 4. 状态、时间、版本与因果边界

**proposed state envelope：**`WorldHead {world_id, schema_version, rule_version, logical_tick, state_revision, state_hash, event_head_hash, checkpoint_ref}`；`ExistenceRecord {existence_id, kind_version, state_schema, state_digest, lifecycle, valid_from_tick, valid_to_tick?}`；`RelationRecord {relation_id, relation_kind_version, endpoint_refs, valid_interval, originating_event_id}`；`TransitionEvent {event_id, command_id, prior_head, input_refs, genesis_candidate_ref?, rule_version, result_refs, reason_refs, event_hash}`。这是字段归属建议，U4/U2 可能调整实际序列化；不把 `influence_mm`、旧植物生物量或 Sphere 配置升为必填生产字段。

- `logical_tick` 表示已提交的世界演化时间；`state_revision` 表示权威状态版本。**proposed：**两者独立单调，显式命令可按批准契约推进 tick；当前探针 tick=revision 只是实验事实。UE 帧时间、相机时间和网络会话时间均不是逻辑 tick。
- `schema_version` 管可解码结构；`rule_version` 管转移语义；`projection_version` 由 U7 管观察呈现。改动任一版本不静默解释旧档，迁移须新事件/工件及来源 hash，具体策略由 U4。
- 因果不是“画面出现了边”即可成立。**proposed：**已提交 `TransitionEvent` 引用旧 head、准确外部输入/命令、Genesis 已验证候选（若参与）、规则版本与结果记录；关系可表达因果链接，但不得引用不存在或未提交的来源。是否允许分叉、合流、循环关系及其时间约束仍开放；因果事件链本身不能指向未来提交。
- 观察指定 tick、水位与视图版本，仅从同一已提交 head/历史产生样本。缺历史、错世界或错水位是显式拒绝；不得读取半提交候选。U4 决定快照/事件索引和历史保留策略，U7 决定视觉重建。

## 5. 写入权限与模块接口（proposed）

| 主体/模块 | 候选行为 | 对 manifest/head 的权限 | 边界失败条件 |
| --- | --- | --- | --- |
| 单一权威协调器（U4） | 校验命令、选择规则版本、合成候选、原子提交、恢复和去重 | **唯一写者** | 双进程写同一 head、半提交可见、提交不确定仍继续写均失败 |
| 演化规则模块（产品规律待裁决） | 从旧已提交状态、版本化输入、已验证物理候选生成候选状态/原因 | 无直接写权 | 把随机/外部输入藏在全局状态、跳过输入版本或无原因引用即拒绝 |
| Genesis 适配层（U2） | 从准确 checkpoint 算物理候选及其配置/设备摘要 | 无权直接替换 head | 物理输出与抽象发展并排存放、未进入候选转移却声称因果通过即失败 |
| AI 提案门（U3） | 记录提案来源、水位、权限、有效期并向权威提出候选命令 | 无直接写权 | 模型输出直接改状态或绕过规则验证即失败；AI 当前非 V-HOME 必需门 |
| 外部动作/访问层（U6） | 将有因果作用的行为形成带权限/预期 revision 的命令 | 无直接写权 | 会话/化身混淆、旧 revision 越权推进即拒绝 |
| UE5 发布版投影/相机（U7） | 只读观察、流送、渲染、镜头及本地非权威运动 | 无写权；显式输入仅提交命令请求 | 相机、暂停、帧率、显隐、历史观察隐式推进或改 manifest 即失败 |

**proposed interface seam：**U1 仅命名身份/状态边界；U2 定义 `PhysicalObjectId → ExistenceId` 候选映射与单位；U3 定义提案主体验证；U6 定义 Account/Session/Avatar 的权限来源；U7 定义 `Existence/Relation → Projection`；U4 定义唯一提交、writer lock、命令指纹、原子持久化和恢复。两份旧 worker 和旧存档继续隔离；无任何 UE 引擎源码修改需求。

## 6. 有界正例与反例矩阵

以下只是**设计 fixture**，用占位状态和摘要说明边界，不给出正式物理量或演化法则。后续运行检查必须先固定 schema、规则、错误码、原始请求/响应和状态目录，不能以本表自证实现已通过。

| Case | 给定/操作 | 设计预期与可判失败信号 |
| --- | --- | --- |
| P1 单次候选到提交 | 世界 `W` 有抽象初态 `E0`（不指植物），head `(tick=0, rev=0, hash=h0)`；`C1` 携预期 rev0；U2 提供候选 `P1`，未来待批准规则版本 `R?` 产生 `E1`、关系 `L1`、事件 `EV1` | **设计预期：**唯一权威一次提交后 head 指向 `(tick=1, rev=1, h1)`，`EV1` 引用 `h0/C1/P1/R?` 和 `E1/L1`；Observe 0/1 各返回对应已提交切片。`R?` 未批准，故这里只检查引用闭合与事务形状，不声称实际发展值正确。若孤立 `P1` 也能被标“已实现因果”则失败 |
| N1 重复/冲突命令 | 已提交 `C1` 后同 ID 同规范化输入重试；再以同 ID 换一个输入 | 前者返回同一已提交结果且不新增事件；后者拒绝 `command_id_conflict` 类错误且 head 不变。具体错误码由 U4 冻结 |
| N2 旧 revision/错世界 | `C2` 以旧 rev0 或另一个 `WorldId` 请求推进 W | 拒绝且无新 head、事件或 Genesis 提交；若通过或推进则设计失败 |
| N3 悬空关系/候选 | 候选 `L2` 指向从未存在的 `E9`，或事件引用未验证物理候选 hash | 提交校验拒绝、旧 head 可恢复；若观察可见悬空 `L2` 或物理候选被当作结果则失败 |
| N4 历史观察越界/副作用 | 请求缺失 tick、错 watermark；随后移动 UE 相机、暂停/显隐或重复 Observe | 越界显式拒绝；其他操作前后 head/state/event/manifest 摘要相同。若任何观察令 tick/revision 前进则失败 |

## 7. PDCA 与下游交接

- **Plan：**在固定基线阅读 G0/S4、总设计树、旧树 worker 与现有组合 worker；将已定、已观察、proposed、开放项分开。只设计身份/状态，U5 的初态地理、U2 的物理和 U3 的 AI 语义独立。
- **Do：**本文件提供单位比较、候选身份域、字段/模块归属、P1 与 N1–N4。未修改协议、worker、UE、旧存档或任何产品规则。
- **Check（owner 实际自检）：**逐字段归属见第 3–5 节；世界内存在/关系/事件 ID 由准确世界作用域限定，外部账号、会话与世界内化身不混同；P1 引用闭合，N1–N4 分别可由未来 manifest/事件 hash 和拒绝响应判失败；设计 DAG 中 U2/U3/U6/U7 可在 U1 被接受后引用。修订后执行 `git diff --check` 通过；本文件 3 个相对链接均存在；`git status --short` 仅本文件修改。**独立设计审查仍待统筹安排**；本卡无运行 Check，UE/Genesis/AI 行为门均为 `planned`。
- **Act：**请非作者审查 ID 生命周期、关系端点时间、事件来源与权限矩阵。若 U2/U3/U6/U7 发现字段冲突，仅返工共享边界；灵域身份、分叉/合流、跨世界链接、状态保留/迁移和正式演化规律留 G0/U4 裁决。设计可接受也只解锁下游设计，不能把探针转成生产接口。
