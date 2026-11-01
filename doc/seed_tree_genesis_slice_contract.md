# S4 草案：抽象 Seed→Tree × Genesis 技术纵切契约

状态：2026-11-01，v0.2 **实验设计经独立审查；仅 G2-SCHEMA-FIXTURE 可派**。依据用户确认的抽象 seed/tree 语义、[S1 接口](seed_tree_genesis_interface_proposal.md)、[S2 UE 设计](seed_tree_genesis_ue_proposal.md)与[S3 验收设计](seed_tree_genesis_acceptance_proposal.md)。本契约只提出一个有界工程探针，供 G2 分工和审查；不批准真实宇宙的物理法则、演化函数、生命规则或最终视觉语言。

## 1. 技术目标与实验语义

`SeedState` 是世界片段的可标识初态。`DevelopmentStructure` 是每次显式逻辑推进后累积的**已实现因果记录**，不是植物树，也不预先承诺数学上必须分叉。UE 将初态、若干中间态和发展态投影成可辨的节点与因果连线；旧植物 BasicShapes 原型只参考传输和渲染方法。

为了验证 Genesis **参与因果转移**，使用旧公开 API 适配器可处理的单个中性刚体作为 `physical_probe_id`。它不等于 seed，也不代表世界中真实种子。固定的两种求解配置/输入作为工程刺激，Genesis 产生候选位置/速度。**实验转移 F** 在相同前态和其他输入下取本 tick 的 Genesis `position.z` 与前一已提交 `position.z`，计算 `influence_mm = round_half_even((z_new-z_previous)×1000)`，将该安全整数写进新发展节点的 `influence_mm` 字段，并在事件中引用完整物理候选 hash。稳定节点 ID 由 world/tick 产生，与物理值无关。UE 的抽象节点偏移从 `influence_mm` 纯函数生成；原始物理向量可另作证据显示，但**不计为**发展结构差异。此 F 仅为工程探针，不是世界法则。现有 adapter 的 `advance(phase)` 只支持 `shaoyang/taiyang/shaoyin/taiyin` 四相；G2 fixture 优先选其中两相（候选 `shaoyang`/`taiyang`），不新增任意力接口。固定其他输入的反事实运行必须在独立审查前记录两相的预期 `influence_mm` 差异；若实测同值则探针失败并先修 fixture，不靠组合 hash 或画面中的物理轨迹判通过。

这个最小探针检验“Genesis 输出进入权威后态、因果事件和画面”的链路。它不声称已找到抽象世界从一生二、二生三至万物的最终演化算子。分叉/合流规则、物理对象扩展与 AI 提案在后续契约中单独批准。

## 2. 单一权威与提交顺序

新组合 worker 拥有一个 `world_id`、单写者、单一 tick/revision、单 manifest、事件链和 command 去重表；旧 `tree_worker.py` 与旧 Genesis `worker.py` 的存档保持独立，不原地升级。JSONL envelope v1 保持 `protocol_version/request_id/operation/world_id`，`advance` 使用 `command_id/expected_revision/target_tick` 和固定 `external_inputs` 版本。`request_id` 不用于幂等。

每个成功 tick：验证输入及旧 head → 从已提交 checkpoint 加载 Genesis 前态 → 求候选物理向量 → 用版本化探针转移函数产生发展节点与因果边（显式引用候选 hash）→ 校验数值/ID/引用 → 存不可变 checkpoint blob → 原子替换唯一 manifest → 返回组合 head。失败时不更改 manifest，内存求解场景重载已提交 checkpoint；提交结果不确定时停止写入并要求重启核对磁盘。历史 Observe 只读完整已提交记录，不运行 Genesis 或转移函数。

## 3. 版本化状态与观察边界

组合状态至少记录：世界/schema/规则/Genesis 配置与设备身份、seed ID 与初态 hash、physical probe ID、每 tick 的物理候选向量/hash、发展节点与因果边稳定 ID、事件前后摘要、checkpoint hash、command 指纹及结果。发展节点必须包含上述可复算的 `influence_mm`，因果事件记录 F 版本与候选引用；反事实 Check 只比较该发展字段与从它产生的抽象节点偏移，不能只比较组合 hash 或直接绘制的物理轨迹。状态 hash 覆盖抽象状态和已提交物理引用；事件 hash 连接前一事件、命令、候选、发展结果及规则版本。浮点编码和容差在 G2 fixture 中先冻结；非有限值不得提交。

