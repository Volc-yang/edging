# F0：递归 PDCA 开发过程契约提案

状态：规划提案，供统筹审查；基线 `1f7e67e`。父节点为总计划 `G` 的过程框架分支。本文只规定开发任务如何拆分、派发、检查、返工与结案，不制定游戏玩法、世界规则或物理法则。

## F0 节点的 PDCA

| 阶段 | 本任务的方法与交付 |
| --- | --- |
| Plan | 以现有 `worktree-iteration`/仓库工作流和 Chaos、Realism 已发生的任务链为输入，设计一个能表达“代码已合并但某验收门未过”的通用节点模型。固定接口：节点 ID、父子关系、DAG 边、状态、门、证据和版本。 |
| Do | 交付下述状态机、递归停止条件、拓扑派发规则、任务卡字段与变更控制。只写本文，不改运行时。 |
| Check | 静态逐项回放 Chaos P0→D1/D2/D3→D4→C1/C2→A1 和 Realism T1→V1→T1-VF→V2；确认不必伪造通过状态就能表达实际提交、合并、失败、返工与开放门。检查字段完整性与依赖无环。下文是此次规划检查结果，不是新运行测试。 |
| Act | 若回放无法表达状态，先改模型和受影响任务卡；若只是证据缺口，标 `inconclusive` 并指定补采。不修改已记录的历史 Check。统筹审查后可接受框架，或提出最小修改。 |

## 1. 状态机：工作进度与验收门分离

节点保存两个不同维度，避免“PR 已合并 = 功能完成”的误判。

**工作状态**：`draft → ready → running → submitted → reviewing → testing → settled`。`reviewing → changes_requested → running` 用于代码或方案返工；`testing → running` 用于原 owner 修复。`blocked`、`deferred` 是带原因、触发条件和保留位置的临时/终局分支，不得只留一个标签。等待依赖的节点仍为 `draft`，不能假装已阻塞。

**验收门状态**：每个预设门单独记 `planned | pass | fail | inconclusive | waived`，附阈值版本、检查者、构建/输入身份、原始证据与时间。`waived` 只能由有权裁决者记录原因、影响和替代门，不能由实现 owner 因失败自行改写。节点裁决 `accepted | rework | partial | deferred | stopped` 由门集合与预设范围得出，独立于 Git 的 `uncommitted | committed | PR-open | merged`。某个叶节点可以通过自己的门并被接受，而父节点仍待集成门；父节点必须满足所有本版本必要子节点的裁决和自己的集成 Check 才能接受。

**状态迁移约束**：

1. `ready` 要求输入与共享接口版本已固定、所有强依赖已 `accepted` 或有明确的仅供规划使用的接口冻结许可、写入路径/独占资源无冲突。
2. `submitted` 要求可审查交付和实际运行的自测记录；没有运行测试可以提交，但需把对应门记 `planned/inconclusive`，不能写通过。
3. `reviewing` 检查具体 diff、所有权、依赖版本和证据；`testing` 由非实现 owner 执行独立门。合并只是 Git 事件，不能直接跨越 review/test。
4. `settled` 必须有裁决、未通过门的处置、PR/合并或留存位置、worktree 清理状态和下一轮入口。
5. `fail` 表示执行了检查且与预设阈值冲突；`inconclusive` 表示无信号、证据不足或输入身份不明。二者的 Act 不同：前者诊断/返工，后者补采或修复测试装置。

## 2. 递归拆分与停止条件

总节点描述用户可感知的结果；里程碑节点描述一个稳定接口或阶段门；叶节点描述一个 agent 可在独立 worktree、一个 PR 内交付且另一 agent 可独立审查的工作包。继续拆分的触发条件是多 owner、共享写路径冲突、接口未冻结、不同检查者/资源必须分开、单次范围超出约定预算，或验收无法区分失败归属。

停止拆分须同时满足：一个明确 owner；独占写入范围或版本化共享接口；有限且可审查的交付；准确输入/基线；可观测的 Check 与阈值；独立复核者能复现；预计在本轮预算内完成。过细拆分同样应合并：如果两张卡总要同时改、必须一起评审且没有独立验收价值，就不应强造两个 PR。每一层子节点的 `Plan/Do/Check/Act` 结构相同，但父节点另保留跨子节点集成 Check。

