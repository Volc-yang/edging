# UE-MAC-LAUNCH-02：跟踪实际 App 进程

日期：2026-11-01（Asia/Shanghai）。状态：修复完成，一次隔离真实启动/退出验证通过。
基线 `3ac8c0f246588d21f7c2e9500015e82b5e4874a9`（含 PR #58）；独立 worktree
`/Users/yangacan/edgeWorld/edge-world/.worktrees/ue-mac-launch`，分支
`codex/ue-mac-launch-app-pid`。父节点仍为 V-HOME 启动可靠性。

## 失败依据与修复

统筹在 `run-jq5xozmB` 实测：外层 `Binaries/Mac/UnrealEditor` PID 23653 返回 1，
实际 App PID 23676 仍运行。入口提前报告失败，随后日志才出现引擎初始化与有效
Observe。统筹用 ⌘Q 结束 App，日志正常退出。这是启动器进程与会话进程身份
混淆，不能据外层退出 1 判断实际 UE 会话失败。
[原状态](before-status.log)与[UE 时间线摘录](before-ue-excerpt.log)保留该矛盾。

修复仅把可执行路径改为官方安装版
`Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor`；注释说明原因。
`$!`、TERM 转发、`wait` 和退出码因此针对实际 App。项目/worker 绝对路径、
UserDir 隔离、Build.sh、Engine initialized / GameMode / validated observation
各阶段及退出判定全部保留。不修改 GameMode、Runtime、worker 或 UE 引擎。

应用 code-complete-2 调试检查：先对照 PID/退出与日志时间线定位失败边界，再做
最小修复，以真实进程身份和完整会话退出验证，不把构建成功替代运行验收。

## 真实 Check

统筹明确确认诊断任务已释放 GPU，并授权本次真实测试后执行。启动前未见 UE
或 causal worker 实例。新 worktree 官方 UE 5.8.3 / CL 58210709 Mac Development
预构建 30 动作成功（27.31 秒）；`--launch` 再构建为 up to date，退出 0。
环境为 `/Users/yangacan/edgeWorld/edge-world/.venv-genesis/bin/python`。

一次 `scripts/launch_edgeworld_ue_mac.sh --launch`，默认生成独立
`Saved/MacLauncher/run-E3yXBxHN/user`，未复用统筹状态目录：

| 检查 | 证据与结果 |
| --- | --- |
| 实际进程身份 | [进程快照](running-processes.log)：脚本 PID 24962 的直接子进程 25039，命令是 App 内可执行文件，与 `process_spawned pid=25039` 一致 |
| Worker 隔离 | PID 25224 的父进程为 25039；worker 脚本和 `--state-dir` 均指向本 worktree/此次独立 UserDir |
| GameMode | 运行中出现 `gamemode_startplay_seen` 与 Causal world StartPlay 日志 |
| 引擎初始化 | 12:19:32.862（原始 UTC 04:19:32.862）出现 `Engine is initialized. Leaving FEngineLoop::Init()`；入口记录 `engine_initialized_seen` |
| 有效 tick 0 | 12:19:36.624（UTC 04:19:36.624）日志为 `Causal world stg-demo observed tick 0, revision 0`；入口记录 `validated_observation_seen` |
| 正常退出 | CUA 选取准确 `UnrealEditor.app`，看到 SF_METAL_SM6 场景与 tick0 HUD 后按 ⌘Q；12:20:15.946 RequestExit，12:20:16.810 LogExit: Exiting |
| 实际退出码 | shell 工具等待入口得到退出 0；入口 `ue_exit_code=0`，最终三项阶段标记均为 1，报告 `session_exited_cleanly` |
| 无残留 | [退出后进程检查](after-processes.json)无 UE 或 causal worker；原脚本/App/worker PID 均已不存在 |

[最终状态](after-status.log)、[UE 时间线摘录](after-ue-excerpt.log)、
[原始日志哈希索引](raw-index.json)。原始 build/status/UE/console/command 与入口
输出完整保存在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/LauncherAppPID-20261101/`，
不是只保留摘录。未执行截图控制台命令，未推进权威状态。

`/bin/bash -n`、`git diff --check` 通过。此次修复后的真实 App PID、启动阶段和
正常退出处理已验证；TERM/Ctrl-C、非零异常退出和共享目录并发仍未另外测试。
单次正常退出不关闭 `SceneViewport.cpp:196` 间歇性可靠性门，也不代表视觉/性能
或 PIE 门通过。窗口可见未作为正式视觉验收；画面仍提示未烘焙灯光。

下一步：统筹审查修复 PR 并集成，后续使用本入口采集运行状态；GPU 已释放，
本任务未留下 UE/worker。不要将本修复描述为视口断言根因修复。
