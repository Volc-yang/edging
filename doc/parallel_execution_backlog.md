# edgeWorld 并行开发统筹清单

日期：2026-10-10
状态：迭代 2 子任务完成并审查；交付待集成和 UE↔worker 接线验证

## 主任务统一开发原则（最新）

所有 subagents/subtasks 必须遵循以下顺序：

1. **优先使用 UE5 发布引擎的成熟能力和渲染管线。** 通过发布版 UE5 插件/模块/适配层连接 Genesis 与 edgeWorld 第四维状态演化，先验证最小纵切；不预设需要维护 UE 源码 fork。
2. **以已批准的 4D 契约作为验收依据。** 把具体契约条目映射到发布版 UE5 的能力，记录实际差距、复现步骤和证据；不能只以架构偏好或静态源码猜测判定不符。
3. **仅当发布版 UE5 无法满足契约时，才评估引擎源码修改。** 源码修改方案需指出无法满足的契约、不改源码的插件/旁路替代方案及其失败证据、源码改造范围/升级成本/许可影响，并由主任务评审后再开实现任务。

此前 UE5 子系统映射报告中的“旁路或替换”仅作为风险分析材料，不代表已决定改引擎源码。源码构建/子系统 PoC 属备用路线，不得取代对发布版 UE5 + 插件集成路径的优先验证。

## 目的与工作区约束

采用一个主任务维护架构、接口、阶段门与集成，多个子任务各自负责有边界的研究或实现。子任务使用独立 Git worktree/分支；每项任务只提交自己的交付物，并报告依据、未验证点和集成风险。

主工作区 `/Users/yangacan/edgeWorld/edge-world` 当前有大量未提交改动。已创建的三个 worktree 都从提交 `51a16b9` 分支，**不包含主工作区的这些改动**。计划副本被复制到各 worktree 作为输入；资产盘点报告明确只认已提交基线。后续涉及现有实现的任务必须显式读取主工作区文件，采用只读审查，或先由主任务将指定成果安全地提交/同步到基线；不得以旧提交推断当前工作树实现。

## 已完成并行工作包

| 工作包 | 交付 | 分支 / 提交 | 结论与限制 |
|---|---|---|---|
| 阶段 0：代码资产盘点 | `phase0_edgeworld_inventory.md` | `codex/edgeworld-phase0-inventory` / `b338328` | 确认提交基线有章节级规则、快照、逐轮历史和消费端实验；指出主工作区未提交内容未复核。 |
| 阶段 0：UE5 子系统映射 | `phase0_ue5_subsystem_map.md` | `codex/edgeworld-phase0-ue-map` / `95a4e82` | 静态源码定位扩展入口；建议先做不依赖 Actor 的薄层纵切，尚无 PoC 证据。 |
| 阶段 1：4D 核心契约 | `phase1_4d_core_contract_draft.md` | `codex/edgeworld-phase1-contract` / `58d3f4a` | 提出权威状态、逻辑时间、调度/提交、因果、事务、观察纯读草案；明确尚未批准。 |
| 阶段 0：主工作区改动审阅 | `phase0_dirty_tree_audit.md` | `codex/edgeworld-dirty-tree-audit` / `47851f8` | 实际检查未提交实现；Genesis 只证明自由球简化 checkpoint；完整持久自然演化、局部传播、UE 发布版纵切和批准契约仍未证明。只读，没有运行测试。 |
| 发布版 UE5 插件纵切方案 | `ue5_release_plugin_vertical_slice.md` | `codex/ue5-release-plugin-path` / `85a57a8` | 建议 UE 插件 + Python worker/Genesis adapter + 现有 Renderer；静态方案未启动/编译/验证。发现 Launcher 是 UE 5.8.3 CL 58210709，源码 checkout 是 5.8.2，需按发布版版本重验。 |
| UE 许可与分发边界 | `ue_license_distribution_questions.md` | `codex/edgeworld-license-boundary` / `ce39e53` | 按 Epic 在线 EULA update 21 整理边界与问题，非法律意见；发布版优先及独立 edgeWorld 核心有利于隔离，但不自动决定插件分类。 |

报告位于各自 worktree 的 `doc/` 下，尚未合并到主工作区分支。报告和分支链接是研究/设计交付，不等于实现集成。

## 综合判断