## 3. DAG 拓扑与并行派发

每个子节点恰有一个父节点；`depends_on` 可指向同层或其他叶节点。父子树与依赖 DAG 分开存，依赖图须无环。新增/改边时重新拓扑排序并计算受影响下游集合。`ready` 队列仅包含依赖门已满足的节点；并行队列另检查 write set、分支基线、接口版本和独占设备/UE 进程/Worker 状态目录是否冲突。一个子任务的 agent 可以先只读研究尚未冻结的接口，但不能开始依赖它的写入实现。

建议在登记中给出 `ready_now`、`waiting_for`、`parallel_with` 和 `resource_lock`，使下一轮可直接恢复派发。实现分支从准确基线建独立 worktree；每个可独立评审的交付有自己的 PR。统筹负责跨路径接口裁决和集成；独立测试不能由同一个实现 owner 自行宣称通过。

## 4. 任务卡最小字段

```text
id, parent_id, objective, scope/non_goals, owner, status, version
base_commit, worktree, branch, PR_target, depends_on, ready_condition
input_versions, interface_versions, owned_paths, forbidden_paths, resource_locks
Plan: assumptions, ordered_steps, budget, risks, acceptance_gates
Do: outputs, commits, PR, execution_log
Check[]: gate_id, method, threshold_version, checker, environment/build/input_identity,
         raw_evidence, summary_index, result, limitations
Act: fact, hypothesis, missing_evidence, disposition, affected_nodes,
     follow_up, test_handoff, cleanup_state
```

任务卡不要求所有字段一开始都有结果；未执行项写 `planned`。原始大日志/图片可留在外部证据目录，Git 只保存可定位的索引和哈希。每轮证据绑定构建、seed、配置、动作和观察窗口；只保存过滤后的摘要不足以复查。

## 5. 变更控制与回路

- 改目标、阈值、输入基线、接口或依赖边时，生成节点新版本，记录提出者、原因、依据、受影响下游、旧/新值和裁决者。既有检查结果保留其旧版本身份，不“重新解释”为新门通过。
- 检查失败先固定原始现场，提出根因假设并说明置信度；按最小受影响节点创建返工子节点，完成后用新构建重跑该门和必要下游门。已通过且接口不受影响的并行节点保持接受状态。
- 检查无信号时仅补采或修测试装置；没有原始证据不得盲改实现。迭代次数和资源预算应由父节点限定，超限进入 `deferred` 或提交重新规划决定。
- 收尾时统筹更新 DAG、登记、backlog、PR 和证据链接，提交精简上下文，移除仅已审查集成且干净的任务 worktree。主工作区其他未提交内容保持原样。

## 6. 历史链回放 Check（仅文档证据）

| 历史事件 | 本模型中的表达 | 评价 |
| --- | --- | --- |
| Chaos P0 冻结起源契约，D1/D2/D3 可按独占路径并行；D4 依赖其接口 | P0 `accepted` 后三叶进入 `ready`；D4 仍 `draft/waiting_for` | 能表达依赖与并行；不是三个分支一提交就放行 D4 |
| Chaos C1 有限状态门通过，C2 Metal 只通过 tick 0/1 与 O1，其他门未测 | C1 状态门 `pass`；C2 每项门分记 `pass/inconclusive`，节点 `partial` | 能表达技术纵切部分通过，避免把整轮写成全通过 |
| Realism T1 PR #15 已合并、构建通过，但最初 Metal 图黑屏；V1 PR #17 发现地表缺失 | T1 Git=`merged`、构建门 `pass`、视觉门 `fail`；V1 视觉 Check=`fail` | 合并不掩盖失败，返工只影响地形视觉及下游呈现 |
| T1-VF PR #18 修正绕序，V2 PR #19 在组装场景复测 | 新返工节点 T1-VF、独立复测 V2；技术视觉门 `pass`，写实资产/实际帧时间门仍 `inconclusive` 或未满足 | 原 V1 失败证据保留；不把可见代理说成写实达标 |

此回放只检查模型是否足以表述现有记录。没有重新运行 UE、Worker、Genesis 或性能测试，不能借它升级任何历史阶段门。下一步由主任务审查 F0/F1 的字段一致性，再决定是否冻结框架和发布 G0/G1。
