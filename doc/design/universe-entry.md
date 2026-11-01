# U6：进入、载具与同世界重访设计

状态：v0.1 **proposed / 待独立设计审查**，2026-11-01；parent=U；depends_on=U1 source `a7fed69`、U5 source `ec8bf6e`。固定交付基线 `6f3c142aed2f67b556d87e2b649735e6c7fd4b2b`。独占本文件，不修改角色、GameMode、worker、配置、世界规则或存档。

## Plan：已定、已观察与目标

- **已定：**[总树](../universe_architecture_design_plan.md)的总目标含载具登陆、人类游玩与重访；当前 V-HOME 的必需门不含完整载具。Seed→Tree 为抽象因果发展。万物有灵，世界内玩家化身也属于世界之灵；何时建立独立可追踪化身/灵域记录及其能力仍由产品裁决。
- **已接受设计输入：**[U1](universe-identity.md)的 Account/Session/Avatar 分域，AvatarId 如单列须版本化绑定同一 WorldId 的 ExistenceId；[U5](universe-origin.md)提供六类共存和候选五区主线加森林—蛮荒支线，实际接点、通行与水文未实测。载具入口不能将城市入口或任意海岸坐标默认当安全着陆点。
- **有限观察：**[H6C 复核](../evidence/home-visitor-independent-acceptance/coordination-review.md)接受准确 `f674483` Mac/Metal 开发入口下安全出生、连续运动、真实墙栏接触、阈值恢复、Tab 保位、两模式显式 0→1→2、历史纯读及重启。它不证明完整载具、账号权限、世界化身物理、pose 持久化、写实/性能或跨平台。
- **源码观察 @ 本基线：**[GameMode](../../engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost/EdgeWorldCausalGameMode.cpp)创建本地 Character，Tab 停止运动并切换 ViewTarget；[Character](../../engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost/EdgeWorldVisitorCharacter.cpp)用 UE CharacterMovement/本地支撑测试和阈值返回入口。当前 Space 命令从最新 head 构造，不等于已经实施下文“历史模式禁世界动作”的新门。

**本卡目标：**设计有限的访问状态机、身份/写权和错误返回边界；为 U4/U7/U8/U9 提供可判失败的接口输入。UE5 发布版相机、CharacterMovement、项目插件/适配优先；无证据触发引擎源码改造。资源限定一份设计及最多两轮定向修订，不启动 UE/Genesis/GPU、不下载资产、不调用模型或付费服务。

## Do：身份与访问上下文（候选逻辑字段，非新 wire）

| 域 / owner | 设计建议与边界 |
| --- | --- |
| `AccountId` / 外部身份服务 | 外部持久主体；可信服务产生 principal/权限，不从模型、客户端字符串或 Pawn 名采信身份；凭证不写世界事件或采证日志 |
| `SessionId` / U6 访问层 | 一次有范围/期限的访问会话，绑定账号/guest principal、world、能力与连接 epoch；断开/过期不删除世界存在。新连接不能接收旧 epoch 的回调或按键 |
| `AvatarId → ExistenceId` / U1、U6 与权威 U4 | 如产品选择独立化身记录，关系必须带准确 world、有效 revision/规则版本及来源事件；存在身份独立于本地 Pawn 生命周期。具体创建/占有/释放规则待裁决，不因打开窗口自动分配灵域 |
| `VisitContext` / U6 | world、entry_request_id、session/epoch、已验证 head、访问模式、载具/化身绑定、授权范围、最近有效当前 ViewBinding、本地访客 pose/支撑引用。后者仅会话可重建状态，默认不持久写世界 |
| `ViewBinding` / U7 | world、viewed tick、source revision/watermark、状态/规则/投影/资产及碰撞版本；另保存最新已验证 head。具体字段与编码由 U4/U7 冻结，不从 tick 推定 revision |

匿名观察能力如采用，必须作为显式 guest grant，不因未登录而拥有世界写权。暂无独立化身记录的技术访问可使用临时本地观察代理；这只定义工具权限，不否认玩家世界内化身属于世界之灵，也不提前决定其出现阶段。已存在化身的选择/占有不得跨 world 或把 AccountId、SessionId 直接当 ExistenceId。

建议 `entry_request_id` 在 `(world,principal,session epoch)` 内幂等：同输入重试返回原访问结果，不多次创建/占有化身或重复执行着陆命令；同 ID 异内容拒绝。实际权威创建/占有如需命令，由 U4 的稳定 CommandId 和去重保证，不以客户端“已显示一次”代替提交去重。

## Do：两类载具路径与权威分工

