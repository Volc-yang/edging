# GQ 短探针：采集可行性与资源占用

状态：2026-11-01，v0.1；输入基线 `617eb5c`；本次为只读环境探针，**没有采集 CPU/GPU 帧时间**。父节点 GQ；参考 [测量设计](pdca_gq_evidence_baseline.md)。

## Plan 与资源边界

目标是确认本机是否具备 UE 5.8.3 的性能采集工具，且不会干扰用户正在查看的场景。检查进程、安装文件、引擎计时实现和旧证据目录；只有 UE/Worker/GPU 可独占且状态目录隔离时才启动短采集。输出计划目录为 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/Performance/runs/<run_id>/raw/`，实际运行前须分配唯一 `run_id`。

## Do：实际观察

| 项 | 观察结果 | 证据/限制 |
| --- | --- | --- |
| 资源占用 | 查询时 PID 58296 是从旧 `chaos-realism-01` worktree 启动的 UnrealEditor，PID 58437 是其 `origin_worker.py`；工作进程带 `ChaosRealismGameMode` 和独立状态目录 | `pgrep -afil 'UnrealEditor\|EdgeWorldHost\|edgeworld_worker\|UnrealInsights'`；PID 是瞬时值，不代表持续占用 |
| 本机 | macOS 26.6.2（25G83）、Apple M4 Pro；DevSSD 挂载且约 722 GiB 可用 | `sw_vers`、`sysctl -n machdep.cpu.brand_string`、`df -h /Volumes/DevSSD`；目标机/存储预算尚未由 G0 冻结 |
| 工具文件 | `/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealInsights.app/Contents/MacOS/UnrealInsights`、`UnrealTraceServer` 和 `UnrealEditor` 存在 | 只证明文件存在，未启动采集，也未确认此安装的 GPU trace 导出字段 |
| 引擎计时路径 | 安装版 `Engine/Source/Runtime/Engine/Private/UnrealClient.cpp` 约第 409 行由 `RHIGetGPUFrameCycles` 形成 GPU frame ms；`stat unit` 在 `UnrealEngine.cpp` 注册 | 证明源码提供计时路径，不证明当前 Metal run 产生有效 GPU 样本或 CSV/Insights 可导出 |
| 旧 V2 证据 | DevSSD 的 `Logs/V2` 有场景日志和索引，未检出 `FrameTime`/`GPUTime` 样本行；旧文档也明确未测实际帧时间 | 未对全部二进制产物做取证；不能把截图、FPS 上限或日志存在等同性能结果 |

因已有用户 UE/Worker 占用 GPU，**未启动第二个 UE 进程、未发送控制命令、未修改现有状态目录**。本次没有性能数值，也没有 C3 采集可行性通过结论。

## Check 与裁决

| 检查 | 结果 |
| --- | --- |
| 资源与工具文件调查 | `pass`：只读检查完成，进程和安装工具可定位 |
| CPU 帧信号导出 | `inconclusive`：未运行短采集 |
| GPU 帧信号导出 | `inconclusive`：未运行短采集；源码计时路径不能替代导出验证 |
| 性能阈值 | `planned`：G0 数值、负载和有效样本比例未冻结，且无 trace |

## Act：下一张有界执行卡

在用户场景自然结束、统筹确认独占运行窗口后，从准确集成提交和隔离 Worker state directory 启动一个全新 UE Metal run。先做 10–20 秒采集可行性探针：记录启动命令、UE build/CL、场景/分辨率、VSync/FPS 设置、采集工具版本，保存完整日志与原始 trace/CSV；实际确认 CPU 与 GPU 帧时间列的名称、单位、时间戳和非空样本数。若只有 CPU、GPU 空值或时间窗无法对应，保留原始文件并判 `inconclusive`，再确定是否切换 Unreal Insights、CSV profiler 或 Metal 采集路径。短探针只验证采法，不能判 p95 门；正式三次运行须等待 G0 冻结路线、负载、阈值和有效样本规则。