`observe(tick, watermark, view_spec)` 返回同一个 revision 的抽象状态、因果节点/边与已提交物理样本及摘要。请求的世界、tick、水位、schema、规则/投影版本均须精确核对；历史缺失显式报错。UE 在应用组合样本前检查身份与版本，拒绝缺字段或错物理引用；相机、帧率、暂停、显隐、重复 Observe 不改变权威文件。UE 的节点/连线/轨迹布局由固定投影函数从已验证样本重建；它不向下一 tick 提供物理或规则输入。

## 4. G2 任务树与写入所有权

| 叶卡 | 依赖 / 独占路径 | Do | Check |
| --- | --- | --- | --- |
| G2-SCHEMA-FIXTURE | 本草案独立审查 / 新 `doc/fixtures/abstract_seed_genesis_v1.*` 与组合 wire schema | 冻结 Genesis 1.4.3 Metal 配置、受支持的两相（作为显式版本化 advance 输入并计入 command 指纹）、初态、逻辑步数、F 的 canonical 数值转十进制与 half-even tie 规则及安全整数界限、预期 `influence_mm` 差异、节点/边 ID 和 UE 布局变换；同时冻结 `status/advance/observe` 的准确字段、ID/版本/水位、错误码、JSON 安全整数和有限浮点规范 | reviewer 对照现有公开 API 与 UE JSON 能力，检查反事实期望预先记录、字段可解析、错误能拒绝、规范无双写；此卡接受后 AUTHORITY/UE 才可并行 |
| G2-AUTHORITY | G2-SCHEMA-FIXTURE / 新组合 worker 与定向测试，不改旧 worker 存档 | 单权威事务、Genesis 候选、发展节点/因果边、历史/恢复/幂等/拒绝 | 同机固定两相输入的 `influence_mm` 差异、反事实对照、重复命令、错误无提交、重启续算；原始 JSONL 与哈希 |
| G2-UE | G2-SCHEMA-FIXTURE / UE 插件新解析器、GameMode/Actor/输入；不改引擎源码 | 只读呈现初态/中间态/发展态和物理轨迹，结果身份校验及键盘导航 | UE 5.8.3 构建、NullRHI fixture、真实 Metal 三切片与逐项只读哈希；错误响应不应用画面 |
| GQ-RUN | G0 目标机/窗口与 G2 集成 / 独立证据目录 | CPU/GPU 短探针及冻结后正式 trace | 缺 GPU 信号 `inconclusive`，FPS 回读不算帧时间 |

G2-AUTHORITY 与 G2-UE 仅在 G2-SCHEMA-FIXTURE 经独立审查并冻结共享 wire/schema 后并行；G3 必须从准确集成提交做同一 world 的 UE↔worker↔Genesis 往返，G4 由非实现 owner 复核。各叶卡独立 worktree/PR，写文件范围由统筹发布时具体列出。

## 5. Check 与开放门

技术探针至少检查：初态、中间态、发展态三切片；两种预先固定物理刺激的可区分结果；同一命令幂等；错误请求与 Genesis 失败无提交；重启前后发展节点、物理向量与事件摘要对照；UE 相机/帧率/暂停/历史查询逐项只读。每次运行保存准确代码/fixture/Genesis/UE build、完整请求响应、checkpoint、状态/事件/因果摘要、Metal 原图和原始性能 trace。按[S3 方案](seed_tree_genesis_acceptance_proposal.md)判 `pass/fail/inconclusive`，不把旧植物或旧单刚体证据算入组合门。

**S0 产品门仍开放：**抽象发展结构最终拓扑和世界语义、正式物理对象/规律、目标负载、视觉标准、性能/内存/恢复阈值与预算。上述缺口不阻止有界工程探针，但阻止宣称“4D 世界演化规律”或产品版本通过。本草案已获独立技术审查，允许先派 G2-SCHEMA-FIXTURE；它的准确 wire/fixture 经独立审查冻结后，才可发布 G2-AUTHORITY/G2-UE 实现任务。本文件本身尚无运行证据，也不是产品验收。
