# I15 执行登记：公开 proof 回放与只读能力采证

2026-11-02；状态 **in progress**。输入/方案提交 `ee138aea8178f7d09082caf7448f6e1090719b11` 已在远端集成分支；[审定任务树](design/universe-i15-proof-capability-plan.md)。本登记记录执行事实，不能代替运行证据。

| 节点 | worktree / branch | 当前交付 / Check | 下一步 |
| --- | --- | --- | --- |
| N / i15_native | `.worktrees/i15-native-replay` / `codex/i15-native-replay` | C++ `eb4c0c4`；Python 回放与 review 适配尚未交付 | 完成 CPU 负例、自检、独立 PR，root 审查 |
| P / i15_probe | `.worktrees/i15-readonly-probe` / `codex/i15-readonly-probe` | C++ `997eda0`；probe_actions 与两阶段准备 helper 尚未交付 | 完成 CPU 自检与独立 PR；root 审查后才执行准备 |
| C / i15_controller | `.worktrees/i15-capability` / `codex/i15-capability` | capability.py 未提交，持续 owner/observer 尚未交付 | 与 N/P 对齐 schema，CPU 自检与独立 PR |
| R / root | `.worktrees/plan-consolidation` / `codex/plan-consolidation` | 方案已提交；实现未集成 | 审查三份交付/CI，再官方 CPU build，冻结真实 source/binaries |
| M/X/T/A | 同方案，root 唯一运行资源 owner | **尚未执行**；没有新 UE/solver/UI/Native 运行 | 依次一次 Metal → 原始响应冻结 → 一次 Native → 独立结算 |

上下文恢复时，旧三个 agent 已不在运行列表；原 worktree 与未提交文件均保留。已按原路径/所有权重新派给三个接续 agent，未另起重复实现分支。任何未提交文件不能称为完成、审查通过或已集成。

## 资源与验收边界

新独占准备 root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe` 尚未创建。root 不先手工创建，待 P 的审定 helper 独占准备。CPU 官方构建累计上限 180s；运行卡连续 dispatch 至最终 seal 上限 900s、新产物 2GiB，一次 Metal 与一次 Native，无自动重试。计划分配不是实测结果。

**执行环境修订 v2：**当前工具目录无 CUA，node REPL 实测 `cuaAvailable=false`。按方案新增明确 `skip_metal` 分支，M 标为环境缺证/未执行；若代码审查、构建与卡校验通过，可执行一次 Native 验证旧三个原始 proof。C 负责 typed 跳过证据与拒绝测试，root 复核；没有授权改用其他界面注入工具或将 skip 写为 pass。

本轮不初始化/prepare/advance/physics/retry；派生 owner 必须 existing / can_initialize=false / allowed_actions=[]。继承 r4 权威只读，不读 key 内容、不迁移或重置。标准双会话与 G-B2 仍未通过；旧 I12 2566/1200s fail、I13/I14 partial 及全部原件继续保留。旧 blocked goal 未改状态。

主 checkout `feature/edge-world` 的用户修改及 I12B 恢复树不碰。集成前所有任务树保留；当前无已完成任务清理。网站/DNS/API、引擎源码与 crash-report 发送不在范围内。
