# H6C 统筹复核与有限接受

2026-11-01；owner source `4ae3148a0a72465fdb481aaad38d8fd583a505ca`，PR [#69](https://github.com/Volc-yang/edging/pull/69)，集成 `0344827f5316e60fc0899e696bd73d4e02023bdf`。独立运行基线仍为 `f674483`，不因期间 U1/U5 设计文档合并而改写运行身份。

主统筹逐项阅读 [验收卡](../home-visitor-acceptance-plan.md)、[报告](report.md)、六文件 exact diff、采证/封存/验证 harness；确认产品、配置、worker 和启动器差异为空。最终 head 的 CI `verify` SUCCESS；固定 head 后合并。

## Check 实际结果

- 主统筹独立运行 `verify_evidence.py --raw /Volumes/DevSSD/Unreal/Projects/EdgeWorld/H6C-20261101/raw`（不传 output，不写证据），结果 35 个完整只读 pair、2 个推进 pair、单次 hold 内 5 个移动样本，primary PID63931、recovery PID66073 退出均 0。
- 非采证 owner `/root/visitor_path_plan` 另做只读审查：复算索引 SHA `049fdabc4cfdd29ddad733b67ea9decab4fa8b83a6a086635b5941442efd7104`，455/455 原始文件路径、大小、哈希匹配；H6B 原索引及 25/25 复用原件哈希匹配，冻结源码/启动器身份与当前版本一致。未启动 UE 或修改原件。
- 独立 reviewer 复核两次 Space 恰为 0→1→2、文件集合 2→3→4，导航/转向/Tab/阈值恢复与历史动作逐项只读；同一 UserDir 重启无新增 Advance，实际 launcher/UE 退出 0，后验无本轮 UE/worker 残留。
- 主统筹查看索引指定的原始 `full-head2-overview-attempt1/image.jpg`：显示 Metal Host、head/view tick2、Genesis engineering probe influence -48 mm、三个节点两条连线、HUD 与可访空间。它是技术代理画面，不是写实质量证据。

## 评价与 Act

接受**准确本机、显式 viewport-preflush 开发路径的有限访客组合门**：安全出生、连续走动、实际墙栏阻挡/脱离、安全阈值恢复、Tab 保位、两模式显式推进、历史纯读及重访。35 对包含诊断，不称 35 种功能；哈希完整性也不能单独证明原始操作时刻，须连同日志、输入区间和快照核对。

鼠标是获准复用的 H6B 真人动作，非 H6C 新跑；原始低层轴未记录、旧 reporter 干扰的限制保留。两次运行还执行了会 flush rendering commands 的光照诊断，因此正常退出不证明 preflush 单独修复根因或改善失败率。原默认退出路径、reporter 自身退出、正式写实/性能、载具、世界/化身物理、完整真人体验、PIE/打包/跨平台仍开放。**V-HOME 整体不转 pass。**

本卡无需返工，原始失败与其他版本证据保留。确认任务 worktree 干净、源提交为集成祖先、报告与原始索引已保留后清理该 worktree，保留分支和 DevSSD 原件；构建/GPU 已由 owner 释放。后续仅因新风险重开最小受影响节点，不重复要求已验证的人工鼠标动作。
