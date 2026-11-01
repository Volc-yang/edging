# UE-MAC-LAUNCH-01 检查报告

日期：2026-11-01。状态：预构建入口实现及 Mac 构建完成；真实启动分支未验。
父节点：V-HOME 启动/运行可靠性优先级。单一边界实现任务，不派生子 Agent。

基线：`6bc1740966f612d189cbdefb45ffebf479299724`（`codex/plan-consolidation`）。
worktree：`/Users/yangacan/edgeWorld/edge-world/.worktrees/ue-mac-launch`；
分支：`codex/ue-mac-launch`。没有复制主工作区的脏改动。

独占交付：`scripts/launch_edgeworld_ue_mac.sh`、`doc/ue_mac_launch.md` 和本文目录。
不改 GameMode、Runtime、worker、UE 引擎或统筹 backlog。入口固定本 worktree
项目和 worker；构建成功后方可显式 `--launch`，默认只构建。

## Check

- `/bin/bash -n scripts/launch_edgeworld_ue_mac.sh`：通过（系统 Bash 3.2）。
- `--help`：退出 0；非法参数：退出 64，无构建/UE 启动。
- 官方安装版 UE 5.8.3 / CL 58210709，Mac SDK 27.2，Xcode Clang 21.1.6；
  `EdgeWorldHostEditor Mac Development -Project=<本 worktree 绝对路径> -WaitMutex`。
- 首次新 worktree 构建执行 30 个动作，UBT `Result: Succeeded`，32.59 秒。
  初次启动构建后修改了仍在执行的 shell 文件，造成构建后状态输出
  `build_rc: unbound variable`。这是本次验证操作错误，不能算入口通过；详见
  [初次完整输出](initial-build-console.log)。此后固定脚本文件再复跑。
- 最终脚本 `--build-only`：官方构建 0 个动作 / target up to date，
  `Result: Succeeded`，2.97 秒；入口实际退出 0，状态记录
  `build_exit_code=0` 和 `build_only_complete; runtime_not_tested`。
  [最终完整输出](final-build-console.log)。
- 最终复跑出现 `CppDependencyCache - There is no partition covering path ...`，
  UBT 仍明确成功。保留完整日志，不根据单一告警关键字把成功报告为失败。
  本轮未出现 Win64/Linux SDK 警告；对其分类为构建退出码优先是入口行为，
  不是伪称观察到了那些警告。
- 人工核对 Build.sh 与 tee 的退出码分离、绝对项目/worker/UserDir/abslog、
  显式 Entry 地图与 Causal GameMode、有效观察与退出失败分离、空/坏参数处理。
  应用技能 code-complete-2 的需求、边界错误处理、工具验证和诚实证据检查。

最终入口 SHA-256：`3ff544f6aa91e7c225b9a69f128707d0c796a87bd9eb2fa2db1a290b31031d25`。
首次/最终官方 build.log SHA-256 分别为
`72f057a5b9f69645d405e084c682751815c8fe4204522b9ee47802d39ced2a66` /
`66a43c21b309e7f14f7c31ad5eeaa4dc47936633320b044ca43ba7a0c29e3963`；
原文件位于该 worktree 的 `engine_platforms/unreal/EdgeWorldHost/Saved/MacLauncher/`
下 `run-SL0EeHM6/` 与 `run-Xpj8lafA/`。

## 限制与下一动作

未启动任何新的 Metal UE 实例，遵守退出可靠性诊断任务的 GPU 独占边界。
`--launch` 的进程/日志监测、真实失败构建的透传、Ctrl-C 转发和复访 UserDir
仅经静态审查，未作运行验收；本轮没有添加假引擎测试来替代真实 UE 证据。
解释器是否具备 Genesis 依赖在运行时才可确认。脚本不设初始化超时；长时间
无观察会持续等待直至用户退出，最终缺少证据时返回 70。

这是 Missing Modules 体验改善，不能证明首次双击提示已消失，也不能修复或
关闭 `SceneViewport.cpp:196` 运行/退出断言。GameMode 日志与有效 Observe 不代表
画面验收通过。下一步由统筹审查 PR，待 GPU 放行后以本入口验证准确项目、
GameMode、worker argv、有效观察、退出码及残留进程；任何视口崩溃另交诊断 owner。
