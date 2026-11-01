# S2：抽象 Seed→Tree × Genesis 的 UE5 呈现与输入设计

状态：2026-11-01，v0.2 **设计提案**；输入 `ac5ec2f`，依据用户对 Seed→Tree 语义的修正。父节点 V-STG/S2。seed 是可标识的抽象初态，tree 是因果发展后的抽象结构态；两者不预设植物。Genesis 作用对象、因果量、投影语义与产品门由 S0/S1/S4 冻结。本文未实现或运行新版本。

## Plan：现有技术与新版本边界

| 现有代码事实 | 新版本的使用方式 |
| --- | --- |
| `EdgeWorldGeneratedWorldGameMode.cpp:69-148,244-299` 生成地面、光、固定相机和植物代理，Space 显式推进 | 只参考生成场景、异步请求和显式推进；旧植物阶段、外形及环境系数不是抽象发展语义 |
| 同文件 `151-199` 用一个 transport/client 启动旧树 worker，状态目录为 `Saved/EdgeWorldTree/<world>` | S1 定义一个新权威世界/进程及独立目录；UE 不并发启动旧树与刚体 worker 再拼因果链 |
| `EdgeWorldJsonlClient.cpp:221-253` 核对请求 ID 与协议 v1；旧树解析器 `510-666` 核对 world/tick/revision/watermark 和版本 | 复用“解析、核验、应用”结构；新抽象 schema 与 Genesis 因果结果需新版本解析，不能直接复用旧植物样本字段 |
| `EdgeWorldObservationActor.cpp:82-154` 将旧标量状态映成 BasicShapes 种子/树干/树冠 | 仅证明确定性代理投影可行；新 Actor 应从 S1 的节点、关系和物理证据构造抽象视觉图 |
| 旧树 Controller 只绑定 Space、相机固定；Chaos 写实样区有 `WASD/QE`、方向键、Shift 导航 | 可复用纯视图输入思路，补历史切片和焦点反馈；导航不改变权威状态 |

设计目标是 UE5 发布版在同一已提交修订上显示因果结构从初态发展。投影可用节点、连线、层级、时间轨迹或空间场；S4 必须固定一种版本化图形编码，支持稳定 ID 和重复布局。旧 BasicShapes 植物画面不算本版视觉通过。

## Do：拟议呈现与交互路径

1. **单权威入口。**S1 冻结新 worker 的 world ID、状态目录、Genesis 配置和原子提交边界后，GameMode 仅连接该进程。`Status → Observe` 初始化；Space 按下只发一个带稳定 command ID、expected revision、target tick 的显式命令。请求在途时禁止重入；超时后先 Status 对账，不能假定失败或自行推进。
2. **结果身份。**Status/Advance 核对 result world ID、tick/revision 和 S1 指定的物理提交标识；Observe 核对请求 world/tick/source revision/watermark、schema/规则/投影版本、稳定节点/关系 ID、状态/事件 hash、Genesis 证据引用。通用传输成功仅说明 JSONL 往返。缺字段、错版本或水位时保留上一已验证画面和 head，记录原始响应与拒绝原因；新字段名和 revision 规则由 S1/S4 冻结。
3. **抽象因果投影。**初态显示一个可辨的源节点；中间态显示新增的因果分支或关系；发展态显示经规则确认的结构扩展。位置、颜色、尺度、连线由版本化纯投影函数从样本稳定 ID 与关系生成，重复观察产生相同布局和组件集合。Genesis 结果只以**同 tick 已提交的物理候选及因果引用**进入图；如何影响节点/关系由 S1 决定，UE 动画不得编造。
4. **物理与视觉边界。**若 S1 选择位姿、轨迹或约束等物理量，须冻结单位、坐标、参考系、时间步及数值范围；UE 可把已提交量投影为符号、轨迹或空间位置。UE Chaos、插值、LOD、镜头过渡与局部碰撞反馈仅供呈现，不能成为下一 tick Genesis 初态或因果输入。抽象结构与物理证据 revision 不一致时拒绝组合呈现。
5. **历史与输入。**由 S0/S4 固定三个检查点：初态、中间态、发展态，不预设 tick 1/5 或萌发。建议 Space 推进、`0/1/2` 请求三个已定义检查点、`H` 回最新，`WASD/QE` 平移、方向键旋转、Shift 加速相机。键位须检查 Editor/PIE 冲突；可见帮助显示视口焦点、请求状态、观察 tick/revision。不存在的检查点明确提示；导航、帧率、暂停、显隐不发 Advance。

## Check：独立验收设计

| 门 | 方法与原始证据 | 判定 |
| --- | --- | --- |
| C1 构建/运行 | 精确提交、UE 5.8.3 CL、插件/worker/Genesis 配置、独立状态目录、真实 Metal PIE 与 Standalone 启动日志 | 任一路径失败如实记录；NullRHI 不证明可见画面 |
| C2 身份/拒绝 | 正常样本与错 world/tick/revision/watermark/schema、缺节点/关系或 Genesis 引用 fixture；保存完整响应、解析错误、Actor 前后快照 | 错样本不得改变画面或本地 head；未冻结字段先记待定 |
| C3 三时刻画面 | 固定 world 的初态、中间态、发展态 Metal 图、日志、相机、请求/响应 hash 和节点/关系快照；非实现 owner 逐图复核 | 三态因果关系可辨，物理证据可回查同 tick；旧植物画面不算通过 |
| C4 只读矩阵 | 相机移动/旋转、帧率/画质、暂停/恢复、显隐、历史/重复观察各自前后采 manifest/state/event/head 摘要；Space 单独执行 | 只读动作逐项摘要相等；只有显式推进可改变权威状态；缺项为 `inconclusive` |
| C5 输入/焦点 | 独立操作者聚焦视口、按 Space 一次、历史键、导航键；保存录屏、键事件和 Worker 请求 | 单击只推进一次且键盘可用；失焦反馈清楚；多推进或无响应判失败 |
| C6 性能 | GQ 按冻结场景/路线采 CPU/GPU 原始 trace、有效样本与资产来源 | 阈值未冻结或 GPU 信号缺失只记观测/`inconclusive` |

证据须绑定 world/build/规则/投影/Genesis 配置、运行窗口、独立状态目录和哈希。不得使用当前用户 UE/Worker 作为新版本测试实例或共用其状态目录。

## Act：依赖与返工

S0 确定抽象初态/发展结构的可观察定义和场景信号；S1 冻结单一权威样本、Genesis 因果引用、单位/坐标、提交和错误路径；S4 才批准新投影版本、键位、检查点和实现卡。实现可拆为 transport/解析、GameMode/输入、结构投影和独立验收，写路径互斥。C2 失败返工校验调用点，C3 失败区分状态/因果映射与视觉可辨性，C4 失败追查越权写入；保留其他已过门和原始失败证据。优先使用 UE5 发布版插件及渲染能力。
