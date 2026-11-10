# I21C 独立审查与结算

2026-11-10；**本轮 partial，D3-IMPORT 未通过**。C0 方案、C1 代码/CPU/准确派发卡接受；两次真实 import 均失败，没有保存的 UE 资产包、Native 正例/负例或新进程 reload 通过证据。本 reviewer 未启动 UE/GPU/worker/Genesis/UI，未读 owner/key，未修改 DevSSD。

审查树 `.worktrees/i21-review` / `codex/i21-review`，基线 `6eae2795628dc10d94506b00f37084fe4ae4e488`；仅拥有本目录。root 负责实际执行、整合、上下文与后续发布/清理。

## C0 / C1：实际完成的审查

[方案门](plan-review.json)接受计划 SHA `12e964370403c52b36e65ebe4a96f4dae3ee554b40fe1e6239a5ed7224dd9f97`：独占 content-only host、失败 attempt 隔离、同一 900s/4GiB/Content512MiB 上限、最多两次 import 与一次 reload、NoTrace/独占 FileSystem DDC，D3-ADAPTER/编译/Metal 后置。

初版 `c71664b` 的四项 CPU 检查独立通过。C1 实际审源要求补齐 `/Script` 的真实已加载包/模块身份、Native 负例精确错误与实际 getter 片段、启用 plugin 的 pip 要求闭包、真实 Foundation Documents 查询。修订 `3b156d51cc9df110e5ef24e0be82618d54e2eb5b` 接受；独立重跑五项定向 CPU 检查 exit0，最终只读 preflight 与 owner 原件逐字节相同，SHA `c72a0b213a6156585ba6aad26c100b1ec3e36fd978f18abd049cada36bfffe21`，实际核对 20 个源文件、698 个安装 Python 文件、23 个相关模块、44 个启用插件。

另外重新读取真实 glTF/BIN，五个源 mesh 的三角数及 `[0,2,1]×100` 局部 AABB 精确匹配 recipe，十四个纹理来源全部覆盖，地表预览球未选入。它证明源期望正确，未证明 UE Native 结果。[CPU 证据](c1-final-cpu-review.json) / [源几何核对](c1-recipe-real-source-check.json) / [安装源码身份](installed-source-check.json)。

[首次准确卡](c1-import-01-card-acceptance.json)核对 800 项输入及持久脚本/实际 argv/env；[第二次准确卡](c1-import-02-card-acceptance.json)核对 803 项输入，旧 driver/seal/card 原路径字节保持。第二卡仅新增受审 `UE_SKIP_UBT_SDK_SETUP=1`，其依据是安装版 TargetPlatformManager 的精确跳过条件；不授予 SDK/build 门。

runner 初版的环境继承、遍历漏错、终检/封存预算意见均已落实。v2 只允许精确 attempt tmp 内、实际 `lstat` 为 socket 的 `dotnet-diagnostic-*` 项，记录类型/bytes/mode、不读内容；Content 和其他非 regular 项仍拒绝。reviewer 的实际 IPC fixture 先因 macOS 长路径失败，短路径重试的 bind 返回 EPERM，故**没有宣称 IPC 测试通过**；两项原始限制分别保留，v2 判定依据为准确源差异审查，非伪造测试。

## C2：两次真实失败与包实况

