# U2：Genesis 因果边界与有界物理对象设计

版本：v0.1，2026-11-01；parent=U，depends_on=U1；状态 **proposed，待独立设计审查**。基线 `6f3c142aed2f67b556d87e2b649735e6c7fd4b2b`；U1 输入为 `a7fed69` / merge `da84aba`。独占交付为本文件。本文不改已有协议、worker 或存档，不批准世界法则，不把 Seed→Tree 理解为植物。

## Plan：已定边界与实际能力

**已定：**Genesis 为当前抽象因果纵切必需路径；单权威协调器拥有 world head，Genesis 只产生物理候选，UE5 发布版插件只读投影。[U1](universe-identity.md) 的 `WorldId/ExistenceId/PhysicalObjectId` 为接受的设计输入，尚非生产 wire；万物有灵的世界设定不等于每个存在必须绑定一个刚体。AI/载具、完整生态与正式写实并非本卡必需门。

**已观察与源码边界：**[公开 API 审计](../genesis_public_api_audit.md)支持 Genesis 1.4.3 Metal 的 `scene.rigid_solver.set_gravity`、显式 `Scene.step`、`save_checkpoint` / `Scene.load_checkpoint`。现有 [adapter](../../engine/edgeworld_worker/worker.py) 只建一个 Sphere，恢复要求 `len(scene.entities)==1`，位置/DOF 速度经公开 getter 读回；[组合 worker](../../engine/edgeworld_worker/abstract_causal_worker.py) 用已提交 checkpoint 恢复，候选位置经实验 F 进入 `influence_mm`。这些不证明多对象身份、碰撞/材料恢复或复杂 solver 支持。[S4](../seed_tree_genesis_slice_contract.md) 与[原 fixture](../fixtures/abstract_seed_genesis_v1.md)继续独立，不能把本提案原地套到其旧存档。

本卡另对已安装 1.4.3 的 `genesis/options/morphs.py` 与 `options/solvers.py` 做**只读源码核对**：公开 `Box` 支持米制 `pos/size` 及 `fixed`；`SimOptions` 区分 `dt` 与 `substeps`。只确认定义存在，未实例化或运行。现有 `get_dofs_velocity` 的分量次序/参考系不能自动解释为世界线速度；新接口须先核实公开 getter 与分量分类，再标注线/角速度。具体材料/质量配置、接触输出及多对象 checkpoint 覆盖仍需新探针；不使用 `_sim`、私有 entity 索引或不存在的通用 `set_rule_parameters`。

## Do：最小扩展及所有权

**推荐的下一物理实验（proposed）：**一个有持续 `ExistenceId` 的动态刚体与一个固定有限支撑体，先只验证重力、支撑和可恢复运动。几何可先是 Sphere 与固定 Box；它们代表可追溯物理参与者，不是植物 seed/tree，也不是整个宇宙的物质原子。水体、柔体、生态、破坏、载具动力学与任意对象数量暂不加入。旧“纯中性 probe”保留为回归样本，新实验以独立 schema/config/状态目录实现。

| 边界 / owner | 设计产物与不变量 |
| --- | --- |
| U1 持续存在 | `ExistenceId` 不随 Genesis 场景重建、UE Actor 名或求解器索引改变；可物理参与、可仅有地理/关系状态 |
| U2 物理映射 | 建议 `Binding {world_id, physical_object_id, existence_id, binding_version, valid_revision, shape_ref, material_ref, body_role}`，以及独立的 `scene_definition_hash`。每个物理 ID 在一个有效 revision 只绑定一个同世界存在；一个存在可由多体组成，但本实验只采用一对一。固定支撑也有明确 ID 与配置归属 |
| U2 运行期句柄 | 可重建表 `PhysicalObjectId → runtime_handle`，用已提交稳定配置重建/核对；句柄与构建顺序不是持久身份。恢复须按物体数、ID、角色、形状/材料摘要逐项匹配，禁止恢复后直接取 `entities[0]` 冒认对象 |
| U4 唯一提交 | 候选只能进入协调器的校验/事务；checkpoint blob、绑定清单、候选和发展记录在同一 revision 被唯一 head 引用。U2 无权独立发布物理 head，失败/孤立 blob 不是已提交状态 |
| U7 UE 投影 | 从已提交样本重建表现；本地 CharacterMovement/碰撞服务访问体验。相同世界对象若由 Genesis 权威求解，UE 不能同时对它作另一套权威模拟；两者接触交互先回版本化命令契约 |

### 坐标、单位、时间与数值契约提案