| 候选路径 | 控制与碰撞 | 世界影响 / 恢复 |
| --- | --- | --- |
| A 纯访问载具 | UE 发布版相机/Pawn 或受支持的车辆组件表达飞行/着陆；本地物理仅服务访问体验。选用 Chaos Vehicles 前须核对目标 Mac、插件/输入及实际构建，不预设当前已启用 | 不创建权威实体，不生成因果事件；“着陆”是本地视角到安全步行点转换，不代表真实质量/接触被 Genesis 验证。重访重新安全进入，不承诺载具或访客 pose 存档 |
| B 权威实体载具 | 明确 `Vehicle ExistenceId/PhysicalObjectId` 映射；Genesis 是批准物理范围内候选来源，输入按版本化显式命令交单权威协调器。UE 展示/输入采样不能反写另一套权威 transform | 着陆、接触、载客、损伤等世界作用须先有规则/单位/步长/权限与事务契约。退出/重连从权威 head/checkpoint 复原；UE 预测如后续引入须标非权威并校正，不用预测完成替代已提交事件 |

**推荐分期（proposed）：**先用 A 验证入口、观察/控制交接与恢复，再为 B 单立有界物理场景；它减少同时扩展的接口，不替用户取消真实物理/载具总目标。当前本地角色阻挡不等于 Genesis 化身物理。本地安全返回只移动观察代理；若化身/载具 transform 是权威数据，本地不得私自传送该存在，需保持最后提交状态、脱离到安全观察，并按批准规则另发恢复命令。

## Do：访问状态机与输入门

所有转换均为设计建议。`Current` 表示显示的 ViewBinding 与用于动作的最新已验证 head 一致，不能只比较画面 tick；head 在等待期间变化时重新校验。一次本地模式转换不是世界提交点。

| 状态 / 转换 | 进入条件与输入 | 失败或退出策略 |
| --- | --- | --- |
| Outside → Resolving | 可信会话/guest授权，选择准确 WorldId；读取 status/身份和已有未决 CommandId | world不存在/权限拒绝不创建新世界；网络超时不能当世界丢失而重置存档 |
| Resolving → LoadingCurrent | 固定请求 epoch，校验 head/schema/规则与视图绑定；异步准备区域、资产和本地碰撞 | 错世界/迟到回调丢弃；缺块/版本错保留最后完整视图并显错，禁世界动作 |
| LoadingCurrent → VehicleAccess | 完整当前视图可用，路径A具本地入口、路径B具已提交载具与权限 | 无载具实现时可显式标“技术步行入口”，不能伪装完成登陆；路径B不得以临时Pawn补造权威载具 |
| VehicleAccess → WalkingCurrent | 转移控制前停输入、校验安全落点/支撑/胶囊及同世界切片；B还需已提交的退出载具/化身状态 | 落点不安全则留载具/安全观察，不强行降到空白或另一tick地形，不自动推进寻找“安全未来” |
| WalkingCurrent ↔ OverviewCurrent | 释放持续输入/速度，保留同一访客和本地pose；总览/步行转换不创建第二化身 | 控制对象丢失则退安全观察并显错；有因果动作另经过权限/expected revision/规则/唯一提交链 |
| Current → HistoricalSurvey | 保存当前访问上下文，停止当前本地运动，装入准确历史 ViewBinding；历史仅可相机巡视/查询 | 默认禁所有权威动作，包括本访问入口的 Space/交互/驾驶及从该历史视图发起的 AI世界提案；不据此暂停独立的已授权世界任务；过去对象不可通过未察觉的键盘焦点作用于当前head |
| HistoricalSurvey → Current | 显式“返回当前”请求，先刷新最新head/完整投影，重验支撑，再恢复本地控制；不重放历史期间按住的键 | 原pose不安全则对路径A选择已验证本地安全入口；B退为安全观察，权威恢复另走规则命令。失败保持历史只读或错误观察，绝不混用画面与障碍 |
| 任一访问状态 → Leaving → Outside | 停输入/取消本地异步应用、保存必要命令receipt、按生命周期结束会话/关闭窗口 | 离开不隐式Advance、不删除世界、不自动持久化pose；在途命令取消不等于权威撤销，先查原 CommandId 结果再决定重试 |
| Outside → Resolving（重访） | 新epoch，明确选择同一WorldId/状态目录；载入已提交head后重新安全进入 | Session可更新、Avatar如存在仍按版本化绑定解析；pose重新安全出生不判存档丢失；提交不确定遵循U4停写/恢复 |

与 U7 的候选对齐：历史模式优先采用纯相机巡视，历史几何不进入当前活动碰撞层；若以后要求“走入过去”，必须另立同切片碰撞/观察代理契约，不能复用当前角色物理。历史/当前投影切换须统一更新 ViewBinding、画面、HUD 与碰撞许可；加载中的混合画面不能标为当前可操作世界。本卡不会修改 H6C 的既有本地胶囊/地面数值或假定六区已通行。

