# I21 PDCA：真实 UE 资产导入与独立回读

2026-11-10；parent=I20/D3-IMPORT；统筹root；固定基线 `d5ada8fcddf215f6fb4bcf9cabea65699ad8ae91`，集成分支 `codex/plan-consolidation`。状态：**方案待独立审查，尚未创建实现树或启动UE**。用户要求开始下一轮，延续已授权并行PDCA；本轮不用goal。

## P：目标、固定输入与依赖

将I20的真实CC0源文件变成可重新打开的UE资产包，取得真实mesh/材质/依赖元数据，解除D3-ADAPTER的导入输入缺口。导入是实际实现与Native检查，不把源下载或合成合同再做一遍称为进展。本轮验收仅D3-IMPORT；实际Universe接线、C++编译及Metal画质按依赖后置，不能用本轮NullRHI导入授予这些门。

- I20A index SHA `d9df98dbf9260ad8e94e5c274563725355ebdddab7e1c1f6676dc02f970447b7`；实际源root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I20-20261110-realistic-assets`，全部保持只读。不得重新下载、改源glTF、改旧receipt或使用未知Dot补丁。
- 发布版UE5.8.3 CL58210709，自带PythonScriptPlugin/Interchange；独立content-only host，不载入EdgeWorld运行模块，不接world/worker/Genesis或owner/key，无可见窗口、无渲染/GPU画质试验、不改引擎源码。
- fern_02各mesh完整导入；boulder_01完整导入；ground仅导入纹理，预览球不得作地形。材质显式PBR；fern独立Alpha→OpacityMask/Masked/0.5/TwoSided；ARM按R/G/B→AO/Roughness/Metallic，数据图禁sRGB。源GL法线保留，额外DX纹理是明确override且禁重复翻绿。
- 已安装源码事实：glTF translator默认翻GL法线绿通道，glTF网格已从m转cm；导入额外scale保持1，禁再乘100。固定不合并mesh/不烘展示节点平移的pipeline，实际UE结果再核节点→mesh与局部bounds。若API/结果不同，保留失败后窄修，不靠字段声明推断通过。

## 任务树与卡

```text
P0 root方案 + A/B只读调查 → C0独立计划审查
  → A importer/recipe/content-only host/CPU边界检查 PR
  → C1独立源差异与执行命令审查
  → R root独占执行：真实导入 → 新进程重新打开并回读 → 外部封存package SHA/依赖
  → C2独立原件/映射/材质/包/进程审查 → root集成、上下文commit、清理
