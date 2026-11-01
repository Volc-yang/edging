# U4 单权威事务设计：独立审查与集成 Check

2026-11-01；parent=U。派发基线 `3b5044debd8008eddbcc4c1fa85e45a8d43da217`；初稿 `b3d3740`，最终 source `28122b7cbfdb14a16c2c3a75887445cae75b9c59`；[PR #74](https://github.com/Volc-yang/edging/pull/74)，merge `09ef8cb034cd4b5ef8339705647dc81ac386cd69`。

工作完成、PR merged、**有界设计门 pass**。主统筹 `/root` 与独立 reviewer `/root/u3_ai_design` 均未编写 U4 文档。只接受[该设计](universe-commit-recovery.md)作为后续版本化输入，不批准新 wire、世界规律或运行保障；本次不替代 U9。

## 发现、修订与复核

初稿只要求恢复时校验可见完整旧/新 root。两位审查者独立确认一项阻断：若进程死于 replace 可见点 V 后、目录同步确认点 D 前，操作系统未重启，新 root 可读且 hash 正确，仍不能推断先前 D 成功。若立即确认原命令或接受新写，便混淆完整性与耐久性。

普通追加提交 `28122b7` 补入 `D_recovery`：同 writer 锁内固定并校验 root 后，按存储 profile 同步必要工件与目录、manifest/authority 目录，完成重新确认再恢复确认响应及写入；同步/保障未知继续停写，只能提供显式未确认、完整且不求解的只读结果，损坏则拒读。W5/W6/W7 与 P1 同步条件，不新增世界事件、不重复原命令。独立 reviewer 重读 exact diff 及对应段落，原阻断关闭，无新增阻断。

## 实际执行的 Check

- 主统筹完整阅读初稿、最终修订及上游 U1/U2/U3/U6/U7；最终 range 仅新增 `doc/design/universe-commit-recovery.md`，未改产品、worker、配置、旧档或 UE 引擎。
- 主统筹与 reviewer 分别核对 8/8 本地相对链接存在；`git diff --check` 通过，W0–W9 十个写点各列一次且有恢复预期与失败信号。
- 审查锁覆盖初始化、恢复、求解、发布及退出；稳定 fd/锁 inode 不按 PID 或超时删除夺权；当前代码只有线程锁的缺口保留，跨进程锁运行门未执行。
- 独立按描述追踪摘要依赖；主统筹另外对抽象依赖图做拓扑检查：proposal→semantic command→approval→最终指纹→candidate→准入 receipt；state/event→result→去重索引→manifest，无自引用环。这里只检查设计图，不证明 canonical 实现或实际重演正确。
- 核对审批/准入 A、可见 V、确认 D 与恢复确认分离；持久命令结果先于新动作有效期/head/预算检查返回，可信读取授权仍须检查；物理、发展、事件、随机游标、动作预算和幂等结果同 root。
- 核对外部模型费用/审批/预留账簿独立恢复域、不虚构跨系统原子性；历史校验全部保留引用、不补求解；离线逐步有界、每步独立提交和稳定命令，失败不承诺整批回滚；版本迁移保留旧字节/hash。
- GitHub connector 核对 exact head/base/单文件范围，CI `verify` SUCCESS（run `41307013938` / job `124849375023`，head `28122b7…`），按 expected head 合并成功；本地 fetch/fast-forward 后确认 source 是集成祖先。
- 任务 worktree 确认干净后已移除，分支/PR/报告保留。没有启动 UE/Genesis/模型，没有故障注入、锁竞争或耐久性实测。

## 实施前仍需冻结

1. 存储 profile 的准确同步顺序、FS/OS/full-sync 语义及 `D_recovery` fixture；当前 DevSSD 的 APFS 类型只是只读环境观察，不是断电保障证据。旧故障测试针对旧 worker，且同步异常在实际 sync 后注入，不外推为组合事务或掉电验证。
2. A 后撤销/到期语义、A→V 时间与发布上界。固定审批 receipt 可以定义 A 后变更作用于后续动作，但仍是待接受的具体契约；两个 HTTP 读不构成即时撤销原子保证。
3. 外部必要 reservation 的有效期、不可撤销性或重新确认、幂等结算及未知状态处理；未冻结或状态未知不能放行需要该保障的动作。
4. canonical 精确字节/typed float、ID 分配与引用命名、规则/随机调度及迁移 fixture；不能将候选接口静默应用到旧 S4 存档。

上述新运行门全部 planned；真实世界法则、载具权威性、写实/性能阈值及原默认退出可靠性继续开放。失败只重开受影响节点。

## Act

接受 U4 有界设计，**下一 ready 为 U8 规模与质量预算设计**（U2/U4/U6/U7 设计依赖已满足）；U9 仍等 U8，由未承担 U1–U8 交付的 reviewer 完成最终跨卡审查与实现树。U 总轮与 V-HOME 产品总门不因 U4 文档合并关闭。