物理边界采用有名参考系 `genesis-si-zup-v1`：米、秒、千克，速度 m/s，加速度 m/s²；原始 Genesis 输出及其 frame ID 留在候选中。向 UE 厘米系的转换归 U7，先声明候选基变换 `S=diag(1,-1,1)`，位置 `p_ue=100*S*p_g+origin_cm`、线速度 `v_ue=100*S*v_g`。这是处理手性差异的**待验证映射**，不是对现有抽象图布局的替换；实现前用不对称三轴/平移标记检查轴向与手性，禁止从 z-only 探针推断完整坐标正确。旋转应按 `R_ue=S*R_g*S^-1` 再转 UE 旋转表示，不能简单逐分量改 quaternion 符号；角速度为轴向量，需考虑 `det(S)`，具体 getter/分量次序另核实后冻结，未核实字段不得交给 UE 使用。

| 项 | 建议的有界实验值或约束 | 冻结/验收状态 |
| --- | --- | --- |
| 环境身份 | Genesis 1.4.3、macOS Metal、单 scene/单 env；记录 Python/包/设备/精度及配置摘要 | 沿用已有技术路径，其他设备未证明 |
| 步长 | 候选 `dt=0.01 s`、每逻辑推进 `N=8` 个 `Scene.step`、`substeps=1`；物理区间 `N*dt=0.08 s`，内部积分步长 `dt/substeps` | 新实验值待 fixture 审查；逻辑 tick 不自动等于秒，不从渲染帧补步 |
| 初态形状 | 候选动态 Sphere 半径 `0.1 m`，中心 `(0,0,1) m`；固定 Box 中心 `(0,0,-0.1) m`、尺寸 `(4,4,0.2) m`，上表面 z=0 | 仅有界支撑 fixture，非世界比例；材料/密度、solver/接触参数须单独记录并冻结 |
| 输入 | 参数清单固定后，每 tick 显式重施该 tick 输入；旧两相仅可作版本化工程刺激 | 新任意力/力矩不假装现有 adapter 已支持；公开 API 与单位/恢复须另验 |
| 数值 | 所有向量有限、维度和单位准确；tick/revision/计数为非负 JSON 安全整数 ≤`2^53-1`；N/substeps 正整数且有预算上限 | 新有限位置/速度/接触容差和运行上限须 fixture 预声明；缺上限不放行运行 |
| 重现与误差 | 同机同包同配置先比较续算与不中断；跨设备确定性/容差另立门 | 原样保存浮点字节/规范数值编码及摘要；渲染插值误差与物理误差分开 |

不得用“密度/摩擦默认值”掩盖物理输入：实现卡先核实选用公开材料 API，记录其显式值或已解析默认值及上游版本。碰撞后的接触法线/间距/冲量如参与演化，须核对可用公开查询与 checkpoint 覆盖；本设计不虚构接触 getter，也不声称支撑场景已运行成功。

### 候选、失败与恢复顺序

建议接口不是现有 JSONL wire：`solve_candidate(base_head, prior_checkpoint_ref, binding_ref, physics_input_ref, step_spec) → PhysicsCandidate`。结果至少引用准确 world、base revision/tick/前态 hash、输入/配置/绑定版本及摘要、各物体位姿/速度的 frame/单位/有效性、实际步数、候选数据 hash 与候选 checkpoint hash。候选 hash 排除自己的 hash 字段，包含被比较的数据和来源引用；U4 统一 canonical 编码和版本，UE 不重算二进制浮点摘要。

1. 协调器先验 command 幂等、权限、预期 revision 和输入 schema；旧/错世界请求不得启动新权威提交。
2. U2 从准确已提交 checkpoint 加载，校验世界/配置/绑定及读回状态；显式应用下一 tick 输入，再执行固定步数。历史 Observe 只读已提交记录，不调用 `step` 或隐式重算物理。
3. 验证有限值、范围、对象映射、步数、候选来源，交演化模块产生**发展字段**与原因引用；只保存一条物理轨迹不算形成因果发展。
4. U4 校验候选与发展属于同一前态，写不可变 blob，唯一 manifest 发布同一 revision。提交之前的候选文件即使存在也不可被 Observe 当结果。
5. 求解异常/非法结果/超预算：不更新 head；抛弃候选内存并从已提交 checkpoint 恢复。恢复失败则停写；manifest replace 已尝试且结果不确定则按 U4 的 `commit_status_uncertain` 路径停写并重启核对磁盘，禁止返回“肯定未提交”后继续求解。

本卡错误分类建议复用 `invalid_physics_result`、`genesis_failed`、`revision_conflict` 等已有语义；新映射/配置错误的精确 wire code 由共享契约冻结。未提交失败可以留下不被 head 引用的 blob；检查必须区分 authority map 不变与“磁盘完全没有新文件”，清理策略归 U4。

