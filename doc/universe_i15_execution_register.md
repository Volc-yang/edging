# I15 执行登记：公开 proof 回放与只读能力采证

2026-11-02；状态 **in progress**。输入/方案提交 `ee138aea8178f7d09082caf7448f6e1090719b11` 已在远端集成分支；[审定任务树](design/universe-i15-proof-capability-plan.md)。本登记记录执行事实，不能代替运行证据。

| 节点 | worktree / branch | 当前交付 / Check | 下一步 |
| --- | --- | --- | --- |
| N / i15_native | `.worktrees/i15-native-replay` / `codex/i15-native-replay` | PR115 `1872a91` → `274d090`，CI41439049209 success；root 13新+21旧 CPU 通过 | 实际 Native 与独立结算待执行 |
| P / i15_probe | `.worktrees/i15-readonly-probe` / `codex/i15-readonly-probe` | PR116 `48ba395` → `e51dcf8`，CI41439556996 success；root 12新 CPU 通过（owner43含旧回归） | 构建发现 RHI link 缺口，单独纠正卡处理中 |
| C / i15_controller | `.worktrees/i15-capability` / `codex/i15-capability` | PR117 `f50d627` → `6825f04`，CI41439782359 success；root最终12 CPU含真实child/timeout通过，N独立审查 | 准确卡准入与实机 Native 待执行 |
| R / root | `.worktrees/i15-integration` / `codex/i15-integration` | PR118 `58f1baf` → `e52e4b8`，CI41439859086 success；N独立审查；root6新+8旧检查通过 | 成功构建后冻结并执行 |
| M/X/T/A | 同方案，root 唯一运行资源 owner | **尚未执行**；没有新 UE/solver/UI/Native 运行 | 依次一次 Metal → 原始响应冻结 → 一次 Native → 独立结算 |

上下文恢复时，旧三个 agent 已不在运行列表；原 worktree 与未提交文件均保留。已按原路径/所有权重新派给三个接续 agent，未另起重复实现分支。任何未提交文件不能称为完成、审查通过或已集成。

## 资源与验收边界

新独占准备 root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe` 已由审定 P helper 完成默认 audit 后显式独占创建；preparation SHA `0a3eadac82a5b9152e2310b37c206db97efc3e5a1ff61553a4f3bdd841215f49`。产品构建树 `.worktrees/i15-native-build` 固定初始 source `e51dcf8`；工具树与产品树分离。

首次官方 CPU build 实际 parent wait **exit6**，32.628994125s，无强制清理、未启动 UE。原件 `prep/build-console.log`、`prep/build-raw.json`；arm64 链接明确缺 `_GDynamicRHI`。只重开 P 的 Host Build.cs RHI 模块依赖；允许保留原准备/失败，独占发布绑定修正准确 source 的 corrected preparation 后重构建。不得修改旧原件或假装同源成功。CPU 累计上限180s，尚余约147s；运行卡还未 dispatch，global900s/新产物2GiB规则不变。

**执行环境修订 v2：**当前工具目录无 CUA，node REPL 实测 `cuaAvailable=false`。按方案新增明确 `skip_metal` 分支，M 标为环境缺证/未执行；若代码审查、构建与卡校验通过，可执行一次 Native 验证旧三个原始 proof。C 负责 typed 跳过证据与拒绝测试，root 复核；没有授权改用其他界面注入工具或将 skip 写为 pass。

本轮不初始化/prepare/advance/physics/retry；派生 owner 必须 existing / can_initialize=false / allowed_actions=[]。继承 r4 权威只读，不读 key 内容、不迁移或重置。标准双会话与 G-B2 仍未通过；旧 I12 2566/1200s fail、I13/I14 partial 及全部原件继续保留。旧 blocked goal 未改状态。

## 实际构建与首个控制器中止

PR119 `a29c3e5` → `d648bed` / CI41441093823 success；PR120 `89f66fc` → `5a6cca0` / CI41441120674 success，经 N 非 owner 审查。修复 RHI 直接依赖与实际 Mac lib-prefixed 产物定位。官方 build2 准确 source `5a6cca0`，parent wait0、6.841072875s；两次累计39.470067s<180。`prep/build-receipt.json` SHA85988e89bce7f6f4d0327a27dde58947f970664c3b5c9c2dc19a8ed399cbc6d2，原失败与 corrected preparation 分别保留；prepared 原件152f968c、old3 manifest1c17bf1a。N 独立核真实源码/二进制/RPATH/原始trace并放行能力专用 Native 路径，不是运行通过。

`capability/` 实际首 dispatch1182671.669250291；观察线程把 skipped Metal 当作有 PID 的阶段，`start_native` 被拒绝，未创建 UE Popen。原 CLI transcript/requests/outer wait2 与 abort 原件保留，不能称 Native fail 或 pass。方案 v3 只允许修复前 dispatch 缺陷后使用尚未消耗的唯一 Native 窗口；新卡/新 prepared/新 controller 目录明确版本化，900s 从此首次 dispatch 连续计，不重置。

主 checkout `feature/edge-world` 的用户修改及 I12B 恢复树不碰。集成前所有任务树保留；当前无已完成任务清理。网站/DNS/API、引擎源码与 crash-report 发送不在范围内。