后续D3-ADAPTER消费真实metadata → 新C++编译/Native事务检查 → D4 Metal画面
```

| ID / owner / 排他路径 | Plan与Do | Check与证据 | Act |
| --- | --- | --- | --- |
| P0 / root + 两位只读planner | 固定来源、发布版API、导入↔呈现交接字段和预算；不实施 | planner引用安装源码，C0裁决本方案 | 接受后才创建A/C树 |
| A / asset subagent；`scripts/realism_import/`、`tests/test_realism_import.py`、`doc/evidence/universe-I21A/` | 实现明确版本的recipe、content-only descriptor、UE导入/回读脚本及有界preflight；由root执行UE。输出`.uasset`仅DevSSD新目录，不进Git。不得改现有Host/launcher/authority/worker/parser/I0A/GameMode或I20原件 | CPU真源身份/路径/缺.alpha/损坏输入拒绝；独立审代码。实际UE还须R门，不以mock/unreal stub证明导入。每个实现任务独立PR到统筹分支 | 源检查接受才移交root真实测试；失败保留原件并只返工A |
| C / reviewer；`doc/evidence/universe-I21C/` | 先只读C0；审定后独立树保存计划/代码/命令及实际结果裁决 | C1不得只读owner报告；C2核源/包摘要、实际UObject与材料节点字段、两进程一致和父wait、有限资源。无第三个自行运行的UE | 可接受、返工或部分；不得把未测画质/物理判pass |
| R / root；计划/登记/backlog、`doc/evidence/universe-I21R/`、DevSSD独占runroot | preflight和C1接受后，用固定命令/环境启动自带commandlet；导入成功后另开进程只读回读；各次日志/结果独占文件，外部实际计量并封存 | 实际parentwait、全部package文件SHA/闭包、无存活自有后代、源输入前后不变；逐项交叉owner/C。导入和回读不是C++build | 只接受已测门，实际metadata不足则标partial；审查后集成/精简上下文/commit |

## 导入→呈现交接契约

真实输出包含UE版本/CL、准确脚本/recipe/descriptor与原始命令身份、I20源index及逐文件SHA；每个源node/mesh→UE object path/class的映射、combine/bake策略、明确单位/轴/pivot、Native局部AABB、LOD0 section→slotindex/name。材质记录实际class、节点连接、每texture的source_file_id与object path、sampler/sRGB/compression/FlipGreen、DX override及alpha/PBR属性。包的文件SHA覆盖所有`.uasset/.uexp/.ubulk`等实际sidecar；依赖逐项分类为新项目包或已安装UE的明确外部依赖，未知/丢失依赖不可pass。

第二个全新commandlet重新打开已保存包，重新读取真实UObject字段和依赖，与导入结果交叉比较；不能拿第一次内存字段或重复JSON充当reload。reload前后Content及所有包sidecar文件map必须一致，Saved/DDC日志增量另计。Native负例在内存中实际断开fern Alpha、改错mesh材质slot并验证拒绝，再恢复且不保存；不能只改JSON声称UObject故障注入。需要的读回API不可用时先保留缺证，不用常量伪造。source_unit/axis/pivot字段区分源码约定、recipe与实际测量。可延后ground派生plane，但此时必须明确本轮只交付ground纹理/材质，不输出已生成地形或可运行完整presentation profile。

正式runtimeprofile、独立launcher pin、HUD/场景原子事务、历史选择、Genesis/权威只读门仍交给D3-ADAPTER；I20 synthetic profile不改造成假Native正例，I18 exact3和I19失败保持。

## 资源卡与停止条件

- 新独占root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import`，输出host/Content/Saved/日志/隔离DDC全在其中；不改旧I15产物或复用旧缓存。root执行前记录实际argv、环境白名单、代码SHA与独立C1接受；准备/审批完成后才开始运行clock。
- 全部运行自首dispatch至最终封存连续≤900s，新root总实际文件≤4GiB、Content合计≤512MiB；最多2次导入尝试（每次≤240s）及1次reload（≤180s），总clock不重置。每个import attempt用独占host/Content/Saved/result/log/DDC，禁止覆盖或复用失败包；reload仅打开已选成功attempt，以新UserDir/Abslog保存独立结果。失败原件保留；一次窄修仍在同一clock/总量中；余量不足就结算partial，不开隐含第三次导入。
- `-run=pythonscript -NullRHI -unattended -NoSplash -NoSound -notraceserver -traceautostart=0`；专属`UserDir/Abslog`，沿用已证实的显式FileSystem Isolated DDC与`-DDC-NoDefaultGraph`。DDC短路径<119字符；不启动Zen/Trace或调用C++build。Python默认隔离，清除EDGEWORLD、PYTHONHOME/PYTHONPATH及UE_PYTHONPATH。
- PythonScriptCommandlet无条件执行RunStartupScripts；项目配置显式清空StartupScripts/AdditionalPaths。Mac的FPlatformProcess::UserDir仍指系统Documents，不能把`-UserDir`误称为Python用户搜索路径隔离；preflight须确认真实Documents/产品标识/Python中无用户init_unreal.py，检查所有已挂载Content/Python路径及启用插件的startup脚本并枚举/固定已安装可信来源。发现未审来源即停，不执行或删除用户脚本。独占UserDir也检查无init_unreal；不覆盖HOME或改用户Python环境。
- root持有唯一UE执行权；实际Popen/wait并监控总量/超时，异常只回收本次精确进程组/后代，不全局kill；强制回收不算正常退出。进程退出后只做非启动式检查，不调用会拉起UI的App binding。不需要用户Play/解锁或切换窗口。
- 只读记录已有Trace/Zen/全局DDC/UBT的声明边界前后变化；出现本次意外外域写入/残留则资源/退出门不pass，保留实际差异。源20payload SHA前后必须一致，不读私密配置。不以进程exit0替代完整结果/schema/字段/依赖校验。

完成条件：A实现与独立审查接受、真实导入和新进程回读及父级封存通过，或明确partial并保留可复现失败。只有实际通过才能关闭D3-IMPORT；未知Dot候选保持延期，写实视觉目标继续开放。
