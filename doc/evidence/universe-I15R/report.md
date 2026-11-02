# I15 R：持续控制器 CLI 接线

2026-11-02；root 实现，i15_native 非 owner 只读审查。输入 `f8f07fe`，仅新增共享 CLI 的 I15 固定命令入口及定向测试；旧 R13 函数和命令分支不改。依赖已审定的 N/P/C 接口，不授权运行，不修改旧验收门。

`i15-controller` 在准确卡/输入 SHA 和显式 execute 校验后创建唯一持续父进程，复用有界非阻塞 JSONL framing，暴露固定方法，不允许任意属性、代码、shell 或额外 argv。UI 在外部执行。EOF/部分帧/超长帧/900s deadline 的 finally 保留 abort 清理责任；实际 Native parent wait 由 C 独立记录。

实际 CPU 检查：6 项 I15 协议测试通过，8 项旧 integration 回归通过。首次新增 EOF 测试因 import 顺序失败，修正后通过。独立审查发现 EOF/deadline abort 仍可能返回 CLI exit0，已修正为 `normal=false/status=aborted`，由 main 返回 exit2；显式 seal 不额外 abort。i15_native 复跑 6 项并接受修复。所有 CPU mock 检查只是接线行为，不是 UE 运行证据。

PR118最终58f1baf经独立review/CI41439859086 success合入e52e4b8。实际一次CLI dispatch完成skip与旧3manifest冻结，但C观察器访问skipped阶段的缺PID而拒绝start_native；outer parent wait2正确反映异常中止。C最终PR121修正经独立16项CPU/CI成功合入077548e，未重新实跑。所有中止/来源/预算的实际结算见[登记](../../universe_i15_execution_register.md)和[A独立review](../universe-I15A/report.md)。没有Native replay、Metal输入/PNG或标准双会话通过声明。

官方构建源5a6cca0最终exit0，前后累计39.470s；旧失败保留。完整campaign771.428s/保守1,471,501,078B有界，但全周期observer缺口仍fail/inconclusive。39项公共原件逐项hash见[runtime-evidence-index.json](runtime-evidence-index.json)。四个干净任务树已non-force结算，构建/旧世界恢复树及全部分支、原件保留，[清理记录](worktree-cleanup.json)。当前父节点partial，下一轮直接执行准确新卡的Native-only old3实际回放。