显式世界动作可由步行或总览发起，但须处于 `Current`、会话有效且意图/目标在授权范围内。新设计建议历史模式仅提供只读查询和明确返回当前操作；若将来支持基于历史反事实实验，应使用独立分支世界/沙盒与显式契约，不能默认为原世界时间旅行写入。输入焦点、历史标签和禁用原因属于访问控制反馈，不显示内部schema细节给一般玩家。

## Check：有界正反例矩阵

下列均为设计 fixture，**新运行门 planned**。固定 W 的当前 head 为 tick4/revision7、历史样本 tick2/revision3（仅示例，不强制二者相等），访问A；若选择B，另附已批准化身/载具规则和物理工件。

| Case | 操作 | 设计预期与可判失败信号 |
| --- | --- | --- |
| P1 访问与重访 | 同principal选W，当前加载→A本地着陆→安全步行→历史巡视→返回当前→正常退出→同W重访 | 观察转换逐项权威文件集合/hash不变；新Session/epoch可以变化，世界身份与已提交head恢复；本地重新安全出生。若仅相机/登陆动画导致世界推进即失败 |
| N1 错 world/绑定 | W会话收到W2样本、W2 Avatar/Vehicle绑定或旧连接回调 | 拒绝应用/占有，保留最后准确视图并禁写；不得“自动改世界”迁就回调。错世界或旧epoch得到控制即失败 |
| N2 过期/撤销会话 | 有效加载后会话过期或权限被撤销，再发世界动作 | 不生成新权威命令；退只读/重认证，已提交命令可查询原结果。若借仍存活Pawn绕过权限即失败 |
| N3 重复进入 | 同 entry_request_id 与相同payload重试，再以同scope同ID换载具参数，另测会话内改world | 前者返回既有进入状态，不多次spawn/占有/提交；改参数为ID内容冲突，改world为会话绑定错误（不是跨world的ID冲突）。客户端重生/重试导致两次世界创建或推进即失败 |
| N4 历史动作 | 观看tick2时按Space/交互/驾驶键，随后返回当前 | 历史期间仅查询/相机有效，无命令/事件；返回前清除held输入，不将按键延迟触发当前动作。历史显示虽正确但head被隐式推进仍失败 |
| N5 加载失败/安全返回 | 当前块缺资产/碰撞，或返回当前时原pose处已不可站立 | 不把不同切片几何/碰撞混合；A退已验证本地安全入口，B不改权威transform而退安全观察。无支撑仍开启步行或擅写传送即失败 |
| N6 在途命令离开 | 合法Current世界动作已发送但响应丢失，用户退出/重连 | 按稳定CommandId查询后恢复；同命令至多一次提交。取消请求不得被当作回滚世界，未知结果不新造命令重复执行 |

未来每例固定代码/build/目标机、输入/会话epoch、WorldId、视图身份与资产/碰撞来源，保存原始状态机/请求响应、实际Pawn/ViewTarget/支撑、逐项权威前后文件集合和哈希、正常退出/恢复证据。H6C 的原35组只读与两次推进只在原版本边界使用，不能代替新会话、载具和历史动作门。

## Act 与交接

- **Plan：**读取固定 U1/U5、H6C 准确结论及角色/GameMode源码，分开现有技术访问与未来账号/载具/化身权限。
- **Do：**本文件交付身份上下文、A/B两路径、有限状态机与P1/N1–N6；另只读对照 U7 source `38f8e02` 的候选 ViewBinding/碰撞方案并向其 owner 确认无冲突；该提案未冻结，未引入额外实现依赖或修改其文件。
- **Check（owner 自检）：**已核对6/6相对链接存在、工作区仅新增本文件，暂存差异格式检查通过；人工核对状态转换与P1/N1–N6覆盖，entry幂等作用域与错world拒绝分开。与U7 owner对照历史隔离/支撑恢复无冲突；没有运行UE/Genesis或新的实际访问检查。非作者审查和全部新运行门仍 planned。
- **Act：**U4合成entry/command幂等、占有/退出事务与未知提交恢复；U7合成ViewBinding、epoch迟到拒绝及历史/当前碰撞；U2界定B路径物理对象/单位/步长，U8制定访问负载与采证预算。冲突只返工对应接口，不重开已接受的H6C人工鼠标用例。

待产品裁决：A/B分期及完整载具目标、化身何时有独立记录/能力、载具/玩家的真实物理作用与恢复规则、地理入口/六区通行、历史模式是否扩展。接受本设计只放行后续设计/契约，不代表载具登陆、多人账号、写实世界或正式性能通过。
