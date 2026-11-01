# H1e 独立审查

日期：2026-11-01。审查者：统筹派发的 `h1e_independent_review`，非实现 owner。
输入：PR #62 / `de4e306`；统筹基线 `15ab1ec`。

裁决：接受为默认关闭的有限诊断候选；默认线程可靠性仍 `fail/open`。
CI 通过，统筹与独立审查均复算 396/396 原始证据哈希。安装版 UE 的通知先于
游戏 viewport owner 释放，候选使用公开扩展点、精确窗口匹配和弱 UObject
delegate，未替换原生关闭处理器。单窗口 Standalone 已测范围内无明确死锁、
所有权循环或悬空委托；全局 subclass 配置不代表默认启用同步。

重复 Init 可覆盖 handle 并留下同一存活 client 的旧绑定。该问题不阻塞当前
一次 Init 的有限诊断集成，但 H1f 必须先补幂等注册和解绑检查，再用新 binary
重做无 reporter 干扰的矩阵。报告中 B1 的 reporter 重叠保留，不计为完全受控
环境。两个干净 B 样本不足以证明根治或失败率改善。

`FlushRenderingCommands` 会广播事件并等待渲染任务；其他监听器或关闭回调
还可能在同步后提交新渲染任务，当前实现没有覆盖所有路径的生命周期不变量。
任意回调组合下的无重入/无死锁、多窗口、PIE 和平台泛化仍未验证。

H1f 验证与裁决见 [复测卡](../g3-viewport-preflush-followup-plan.md)。任何 B
断言、挂起或生命周期异常均拒绝候选；干净样本最多支持有限显式旁路。
