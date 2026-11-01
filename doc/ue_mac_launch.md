# UE 5.8.3 Mac 预构建启动入口

入口：`scripts/launch_edgeworld_ue_mac.sh`。在每个新 Git worktree 直接双击
`.uproject` 前，先构建该 worktree 的 `EdgeWorldHostEditor Mac Development`，
减少缺少 `EdgeWorldHost` 模块的首次重建提示。脚本不修改 UE 引擎源码或项目配置。

从任意目录以脚本绝对路径调用也可；项目根由脚本自身位置确定，不使用调用者的
`pwd`，不复用其他 worktree 的 Binaries。

```sh
# 默认仅构建：可用于当前 GPU 诊断期间
scripts/launch_edgeworld_ue_mac.sh --build-only

# 等统筹放行 GPU 后，使用已装 Genesis 1.4.3 的绝对 Python 路径启动
export EDGEWORLD_CAUSAL_PYTHON=/absolute/path/to/genesis-env/bin/python
scripts/launch_edgeworld_ue_mac.sh --launch
```

`UE5_ROOT` 默认 `/Users/Shared/Epic Games/UE_5.8`；可设置其他绝对安装路径。
入口检查 `Build.version` 为 5.8.3、`InstalledBuild.txt` 和官方
`Engine/Build/BatchFiles/Mac/Build.sh`。它调用官方脚本，保存真实构建退出码
（而非 `tee` 的退出码）。任何非零退出码立即返回，不启动 UE。Win64/Linux 等
非 Mac SDK 提示不单独作为 Mac 构建失败；Mac SDK/编译器错误必须按退出码与
完整 `build.log` 诊断。退出 0 的构建仍应按日志评估其中与任务有关的警告。

启动使用安装版 `UnrealEditor`、本 worktree `.uproject` 绝对路径，以及明确的：

```text
/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode
-game -log -windowed -ResX=960 -ResY=600 -UserDir=<isolated absolute directory> -abslog=<absolute ue.log>
```

不继承其他 worktree 的 `EDGEWORLD_CAUSAL_WORKER`，始终指定当前
`engine/edgeworld_worker/abstract_causal_worker.py`。Python 环境须由调用者提供，
脚本不安装依赖，也不把解释器可执行等同于 Genesis 可用。

每次运行生成 `EdgeWorldHost/Saved/MacLauncher/run-XXXXXXXX/`，含 `build.log`、
`status.log`，启动时另含 `command.txt`、`console.log` 和 UE 生成的 `ue.log`。
默认 UserDir 为该次目录下的 `user/`，因此每次为独立状态。需要重访持久世界时，
用 `--user-dir /absolute/isolated/path` 指定此前目录；不要同时启动两个共享该目录
的实例。UserDir 影响 worker Saved 路径，跨 worktree 复用它会失去状态隔离。
日志含本机路径，提交证据前检查内容。Saved 产品已被现有 UE gitignore 排除。

脚本保持前台等待 UE 退出，记录 PID 和实际退出码，可用 ⌘Q 正常退出。
`process_spawned` 仅表示子进程已创建；`gamemode_startplay_seen` 表示发现本轮
GameMode StartPlay 日志；`validated_observation_seen` 表示发现 `stg-demo` 的有效
Observe 日志。它们均不证明窗口可见、画面合格或运行稳定。即使已观察到状态，
后续崩溃仍返回 UE 非零退出码；UE 退出 0 但日志含 fatal/assertion 或缺少初始化/
Observe 证据时，脚本返回 70（`initialization_unconfirmed` 可包含用户过早退出）。
参数/环境无效返回 64。启动长时间无日志时，入口会继续等待，检查输出目录与
`console.log`，必要时 Ctrl-C 转发 TERM；本入口不实现超时自动终止或可靠性修复。

此改动只改善预构建与诊断体验。它不修复 `SceneViewport.cpp:196` 的
`IsInGameThread()` 断言，不证明 PIE、打包、跨平台或间歇性退出门通过。
当前与 GPU 诊断任务互斥，未获统筹放行前只运行 `--build-only`。
验证记录见 [本轮证据](evidence/ue-mac-launch/report.md)。
