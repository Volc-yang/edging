# H1g 标准启动器显式同步接线

状态：代码准备和静态/mock 验证完成；真实运行验收等待统筹明确交接构建/GPU 资源。
父卡：[viewport-preflush-launch-plan.md](../viewport-preflush-launch-plan.md)。
准确基线：`c8209331f976360a92a9d3f3b5dad6e4fffbc666`。
分支：`codex/g3-preflush-launch`；独立 worktree：
`/Users/yangacan/edgeWorld/edge-world/.worktrees/g3-preflush-launch`。

## 修改边界

只改 `scripts/launch_edgeworld_ue_mac.sh`、现有
`tests/test_unreal_mac_launcher.py`、`doc/ue_mac_launch.md` 和本报告。
不修改 viewport/client、GameMode、worker、世界规则或光照文件；主工作区
用户未提交文件保持原样。使用 Code Complete 2 的边界校验、控制流和定向
行为测试检查（Ch. 8/15/22/29）；不扩大到引擎或运行时实现。

新增 `--viewport-preflush`，默认关闭。解析阶段拒绝与 `--no-render-thread`
组合，早于引擎探测、输出目录创建、构建和启动。布尔参数只在构造 UE 参数时
追加一次 `-EWDiagPreflushViewport`，重复传入仍只有一次；保留默认线程。
状态日志明确请求模式、有限项目旁路和性能代价未测。原有构建失败提前返回
路径不变，没有自动回退。

## 静态和 mock 验证

2026-11-01 完成以下检查：

- `bash -n scripts/launch_edgeworld_ue_mac.sh`：退出 0。
- `python3 -m unittest tests.test_unreal_mac_launcher -v`：8 项通过，7.109 秒，退出 0。
- `git diff --check`：通过。

覆盖默认仅构建、默认启动不带两个旁路参数、原 no-render-thread 路径、新参数
重复输入但仅转发一次、两种顺序的冲突在 build-only/launch 下均于构建前返回
64、两种旁路的构建失败不启动、build-only 不声称启用运行模式。
构建 mock 的独立标记文件验证冲突时 Build.sh 未执行；假 App 参数记录验证
没有悄悄添加另一线程模式，日志说明与请求参数一致。
Mock 使用临时目录中的假 Build.sh 和假 App，只验证启动器分支、参数和日志，
不执行真实 UBT/UE/Worker/Genesis。

## 待交接后的真实验收

本阶段没有执行 UBT/build、真实 UE/Worker 或 GPU 任务。H-LIGHT-01 独占资源，
未经统筹明确交接不启动真实验证，也不以 mock 代替运行验收。

后续须使用该准确基线上的实现和真正标准脚本，在独立 UserDir 采集构建、
实际 App/Worker PID、初始化、有效观察、首图、显式 Advance、历史/相机只读
全文件比较、关窗、同目录恢复、退出码及精确清理。UE 日志须证实默认线程、
正确游戏窗口/GameThread、非空 owner 和同步后 owner 不变。失败原始证据保留，
不换模式回退。完成真实验收后再做独立 scoped commit/PR 到
`codex/plan-consolidation`，当前不提交完成 PR。

H1f 的有限显式旁路接受不等于本启动器已获真实接线验收；默认线程原始路径、
其他窗口/PIE/平台和产品可靠性门继续开放。
