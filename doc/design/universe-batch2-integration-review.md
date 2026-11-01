# U2/U3/U6/U7 第二批设计：独立审查与集成 Check

2026-11-01；父节点 U，固定派发基线 `6f3c142aed2f67b556d87e2b649735e6c7fd4b2b`。主统筹 `/root` 未编写这四份设计文档，逐卡审阅全文、最终树与写入范围；另安排非文档作者进行局部跨接口复核。本文不是 U9 最终审查，也不批准世界法则、新 wire 或产品运行门。

| 卡 / PR | exact source | merge | 工作 / 独立设计门 / CI |
| --- | --- | --- | --- |
| U2 / [#70](https://github.com/Volc-yang/edging/pull/70) | `b78b3ab7e2066fcd350b586aac71fa6b16567a19` | `88d34272ec58ff6d94c2b0a8772f5ac1f761dcd4` | 完成 / pass（有界设计） / verify SUCCESS |
| U3 / [#72](https://github.com/Volc-yang/edging/pull/72) | `9f2fe7e54d3475794a1577c18ffe8fdb0c3df58d` | `fc1f80ffa4cb00bdfea7a6fb28f3ab4a8f055d98` | 完成 / pass（有界设计） / verify SUCCESS |
| U6 / [#73](https://github.com/Volc-yang/edging/pull/73) | `95903b2a9432b9843b0b1f6e60b87a866482f878` | `c4c5f7e77dd3902e2d48f10ff12d7338587d8df6` | 完成 / pass（有界设计） / verify SUCCESS |
| U7 / [#71](https://github.com/Volc-yang/edging/pull/71) | `38f8e02f8b4049d2cb0ba19fecf56b6e5d3c846b` | `622c2d91db2f096cda56e93a2bbf5734f922bd94` | 完成 / pass（有界设计） / verify SUCCESS |

## 实际检查与裁决依据

主统筹确认四卡只各新增一份独占设计文档，`git diff --check` 通过；U2/U3/U6/U7 的本地相对链接分别 6/5/6/5 个全部存在。每个正反例都包含固定输入、预期和可判失败信号；新运行 Check 始终 planned。PR 合并均固定 exact head，最终源提交已成为集成分支祖先。U3 首次合并 API 连接失败后先核对仍 OPEN、head 未变和 CI，再重试成功，不以工具异常推断已合并。

- **U2：**对照现有 adapter 的单实体恢复限制，建议的动态体+固定支撑体是独立新实验，未称已支持多对象/接触恢复。物理角色与存在身份显式绑定；有 frame/单位/步数的候选交 U4 唯一提交，不另设物理 head。主统筹只做提案映射的代数核对：`S=diag(1,-1,1)`、`100*S*(1,2,3)=(100,-200,300)`，z 轴 90° 旋转经 `S*R*S^-1` 反向，`det(S)=-1`。这验证表达式内部一致，不验证 Genesis/UE 实际坐标约定；DOF 速度、姿态、接触公开 API、材料和误差上限仍待新探针。
- **U3：**校验可信 principal/grant/approval receipt、逻辑水位与墙钟准入分开、已提交重试先查持久结果、模型费用与世界动作预算分开。被拒绝可产生操作审计/费用记录，不能更改世界 head。固定输出/原审批与时间输入用于重放，不再次问模型或读取当前时钟替代原因。旧第一章动作与规则 fallback 未被升级为新宇宙规律，AI 不是当前 H6C 必需门。
- **U6：**Account/Session/Avatar 与存在身份分开；比较 A 本地访问载具和 B 权威实体载具，分期为 proposed。历史模式建议只读相机，禁止本访问入口的世界动作并清理 held input；返回先装齐当前切片、重验支撑。A 本地安全返回不等于 B 权威传送；退出/取消不被当作在途权威命令回滚。明确现有 Space 从最新 head 构造，新的历史动作禁用门尚未实现，不用 H6C 倒推通过。
- **U7：**Landscape/World Partition/HLOD/Nanite/Lumen/Water/植被是按需验证的发布版候选，不是本机能力已达标。ViewBinding 统一来源时间/规则/资产/单位，旧异步结果不能覆盖新选择，碰撞与历史画面同切片或暂停导航；本地投影原子应用不是第二个世界提交点。资产 hash 不替代授权，来源缺项不伪造许可；写实参考和正式性能均开放。

## 非作者局部复核与跨卡交接

`/root/u2_physics_design` 只读核对 U7 exact source，与 U2 的候选→已提交样本、单位映射、同对象无双权威模拟及历史不求解边界无冲突。`/root/u7_projection_design` 分别只读核对 U3 与 U6 exact source：权限/期限/幂等/重放和 H6C 必需范围无冲突；历史碰撞隔离、安全返回、held input、会话 epoch 与视图 generation 两层迟到拒绝一致。复核者未改被审文件、未运行 UE/模型/Genesis。主统筹采用结论并核对原文，未以 agent 回报代替最终范围和 CI 检查。

交 U4 的明确输入：物理 binding/config/candidate/checkpoint 来源、提案/审批/预算 receipt、entry/command 幂等及未知提交恢复。U4 仍须冻结 canonical 编码、标识分配/命名映射、writer lock、提交与恢复顺序；U2 的映射版本与 U7 `unit_transform_version` 需显式对应，不静默扩充旧 JSONL。

交 U7/后续 UI 的显示要求：proposed/approved/admitted/committed 分开；批准或准入不等于世界事实，只有提交后的世界状态可称已发生。U6 的会话 epoch 拦截旧连接，U7 view generation 拦截同连接旧视图，不能混作单一水位字段。

## Act

接受本批四份版本化设计。四个任务 worktree 在确认干净且源提交为集成祖先后已移除，分支、PR 和设计保留。没有 UE/Genesis/GPU 运行、模型调用、素材下载或产品代码变更。

下一 ready 为 **U4 事务/调度/恢复设计**（依赖 U1/U2/U3）；U8 等 U4 及既有 U2/U6/U7，U9 等 U4/U8 且由未承担 U1–U8 交付的 reviewer 检查。所有新世界运行门、正式规律/载具权威性、写实资产/参考、性能和规模阈值继续待决；本批完成不关闭整个 U 轮或 V-HOME 产品总门。
