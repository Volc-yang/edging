# H1g 标准启动器显式同步接线

状态：代码、静态/mock 和有限真实组合验证完成；等待最终独立 PR/证据审查。
父卡：[viewport-preflush-launch-plan.md](../viewport-preflush-launch-plan.md)。
初始准备基线：`c8209331f976360a92a9d3f3b5dad6e4fffbc666`。
统筹正式交接后更新到准确基线：`d1dac431c2f7c666dce68be09af46c4e9ee4dc06`，
包含 H1f 集成 `e6c9d96` 与 H-LIGHT-01 集成 `69cd400`。
先提交 scoped 准备提交 `7157720eb9d08e42d5004e77a118980341672887`，再无冲突
rebase 为 `40d40c64ba2c2b418f198da62f138cbab8a0e408`。两次真实运行都使用后者
源码及标准脚本；未使用旧基线运行充当组合证据，未追随移动分支。
分支：`codex/g3-preflush-launch`；独立 worktree：
`/Users/yangacan/edgeWorld/edge-world/.worktrees/g3-preflush-launch`。

## 修改边界

只改 `scripts/launch_edgeworld_ue_mac.sh`、现有
`tests/test_unreal_mac_launcher.py`、`doc/ue_mac_launch.md` 和本报告/紧凑证据索引。
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
- `python3 -m unittest tests.test_unreal_mac_launcher -v`：初始准备 8 项通过，
  7.109 秒；更新到最终基线后复验 8 项通过，6.222 秒，均退出 0。
- `git diff --check`：通过。

覆盖默认仅构建、默认启动不带两个旁路参数、原 no-render-thread 路径、新参数
重复输入但仅转发一次、两种顺序的冲突在 build-only/launch 下均于构建前返回
64、两种旁路的构建失败不启动、build-only 不声称启用运行模式。
构建 mock 的独立标记文件验证冲突时 Build.sh 未执行；假 App 参数记录验证
没有悄悄添加另一线程模式，日志说明与请求参数一致。
Mock 使用临时目录中的假 Build.sh 和假 App，只验证启动器分支、参数和日志，
不执行真实 UBT/UE/Worker/Genesis。

## 真实标准启动与恢复

收到统筹正式资源交接后才启动；每次启动前检查相关 UE/Worker/reporter 无残留。
实际命令均为本 worktree 的 `scripts/launch_edgeworld_ue_mac.sh --launch
--viewport-preflush --user-dir <absolute isolated directory>`，Python 为主仓库
`.venv-genesis/bin/python`（Genesis 1.4.3），worker 强制使用本 worktree。
原始 `command.json`、标准脚本 `command.txt` 与状态/构建/UE 日志全部保留。
第二次仍经过标准脚本构建，报告 Target is up to date，没有绕过构建步骤。

以下时间为 2026-11-01 上海时间（UTC+8）；原始日志/JSON 保留 UTC。
首图时间表示采集观察时间，不是首次 GPU presentation。

| 会话 | 构建 | UE / Worker PID | 引擎初始化 | 首次采集可见画面 | 原生游戏窗口销毁 | UE / 启动器退出 |
| --- | --- | --- | --- | --- | --- | --- |
| primary | 成功，25.77 s | 47683 / 47866 | 14:57:52.237 | 14:58:37.144，tick0 | 14:59:34.267，窗口按钮关闭 | 0 / 0 |
| recovery | 成功且 up to date，2.65 s | 48265 / 48400 | 15:00:16.201 | 15:01:08.525，恢复 tick2 | 15:01:43.485，CmdQ | 0 / 0 |

主会话两次显式 Space 分别得到新的 tick1/tick2 ack，权威 tick 0→1→2。
每次会话分别执行历史 0、H 与 W，合计六组逐项只读比较，全部 manifest 和
三个 checkpoint 哈希不变；历史/H 的 ack 从各次操作前日志 offset 之后匹配。
相机只读以文件比较及前后可见构图变化验证，不虚构 worker ack。
两次光照命令前后另有独立文件比较，均不变，不计入上述六组。

恢复使用 primary 的同一个隔离 UserDir，没有 Advance。主会话 preclose、
postclose、恢复首图、恢复 preclose/postclose 的全部四文件集合相同；manifest
SHA-256 为 `556bc0ded7f3a1e858e7e032e657a8ba8eea096fb8a930c58ef46ca91ffebe9d`。
最终 checkpoint 实体字节亦在原始目录内，封存时重算与快照一致。

