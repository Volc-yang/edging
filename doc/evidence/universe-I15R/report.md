# I15 R：持续控制器 CLI 接线

2026-11-02；root 实现，i15_native 非 owner 只读审查。输入 `f8f07fe`，仅新增共享 CLI 的 I15 固定命令入口及定向测试；旧 R13 函数和命令分支不改。依赖已审定的 N/P/C 接口，不授权运行，不修改旧验收门。

`i15-controller` 在准确卡/输入 SHA 和显式 execute 校验后创建唯一持续父进程，复用有界非阻塞 JSONL framing，暴露固定方法，不允许任意属性、代码、shell 或额外 argv。UI 在外部执行。EOF/部分帧/超长帧/900s deadline 的 finally 保留 abort 清理责任；实际 Native parent wait 由 C 独立记录。

实际 CPU 检查：6 项 I15 协议测试通过，8 项旧 integration 回归通过。首次新增 EOF 测试因 import 顺序失败，修正后通过。独立审查发现 EOF/deadline abort 仍可能返回 CLI exit0，已修正为 `normal=false/status=aborted`，由 main 返回 exit2；显式 seal 不额外 abort。i15_native 复跑 6 项并接受修复。所有 CPU mock 检查只是接线行为，不是 UE 运行证据。

当前代码交付待独立 PR/CI/集成；真实 build、Native replay、Metal 输入/PNG/标准双会话均不能由本报告宣称通过。后续运行与 root 结算见 `doc/universe_i15_execution_register.md`。