三份报告对架构方向一致：edgeWorld 自己定义权威世界状态、逻辑时间、规则提交和因果；UE5 首先作为成熟宿主、工具和呈现后端，通过发布版 UE5 插件/适配层集成 Genesis 与第四维状态演化。Actor、逐帧 Tick、TimerManager、World Partition 的加载状态以及画面都不应自动成为持久世界事实。UE 源码构建通过只证明构建链在本机可用，不证明交互启动或目标语义成立；是否改源码取决于发布版集成对已批准契约的实测结果。

现有执行计划中的阶段 0/1 仍未全部关闭，至少有三项证据缺口：

1. **主工作区改动复核**：已由只读审计复核，详见 `phase0_dirty_tree_audit.md`；审计引用历史测试日志，本次未运行测试，仍需按当前工作树验证。
2. **发布版 UE5 纵切验证**：发布版 UE5 插件/适配层承载 Genesis、非 Actor 权威状态、逻辑时钟、恢复/重演和只读观察仍未验证。已知 Launcher 是 UE 5.8.3，备用源码 checkout 是 5.8.2；此前面向源码 5.8.2 的启动记录不能替代发布版插件纵切验证。
3. **契约与产品决策**：最小原型契约已写入 `doc/phase1_4d_prototype_contract.md`；生产级时间政策、通用规则仲裁、跨平台确定性、完整物理求解器恢复、规模和商业许可归类仍开放。

因此，当前不应把阶段 0 或阶段 1 标为通过，也不应将 UE Renderer 深改、规模化、内容生产分配为实现任务。

## 当前迭代：发布版插件与 Genesis 纵切

原型范围和路线已由统筹任务完成；下面两个前置工作可并行。原型契约仅适用于有限实验，不代表生产架构全部定案。

| ID | 工作包 | 依赖 / 输入 | 状态与交付 |
|---|---|---|---|
| N1 | 主工作区现有资产复核 | 只读访问当前工作树 | **完成**：`phase0_dirty_tree_audit.md`，分支 `codex/edgeworld-dirty-tree-audit`，提交 `47851f8`。未运行测试。 |
| N2 | 发布版 UE5 插件纵切方案 | UE 5.8.3 发布版 | **完成（静态）**：`ue5_release_plugin_vertical_slice.md`，分支 `codex/ue5-release-plugin-path`，提交 `85a57a8`。未创建/构建插件。 |
| N3 | UE 许可与分发问题 | Epic 当前在线 EULA | **完成（资料整理）**：`ue_license_distribution_questions.md`，分支 `codex/edgeworld-license-boundary`，提交 `ce39e53`；非法律意见。 |
| N4 | 原型契约与计划路线 | 三份报告及用户的 UE5 发布版优先原则 | **完成（原型范围锁定）**：`phase1_4d_prototype_contract.md`；执行计划更新为 v0.3。生产级 ADR 保持开放。 |
| P1 | UE 5.8.3 Runtime 插件传输骨架 | 契约/计划基线 `203e632` 和 UE 5.8.3 安装 | **完成，待集成**：worktree `.worktrees/stage2-ue-plugin`，分支 `codex/stage2-ue-plugin`，提交 `326c113`。提供异步 JSONL `status/advance/observe` 请求构造和只读观察 Actor；UE 5.8.3 `EdgeWorldHostEditor Mac Development` 构建成功。无实际进程/pipe transport、响应解析和端到端验证；审查未发现阻断问题。 |
| P2 | Genesis 稳定 API 适配调查 | Genesis 1.4.3 PoC 与官方 API 文档；基线 `203e632` | **完成**：worktree `.worktrees/stage2-genesis-api`，分支 `codex/stage2-genesis-api`，提交 `363d23b`；报告 `doc/genesis_public_api_audit.md`。确认公开 `scene.rigid_solver.set_gravity()`、`scene.step()`、`Scene.save_checkpoint()`/`gs.Scene.load_checkpoint()`；单自由刚体 Metal 探针验证重设下一 tick 参数后的 checkpoint 续算与不中断轨迹一致。未测新 OS 进程重启或复杂 solver。 |
| P3 | edgeWorld worker 实现 | P2 API 结论和 `phase1_4d_prototype_contract.md` | **完成，主审查通过，待集成**：worktree `.worktrees/stage2-worker`，分支 `codex/stage2-worker`，基线 `292ac0d`，提交 `e143c23`（含初始提交 `2557ad2`）。提供有限单刚体 `status/advance/observe`、revision/command 幂等、Genesis 公共 API、checkpoint 和历史观察；新 OS 进程恢复、常规 JSONL smoke 及 2 项 manifest 替换/目录 fsync 故障注入通过。替换状态不确定时 fail-stop，不再服务旧 head。细节见该分支 `doc/stage2_worker_protocol.md`。 |