## Check：正例、反例与证据

所有新运行门目前 **planned**。将固定环境/全部输入/预期字段与阈值写进新 fixture 后，独立 reviewer 才可放行探针；不能事后调整不等式或容差把失败变成功。

| Case | 给定与操作 | 未来可判结果 / 失败信号 |
| --- | --- | --- |
| P1 物理影响抽象发展 | 从同一已提交前态复制两个全新目录，保持形状/材料/绑定/随机源/步数/F 版本相同，只改工程刺激重力；候选 F 仍先采用原 half-even 位移映射，发展字段 `D=round_half_even((z_new-z_old)*1000)` | 先声明强下向刺激 `D_B<D_A`，比较相同发展节点 ID 的 D 及 U7 从 D 产生的抽象位置；事件引用相应候选 hash。原两相首步 `-7/-35` 仅为旧 fixture 观察，不预填为新接触场景结果；仅组合 hash/原始物理轨迹不同，判失败 |
| P2 身份与支撑恢复 | 新有界两物体配置落稳后保存并重启，按绑定映射恢复；同配置续算与不中断对照 | 两 ID/角色/配置正确，动态体在预声明接触容差内受支撑；续算物理和发展字段满足预声明标准。任何对象交换或静态支撑丢失均失败；仅恢复出一个 Sphere 不算通过 |
| N1 非有限值/错维度 | 在新适配器边界注入 NaN/Inf、错误向量长度或超范围；保留原始错误输出 | 拒绝，无新已提交 head/事件/发展；内存恢复旧 checkpoint，失败则停写。非法值进入 canonical hash 或画面即失败 |
| N2 错水位/旧来源 | 命令 expected revision 过期；或候选 base/checkpoint/绑定版本不匹配；历史观察 watermark 不匹配 | 提交/观察显式拒绝；历史与 head 不变。静默改用当前物理状态补历史或跨 revision 拼样本即失败 |
| N3 求解/保存失败 | 求解中断、checkpoint 写失败、写后校验失败；单独注入 manifest 替换结果不确定 | 未触及提交点时旧 head 继续有效；不确定提交必须停写再恢复，只见完整旧/新 head；物理先提交而发展未提交即失败 |
| N4 重复与观察 | 同 command/同规范输入重试；同 ID 异输入；相机/帧率/历史/重复 Observe | 相同重试返回原结果不多 step，冲突拒绝；观察不求解，权威状态/事件/head 摘要不变。step 计数增加或新增事件即失败 |
| N5 坐标/时间混淆 | 不对称三轴点与旋转；改变 UE 帧率但保留相同显式命令序列 | 单位/手性与固定 tick 物理区间符合冻结映射；把 cm 当 m、DOF 次序当世界速度或 UE delta time 改 N 均失败 |

证据绑定准确源码/输入/规则/Genesis/设备/映射版本、原始请求响应、全候选、checkpoint、状态/事件摘要、独立目录及运行 ID。保存原始失败；缺样或公开接触/旋转语义未核实判 inconclusive，不用近似图片代替。新支撑物理是否“真实可信”还需产品物理范围和容差，不能由本卡文档通过推出。

## Act：交接与当前结果

- **U4：**接收 base/checkpoint/绑定/输入/候选来源与唯一提交要求；冻结 canonical 编码、writer lock、幂等指纹、超时/停写/恢复及离线结算。不能把当前单进程原型推成跨进程锁已存在。
- **U7：**消费有 frame/单位/版本的已提交物理结果，并区分原始物理姿态与从发展字段生成的抽象投影；不让渲染反向改物理。旋转/接触 getter 核实之前不使用假定次序。
- **U8/U9：**先冻结材料/求解参数、位置速度上限、误差预算和运行预算，再拆最小公开 API、多物体恢复、反事实及 UE 观察实现卡。失败定位到求解、映射或演化，不用扩展引擎源码掩盖未定义契约。

**本卡 PDCA：**Plan 固定 U1/S4 与公开 API 现状；Do 仅交付本文件的候选映射和有界实验；Check 已做文档来源/身份/权限及 API 定义只读核对，提交前执行单文件范围、相对链接及 `git diff --check`；实际结果补记如下。Act 请求非作者设计审查；通过只解锁 U4/U8 的设计输入，不批准正式演化规律或新运行实现。

**Owner 实际文档检查：**本文件 6 个本地相对链接全部存在；正反例覆盖候选因果差异、两体身份/支撑恢复、非有限值、错水位、求解/保存失败、重复与观察、坐标/时间；`git diff --check` 通过，写入范围仅本文件。未运行 UE/Genesis/物理模拟；独立设计审查及全部新运行门仍 planned。
