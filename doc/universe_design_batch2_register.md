# U 架构设计：第二批执行登记

状态：2026-11-01，v0.1，进行中。父节点 U，方案为[架构设计树](universe_architecture_design_plan.md) v0.1；用户已授权继续。范围仅 U2/U3/U6/U7 的设计交付、审查、集成与上下文收尾。U4/U8/U9 等待后续依赖，不在本批自动展开实现。

## 固定基线与派发

四张卡均从 `6f3c142aed2f67b556d87e2b649735e6c7fd4b2b` 建立独立 worktree。U1 依赖 source `a7fed69` / merge `da84aba`，U5 依赖 source `ec8bf6e` / merge `89254ab`；H6C 有限验收 source `4ae3148` / merge `0344827`。依赖设计被接受不表示新生产 wire 或世界法则已冻结。

真实仓库 `/Users/yangacan/edgeWorld/edge-world`，集成 `codex/plan-consolidation`；下表 worktree 均相对真实仓库。Git CLI 沿用仓库固定 `.worktrees/<task>` 目录，不触碰主工作区。当前三个子 agent 并行，第四卡待空闲槽，不制造重叠写入。

| 卡 / parent / depends_on | owner / 状态 | worktree / branch | 独占交付 |
| --- | --- | --- | --- |
| U2 / U / U1 | `/root/u2_physics_design` / 进行中 | `.worktrees/u2-universe-physics` / `codex/u2-universe-physics` | `doc/design/universe-physics.md` |
| U3 / U / U1 | `/root/u3_ai_design` / 进行中 | `.worktrees/u3-universe-ai-proposals` / `codex/u3-universe-ai-proposals` | `doc/design/universe-ai-proposals.md` |
| U6 / U / U1,U5 | 待空闲 agent / queued | `.worktrees/u6-universe-entry` / `codex/u6-universe-entry` | `doc/design/universe-entry.md` |
| U7 / U / U1,U5 | `/root/u7_projection_design` / 进行中 | `.worktrees/u7-universe-projection` / `codex/u7-universe-projection` | `doc/design/universe-projection.md` |

各卡 v0.1；PR 尚未建立、独立设计 Check 为 planned、新运行门 planned；worktree 活跃保留。准确最终 source、PR、merge、CI、裁决和清理在交付时逐项更新。

## 执行与门

Plan/Do/Check/Act 沿父树各卡，只写独占单份主设计、一组正反例，引用版本化输入；最多两轮定向修订。只读调查已有契约、源码与原始报告。禁止改产品、worker、现有 schema、引擎或主工作区，不跑 UE/Genesis/GPU、不下载资产、不调用付费模型。

- U2：单位/坐标/步长、物理对象到存在身份、候选数值/摘要与失败边界；工程反事实需要发展字段差异，不升为世界法则。
- U3：模型来源/输入水位/预算/有效期/权限/提案幂等/审批与命令交接；模型只提案，状态提交仍唯一权威，拒绝无世界副作用。
- U6：外部会话→载具入口→步行→退出→重访；会话/账号/化身身份分离；比较纯访问载具与权威实体载具，明确两条物理边界，不代产品选择。
- U7：当前/历史水位到 UE 可重建投影、资产/碰撞/流送/版本及平台能力；现有 BasicShapes 不算写实，授权和性能待实际证据。

每 owner 执行范围、链接、术语及正反例自检后普通 commit/push，独立 PR 到集成分支；不用 amend/rebase/force-push 重写已发布历史，不自行合并。统筹非作者核对 exact diff、输入来源及权限，再检查最终 CI；缺项只返工受影响卡。设计接受只解锁后续设计，不以 CI 或文档替代新运行证据。

父级 Check 核对 U2/U3 的候选/提案到 U4 唯一提交的接口，U6 的本地运动/权威动作与 U7 当前/历史投影边界，及跨卡 World/Existence/Avatar/Session/版本/单位用语。共享序列化仍由后续契约明确，不擅自兼容旧档。未来 U9 reviewer 须未承担 U1–U8 交付，本批局部统筹审查不替代 U9。

Act：每卡记录完成/部分/阻塞、检查与未决项；PR 审查并集成后，仅移除干净且源提交为集成祖先的任务 worktree，保留分支/报告。四卡有独立裁决后更新 backlog 和设计树、commit/push；全 U 轮与 V-HOME 产品总门保持各自真实状态。