完整独立结果：[c2-run-review.json](c2-run-review.json)。两次原件均保存在 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import/`，没有覆盖旧 attempt 或改写历史失败。

| attempt | 实际 parent wait / 强制介入 | 实际原因与裁决 |
| --- | --- | --- |
| import-01 / PID10196 | exit0 / forced=true；9.403s 监督结算 | sizes 拒绝 dotnet-diagnostic 非 regular 项，监督器主动终止进程组；Python 导入尚未执行，result 不存在。exit0 不能授正常退出。旧记录未保存当时具体 lstat mode，dotnet 上下文与 Unix diagnostics socket 一致，不倒推为独立测得的 mode |
| import-02 / PID26198 | exit255 / forced=false；26.407s | Python 已运行，16 条 Interchange import-completed 日志；随后 `ue_entry.py:245` 调用空 subsystem 的 `enable_section_collision`。`get_editor_subsystem(StaticMeshEditorSubsystem)` 在这个准确进程返回 None，实际 FAIL/堆栈一致；不是超时或监督器误杀 |

两份 `host/Content` 实际都为空，**0 个已保存 `.uasset`**。R 的 `content_bytes=2,679,781` 来自 `a2/ddc/Content/` 两份 `.udd`，是按路径名 Content 的保守计量，不是已保存资产或可交付 Native 包。第二次执行到内存导入/材质构建后的 mesh 设置；显式正例保存、Native metadata 验证、真实负例与 reload 均未完成。两次 import 额度耗尽，没有第三次，也没有以 reload 重新导入。

独立重算两卡 **813 个唯一 pin**，全部匹配；I20 全部 **34 个原件**（含许可/元数据）与 I20 父级索引一致。两次共六份 quiet PS 和最终 PS 均核对原 SHA、独立解析，无自有或同 executable 残留。七份稳定仓库运行原件与 DevSSD 逐字节相同。

## 资源与阶段门

root 实际最终 fsync 后 stdout 记录 **742.467523s、217 文件、26,383,495B**；独立重新枚举与之相等，seal SHA `b4d27d42afad4dedf11a477c0a7429a7ce393d67f65617cbe05bd895e048745e` 匹配。900s/4GiB 与保守 Content512MiB 封顶未超，但首次 forced 和外域门仍 fail。

六个声明域的 before/after metadata 独立复算为三处 UBT Trace 文件删除/轮转/替换；首次 console 明示 328B `Trace.uba` 写入。安装源码及真实进程链表明这是启动自动 `ValidatePlatforms`，不是本轮执行了 C++ 编译。Mac VALID26.1.1 与 Win/Linux 缺 SDK 的 AllPlatforms 输出，不能替代导入门，也不是这次 Python 异常的诊断。该审查仅覆盖声明六域，不声称全系统无写入。

裁决：C0/C1 通过；字节/连续时间封顶有限通过；正例导入、正常成功退出、声明外域写入边界失败；Native metadata/负例与独立 reload 未运行；D3-IMPORT 不接受，D3-ADAPTER/BUILD/D4 不解锁。I18 exact3、I19 与旧失败账不变。

## Act：下一轮最窄入口

先在新审定卡中验证所属 `StaticMeshEditor` 模块激活与实际 subsystem/getter 能力，再开始任何资产修改。公开 `unreal.load_module('StaticMeshEditor')` 是待验证候选；所属动态模块尚未启动是依据安装源码与本次日志的解释，未实测为唯一原因。其 StartupModule 会加载 AdvancedPreviewScene，必须继续遵守无窗口/NullRHI 边界。

同时冻结 Nanite 的计数语义：本次确有 NaniteBuild 日志，但程序还没运行到 Native 三角计数。`GetNumTriangles` 的 render LOD/fallback 不能默认等于源 glTF；下卡明确 import policy 或分别记录源、Nanite input 与 render fallback，不扩大容差掩盖差异。

A 的后置 guard-only 提交 `a0ebfbf3c4830b622b63164a3bfee56afbb338d7` 仅在导入前清晰拒绝 None；差异已静态审读，**未经过 UE 执行，不是本轮导入修复通过**。本轮 runtime 身份仍固定 `3b156d51`，其原 DevSSD snapshot 不变。

父任务报告自动审批拒绝公开推送代码、本地路径与 UE 元数据，要求用户确认具体公开 payload；A 保留本地分支，PR/CI pending。本 reviewer 没有发布、换渠道绕过、合并或清理。该阻碍与本地 C1/R/C2 判定分别记录。

重现只读核验：`python3 -B doc/evidence/universe-I21C/check_run_evidence.py <稳定统筹repo> <新的审查输出目录>`。它读取封存原件并仅写指定输出目录，不启动 UE，不修改 runroot。原始失败、源输入、两个任务分支和 DevSSD 输出均应保留；父任务审读本 scoped commit 后记录等效审查/集成门。
