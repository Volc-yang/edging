# I 实现轮统筹登记

状态：2026-11-01，v0.1，执行中。用户已明确同意[U9任务树](design/universe-integration-review.md)，要求分配subagents并实现；原U设计轮不重开。目标为I0–I12有界内核、新域Genesis/UE接线与独立组合验收，延期X分支不被默认为当前必需范围。

## Goal 与基线

现有goal“继续执行计划”仍为blocked且未结束；本轮显式调用create_goal被工具拒绝，原因是已有unfinished goal；当前API没有resume入口。没有将旧goal虚假complete或覆盖它。本轮继续按用户授权推进，以本登记保存里程碑，不宣称goal面板已active。

真实仓库 `/Users/yangacan/edgeWorld/edge-world`，集成分支 `codex/plan-consolidation`。启动基线 `b3e1fd4fac69ce7d78bf5c14a4d8ed554622048c`；主工作区 `feature/edge-world` 用户改动保留。仅依赖/契约/独立Check和资源门满足的卡可派发，后续每卡绑定届时准确输入SHA和独占worktree，不从移动基线各自猜接口。

## 节点、所有权与阶段门

| 卡 | owner / worktree / branch / base | 工作 / PR / 门 / 清理 |
| --- | --- | --- |
| I0 契约+可执行黄金fixture | `/root/u9_architecture_review`；`.worktrees/i0-universe-contract` / `codex/i0-universe-contract` / `b3e1fd4` | 进行中 / 未建 / G-C planned / 活跃保留 |
| I1 codec/records | 待G-C后绑定 | queued / 未建 / planned / 未建worktree |
| I2 ownership/进程锁 | 待G-C/G-S0后绑定 | queued / 未建 / planned / 未建worktree |
| I3 store/提交 | 等I1/I2/G-S0 | queued / 未建 / planned / 未建worktree |
| I4 commands/admission/rules | 等I1/I3 | queued / 未建 / planned / 未建worktree |
| I5 recovery/observe | 等I1/I3 | queued / 未建 / planned / 未建worktree |
| I6 无GPU独立故障验收 | 非I1–I5实现owner，待依赖 | queued / 未建 / G-S1 planned / 未建worktree |
| I7 物理fixture/API契约 | 待G-C后绑定 | queued / 未建 / G-P0 planned / 未建worktree |
| I8 真实Genesis新适配 | 等I6/I7/G-S1/G-P0/R-8 | queued / 未建 / G-P1 planned / 未建worktree |
| I9 UE新域严格解析 | 等I0/I7/G-B0 | queued / 未建 / planned / 未建worktree |
| I10 单root worker/初态 | 等I6/I8/G-S1/G-P1 | queued / 未建 / planned / 未建worktree |
| I11 Host/启动接线 | 等I9/I10/G-B0/R-B | queued / 未建 / G-B1 planned / 未建worktree |
| I12 独立组合验收 | 非相关实现owner，待I10/I11/G-P1/G-B1/R-12 | queued / 未建 / G-B2 planned / 未建worktree |

worktree均相对真实仓库固定`.worktrees/`；详细文件所有权、P/D/C/A与图见U9。I0目前只写 `doc/contracts/universe_authority_v0_1.md`、`doc/fixtures/universe_authority_v0_1/`、`scripts/validate_universe_authority_fixtures.py`。未提交输入不复制到子worktree；不得改旧S4领域/存档来迁就新schema。

## 已发布执行额度与审查分工

I0正式获得本地stdlib无GPU检查额度：单次≤120秒、至多一次定向重跑、原件≤64MiB；不安装依赖、不运行UE/Genesis/模型，不写world状态。八份设计中候选75分钟/16GiB没有自动转为运行授权。

I0由`/root/u2_physics_design`准备非作者黄金bytes/hash复算与对抗审查；`/root/u7_projection_design`只读检查现Runtime envelope/UE兼容边界。这两项当前不是I1/I7提前实现。G-C未接受不派依赖实现，G-S0由精确local存储契约/锁和同步预期另裁决，不误用G-S1结果当自身前置。

采用code-complete-2的构造检查重点为Ch3需求/成功条件、Ch8边界验证、Ch12编码/单位/范围、Ch22行为正反验证，结合协作/范围检查；当前风险是新共享契约与持久化/并发接口，使用新domain与旧档隔离，保留原失败。已有用户授权覆盖本树实施和独立PR集成，不额外制造重复审批。

## 通用交付与收尾

每卡固定base/输入/独占文件、普通commit、独立PR到集成分支；owner自检、非作者审查、父级集成和真实阶段门分别记状态。黄金期望由独立算法/来源复算，不用同函数生成并验证自证。源提交/PR不等阶段门通过；未执行记planned，缺证inconclusive，真实失败保留并最小返工。

GPU/UE构建窗口按前置已满足的具体卡登记实际owner/环境/预算；测试只作用于隔离目录与精确进程，未知提交遵D_recovery/停写，不全局清理。每卡经审查/CI合入后确认干净且source为集成祖先才清理worktree，保留报告/分支/原件。阶段交付和最终收尾都更新backlog、精简上下文并commit/push；仍有活跃节点不称I轮或产品完成。