P1/P2/P3 已在独立 worktree 完成并由主任务审查，尚未集成。当前不允许 UE 源码修改，除非发布版针对批准契约的实测缺口经主任务审议。

## 实现阶段的拆分准则

契约通过后，可按模块和文件边界建立后续并行批次：

1. **状态与存档核心**：独立 schema、稳定 ID、检查点/迁移；拥有核心数据与持久化文件。
2. **规则调度与因果日志**：显式时间、触发依赖、候选变更仲裁、提交日志；不得同时改存储 schema，接口需先冻结。
3. **UE5 发布版宿主适配**：Runtime 插件/Subsystem 只负责生命周期接线和调用核心，优先复用现有 Renderer；不改 UE 源码。
4. **观察投影原型**：只读查询和 UE 表现层；不写权威状态，不与宿主适配任务修改同一模块文件。

每个实现任务都应写清：基线提交、允许修改目录、禁止修改目录、依赖接口版本、验收命令/证据、是否需要运行测试、分支交付方式。主任务负责审查差异、解决接口冲突和串行集成。

## 交付与集成流程

1. 主任务先公布任务卡和稳定输入版本；若有未提交成果，明确哪些作为只读输入，或先建立可引用提交。
2. 每个 Agent 在自己的 worktree/分支工作，只改认领文件；未经安排不共享写同一文件。
3. Agent 完成时报告提交号、文件清单、验证证据、限制与潜在冲突。
4. 主任务逐项审查。文档可 cherry-pick 或摘取；代码按接口顺序集成，任何失败都保留在原分支，不重置用户工作区。
5. 更新能力矩阵和阶段门；通过后才派发依赖它的实现工作包。

## 尚未完成

- 六份研究/方案报告仍在各自分支，尚未集成到主分支。
- 主工作区未提交实现已经只读审计，但没有运行测试；历史日志中的通过结果不代表当前工作树复验。
- `phase1_4d_prototype_contract.md` 只锁定有限实验边界；生产级时间、通用调度、跨平台确定性、复杂求解器恢复和产品规模仍开放。
- UE 插件已按发布版 UE 5.8.3 构建，但没有真实 worker transport、Editor 启动/渲染、cook/打包或 UE↔worker↔Genesis 端到端证据。
- Genesis 公开 API 已用单自由刚体 Metal 探针验证 checkpoint 续算；尚未验证全新 OS 进程重启、复杂 solver 或其他设备/精度。
- P1/P2/P3 交付均尚未集成。P3 已按主审查修复提交不确定错误路径；worker、Genesis API 调查和 UE 插件纵切仍是原型工作，不代表 UE↔worker↔Genesis 端到端阶段门通过。
- 本轮执行计划已更新为 v0.3，最小原型契约已建立；领域原则已同步为 UE5 发布版优先、Godot 为辅助观察端。
- 下一步：将已审查的 P1 插件、P2 API 报告、P3 worker 按依赖次序集成到主分支；随后实现/接通 UE 异步 worker process/pipe transport，进行真实 `status/advance/observe` 往返和 UE 发布版运行/渲染验收。当前 worker 只支持 Metal/macOS、单世界单写进程，`view_spec` 暂为校验并回显；JSON tick/revision 限于 IEEE-754 安全整数 `2^53-1`，长期协议再定义精确整数编码。
- UE 源码修改仍须等待发布版能力对批准契约的可复现缺口，并经主任务审议。
- P1/P2 worktree 基于原型文档提交 `203e632`；任务发布后的上下文检查点为 `df32599`。P1/P2/P3 子任务 SHA 分别为 `326c113`、`363d23b`、`e143c23`，均尚未集成。统筹上下文检查点：`001d176`（P3 发布）、`786d77d`（审查跟进）。本轮收尾后，新迭代从获取目标 worktree、载入本 backlog 和相应子任务报告开始。
