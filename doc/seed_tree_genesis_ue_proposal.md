# S2：Seed→Tree × Genesis 的 UE5 呈现与输入设计

状态：2026-11-01，v0.1 **设计提案**；输入 `8a069fa`，另只读参考统筹 [V-STG 方案树](seed_tree_genesis_pdca_plan.md)（该文件在建卡时尚未进入本分支）。父节点 V-STG/S2。本文不批准 Genesis 作用对象、物理参数或植物规律；实现与运行验收尚未执行。

## Plan：现有代码与设计约束

| 已有能力/缺口 | 代码依据 | 本版处理原则 |
| --- | --- | --- |
| UE5 发布版通过 GameMode 生成地面、光、相机与树 Actor，Space 显式推进 | `EdgeWorldGeneratedWorldGameMode.cpp:69-148,244-299` | 保留生成场景与显式命令；不由 Game/Render Tick 推进权威时间 |
| 树 Worker 从环境变量启动，状态目录在 `Saved/EdgeWorldTree/<world>`；GameMode 同时持有一个 transport/client | 同文件 `151-199` | S1 冻结同一权威世界的 Genesis 接线后，只连接**一个**权威进程/状态目录；禁止 UE 并发启两个 worker 再拼画面 |
| 树 Observe 解析器核对 world/tick/revision/watermark、规则/投影版本及样本字段；Actor 无 Tick，以 BasicShapes 映射种子/树干/树冠 | `EdgeWorldJsonlClient.cpp:510-666`；`EdgeWorldObservationActor.cpp:82-154` | 沿用“验证后应用”；Genesis 结果必须先成为已提交 Observe 样本，不能从 UE 本地物理模拟倒灌状态 |
| 通用传输只核对 request ID 和协议 v1；GameMode 的 Status/Advance 只读 tick/revision，没有核对 result world ID 与期望 revision | `EdgeWorldJsonlClient.cpp:221-253`；`EdgeWorldGeneratedWorldGameMode.cpp:175-199,256-279` | 为新契约定义各调用点身份校验；错误/不完整响应不更新显示或本地 head |
| 当前树 PlayerController 只绑定 Space；相机固定且无历史切片快捷键 | `EdgeWorldGeneratedWorldGameMode.cpp:128-148,282-299` | 增加明确的相机导航与历史观察操作，解决视口聚焦后才可用键盘的可操作性问题；导航只改视图 |

现有 Chaos 写实样区控制器以 `WASD/QE`、方向键、Shift 移动相机（`ChaosRealismGameMode.cpp:24-52`），可复用其输入思路，但不要让相机移动发送 Worker 命令。现有树代理仍是固定数量 BasicShapes，不是写实资产或 Genesis 几何。

## Do：拟议 UE 接口与呈现路径

