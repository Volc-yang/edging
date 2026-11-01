# U4 事务、调度与恢复：执行登记

状态：2026-11-01，v0.2，本卡设计交付完成；U 总轮继续。parent=U，依赖 U1/U2/U3 已接受设计；依据[架构树](universe_architecture_design_plan.md)与[第二批审查](design/universe-batch2-integration-review.md)，用户授权继续执行下一步。

## 任务卡

- Owner：`/root/u2_physics_design`；非作者只读 reviewer：`/root/u3_ai_design`，主统筹另做集成 Check。本次不是 U9 最终审查。
- 准确基线：`3b5044debd8008eddbcc4c1fa85e45a8d43da217`；输入 source U1 `a7fed69`、U2 `b78b3ab`、U3 `9f2fe7e`，同时对齐 U6 `95903b2` 与 U7 `38f8e02`。
- 真实仓库 `/Users/yangacan/edgeWorld/edge-world`；worktree `.worktrees/u4-universe-commit-recovery`；分支 `codex/u4-universe-commit-recovery`；PR target `codex/plan-consolidation`。
- 唯一写入 `doc/design/universe-commit-recovery.md`。主工作区、产品、worker/schema、UE/引擎/配置及其他文档不改；可只读现有实现和故障测试。
- Plan/Do：明确单机本地盘互斥、单一提交、规则/随机源调度、版本化候选与命令引用、崩溃窗口、恢复/迁移和有界离线结算；至少一正例和逐写点失败矩阵。外部模型/账簿不虚构跨系统原子事务。
- Check：owner 范围/链接/差异自检；非作者对照 exact source 做故障与重复/恢复审查；统筹核对 U1–U3/U6/U7 兼容、最终 PR/CI 与局部集成。未来真实故障注入和物理/进程锁运行门为 planned。
- Act：有阻断只返工本卡，最多两轮定向修订；通过仅接受版本化设计，放行 U8 后续设计，不批准世界法则、新 wire 或产品运行。
- 资源：一份主文档，不启动 UE/Genesis/GPU/模型、不安装依赖、不下载资产。单卡普通 commit/push/PR，不自行 merge、不重写已发布历史。

## 状态与收尾

工作：完成；PR [#74](https://github.com/Volc-yang/edging/pull/74) merged；初稿 `b3d3740`，最终 `28122b7cbfdb14a16c2c3a75887445cae75b9c59`，merge `09ef8cb034cd4b5ef8339705647dc81ac386cd69`。owner、非作者审查和局部集成设计门 pass，新运行门 planned。恢复耐久性阻断经 D_recovery 修订关闭，实际检查及限制见[审查](design/universe-u4-integration-review.md)。最终 CI verify SUCCESS；确认干净和祖先后已移除本卡 worktree，分支/报告保留。

U8 后续已交付接受，见[登记](universe_u8_execution_register.md)；当前 U9 ready、尚未派发。现有 V-HOME 有限访客结果与原默认退出可靠性、写实/性能等开放门不因本卡文档改变。