两次实际命令各恰有一个 `-EWDiagPreflushViewport`，均无 `-norenderthread`。
原生通知均记录 `preflush=1 threaded_rendering=1 game_thread=1`，指向实际游戏
窗口，非空 owner 同步前后相同并记录 `owner_unchanged=1`。主会话 owner
`0x96533ac8c10`、窗口 `0x96538678010`；恢复 owner `0x5fb05681e10`、窗口
`0x5faf6109810`。flush 结束均早于同一游戏窗口销毁；单次耗时为
24.094/0.164 ms，仅作机制记录，不形成性能结论。输入调用时间和返回时间
另存 `close-input-attempt1.json` / `close-return-attempt1.json`，不混同原生事件。

## 光照组合观察与画面

两次会话分别通过游戏控制台运行 `edgeworld.DumpLightingEvidence`。
`NumLightingUnbuiltObjects=0`、`Lights with unbuilt interactions: 0` 和
`Primitives with unbuilt interactions: 0` 均得到实际原生日志；DirectionalLight
和 SkyLight mobility 都为 2（Movable）。主会话 tick0、tick1/2、恢复 tick2 的
画面可见 HUD、因果节点/连线、地面/墙和工程代理；没有光照未构建提示。
这不是正式视觉质量验收。

该采证命令会通过 DumpUnbuiltLightInteractions flush。两次组合运行都执行过
此命令，因此不能把本卡作为新的 H1f 受控 A/B 对照，或据此宣称 preflush
单独造成退出成功、失败率改善或性能收益。默认线程原始关闭路径仍是开放门。
完整日志还保留 worker 的 torch deprecation、EditorDataStorageUI/EnhancedInput
以及主会话音频采样率等警告；退出 0 不表示所有警告均已修复。

## 采证完整性与工具限制

采证每次必须显式输入 run/arm/log/stateDir/PID，操作前将 PID 的真实进程命令
与日志/UserDir 比对，再核对 context.json；只在初始化和有效观察已证实后绑定
正在运行的 App 路径。每项操作以独立 `*-attempt1` 目录保存，mkdir 独占创建，
每个文件用 `wx`/`x` 写入；没有覆盖旧记录，也没有隐式沿用前一会话闭包。
没有工具超时导致重启，没有额外 Editor 实例。

一次试图用 eval 加载 helper 被 CUA 拒绝（Code generation from strings
disallowed），随后直接声明 helper；失败时未发送 UI 输入，也未重启进程。
封存检查又发现 CUA 返回的跨运行时 Buffer 不满足 `instanceof Uint8Array`，
helper 将截图和日志片段完整保存为 `{type: Buffer, data: [...]}` JSON；首次
封存的文本断言因此失败，未生成摘要/索引。原始字节数组全部保留，
`decode_buffers.py` 将 24 份记录无损还原到各 attempt 的新 `decoded/` 目录，
没有覆盖原件；重新检查解码日志、图片和哈希后完成封存。索引同时覆盖原始
Buffer JSON 和解码文件，未将该写入问题当作 UE 故障。解码恢复首图已再次
打开检查，HUD tick2 与场景可见。问题说明与恢复映射见
`helper-limitations.json` / `buffer-serialization-limitation.json`。

## 封存和剩余门

原始目录：`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H1g-20261101/raw/`。
紧凑 [evidence-index.json](evidence-index.json) 认证本地完整
`sha256-index.json`，共 179 个文件、26,059,156 字节；完整索引 SHA-256：
`8bab7ef0933e2e99e64fff1bc416ee21a48e370d01bb4d670659f728e5b74163`。
索引排除自身/紧凑索引、pycache 与 UserDir 的非权威生成缓存/config；包含
真实日志、输入/快照、首图、原始 Buffer/解码文件及全部权威/checkpoint 实体。
`seal_evidence.py` 验证两次构建/退出、机制、只读、恢复、源文件/二进制身份，
并逐文件复算索引。`engine-source-verified.sha256` 与 H1f 原始引擎源码摘要
一致；没有引擎源码改动。恢复构建为 up to date；运行期间产品源码未改变。

两次启动前/退出后相关进程检查均干净，没有 reporter 干扰或需要 signal 清理
的 orphan。最终本地 15:02:27.891 库存无 UE/Worker/reporter/UBT；构建/GPU
资源已释放，不再启动本卡外的运行。工作树没有自动生成的 DefaultInput.ini
待处理；主工作区的同名用户文件未触碰。

本卡仅交付有限显式开发旁路的标准接线及组合证据，目标 PR 为
`codex/plan-consolidation`，最终独立审查/集成由统筹完成。默认保持关闭，
无 H6B/C 或产品默认启用决定。根因、原始默认线程间歇性退出、其他窗口、
PIE、打包、其他平台、正式视觉和产品总体可靠性仍开放。