1. **进程与命令。**S1 明确新 Worker 入口、持久化目录、Genesis 版本/设备/步长和单写者提交语义后，GameMode 仅启动该 Worker。`Status → Observe` 初始化；Space 的 `IE_Pressed` 只产生一次具有稳定 `command_id`、`expected_revision` 与 `target_tick` 的显式 `advance`。请求在途时禁用再次提交，超时或断线显示状态，不能推测已提交；重新 `status` 对账后再决定是否重试相同 command ID。
2. **结果身份。**`Status` 必须匹配请求 `world_id`，`tick/revision` 是安全精确整数且与已知 head 不倒退；`Advance` 必须匹配 world、目标 tick、预期的新 revision、command ID 回显（若 S1 规定）及物理提交标识。`Observe` 必须匹配请求 world/tick/source revision/watermark、规则/投影版本、稳定 seed/tree/物理实体 ID、状态/事件 hash。缺字段、错字段或负例时保留上一个已验证画面，记录 `request_id`、错误码和拒绝原因；不调用 `ApplyTreeObservation`。具体新字段由 S1/S4 冻结，UE 不自行发明别名。
3. **物理投影。**S1 若将种子刚体位姿或其他物理量作为同 tick 的已提交样本，UE 仅将其经版本化单位/坐标变换放置代理。Tree Actor 继续从树状态控制种子、树干和树冠的显隐/尺寸；物理位姿可定位**已声明属于物理实体**的代理，但树根是否随位姿变化要由 S1 说明。UE Chaos、碰撞、插值、镜头过渡都只能是视觉效果，不能成为下一 tick Genesis 初态或规则输入。若物理样本缺失或版本不符，拒绝整帧绑定的组合样本，避免展示“树 tick 5 + 物理 tick 4”。
4. **时间切片。**按冻结环境序列采 tick 0、一个明确幼苗 tick、一个明确成树 tick（现有实验序列约 tick 5 成树，须以固定输入实测为准）。历史观察键和“回到最新”操作只发 `observe`；界面或日志同时显示世界 ID、tick/revision、seed/tree ID、物理实体 ID 与 state/event hash。重复同一查询应得到相同可重建组件数量、变换与材质参数。
5. **可操作性。**建议视口可聚焦后 Space 推进、`0/1/5` 请求相应已存在历史 tick、`H` 回到最新；未存在的 tick 显式报错而不显示旧画面为新时间。`WASD/QE` 平移、方向键转向、Shift 加速相机，提供可见帮助文本与当前“视口焦点/请求进行中/观察 tick”反馈。具体键位须在 S4 定案并和 Editor 快捷键冲突检查；所有观察/导航操作不触发 `advance`。

## Check：可执行的独立验收设计

| 门 | 方法与原始证据 | 判定边界 |
| --- | --- | --- |
| C1 构建/运行 | 精确提交、UE 5.8.3 CL、插件构建日志、Worker/Genesis 配置、一次真实 Metal PIE 与一次 Standalone 启动日志 | 任一失败如实记录；NullRHI 不能替代画面 |
| C2 身份/拒绝 | 固定正确样本和故意错 world/tick/revision/watermark/物理版本或缺样本 fixture；记录完整响应、解析结果、Actor 应用次数及前后变换 | 错样本不得更新 head 或任何树/物理代理；不把传输成功当结果可信 |
| C3 三时刻画面 | 同机同 build 的 tick 0、幼苗、成树三个固定观察，逐帧图、日志、相机参数、状态/事件摘要、组件快照；独立 reviewer 看 Metal 原图 | 三种阶段可辨、物理代理与同 tick 样本一致；BasicShapes 仅算技术可见，不算写实质量 |
| C4 只读矩阵 | 初始化后保存 manifest/state/event/head 摘要；逐项执行移动/旋转相机、FPS/画质变化、UE 暂停恢复、显隐代理、历史与重复 Observe，再分别取完整摘要；另执行一次 Space | 每个只读动作前后摘要相等，只有显式命令可改变；遗漏/未取到摘要为 `inconclusive` |
| C5 输入/焦点 | 独立操作者从启动场景点击视口、按 Space 一次、按历史键、WASD/方向键，录屏和请求日志对应；确认 `IE_Pressed` 单击只推进一次，失焦有明确提示 | 若键盘无响应或一次按键多次推进，判失败并重开输入卡 |
| C6 性能 | GQ 用冻结分辨率/路线采原始 CPU/GPU 帧时间与有效样本比例 | G0 阈值未冻结或 GPU 信号缺失时只报告数值/`inconclusive` |

所有证据需记录独立 Worker state directory、输入 seed/初态、Genesis 配置、运行窗口和绝对路径/哈希。避免与当前用户 UE/Worker 共用进程、GPU 测试窗口或状态目录。

## Act：依赖与局部返工

S2 的接口与键位仍为提案。S1 需给出物理对象、样本字段、单位/坐标、原子提交和错误语义；S0 冻结场景行为与视觉/性能标准；S4 对齐后才可拆实现为非重叠的 transport/parser、GameMode/input、projection/visual、独立验收卡。若 C2 失败先修校验调用点；若 C3 失败先区分样本错误与投影/可见性；若 C4 失败检查是否有 UE 帧/观察写入。保留通过的其他检查及原始失败证据，不以 UE 引擎源码修改代替插件层修正。
