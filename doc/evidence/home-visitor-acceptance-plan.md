# H6C：非实现 owner 的访客组合验收

状态：H6B PR #66 已审查集成 `a2ae0f1`，统筹放行独立实施，准确基线见发布卡。
日志格式按 H6B observation.md，独占构建/GPU，不并行修改共享产品代码。

## Plan / 边界

只写 `doc/evidence/home-visitor-independent-acceptance/` 报告、采证 harness 与
紧凑索引；原始资料独立保存在 DevSSD。不得修改角色、GameMode、环境、
Worker、viewport 或启动器。使用标准 `--launch --viewport-preflush`。
实现 owner 的构建、自测和图片都是输入，不能代替本卡独立运行。

观测命令已由统筹和 H6B 协调：只读 `VisitorStatus`；显式 `VisitorTrace <秒>`，
最长 10 秒、默认关闭。快照/采样包含时间/frame、实际 Pawn/ViewTarget、
位置/旋转/速度、MovementMode/IsFalling、胶囊尺寸、CurrentFloor 支撑信息
与 Actor/Component、忽略自身的实际 blocking-overlap。阻挡需实际运动 Hit
或能关联该次阻挡的等效原生证据；恢复需原因/阈值与前后位置。日志确切布局
以 H6B 经审查的交付为准，H6C 不并行写共享接口。不增加 teleport/强制推进。

## Do / Check

1. 核对准确提交、源码/binary、实际 PID/log/UserDir；初始化和有效 tick0
   后才绑定 UI。保留首图、光照零计数和显式同步模式日志。
2. 出生时胶囊无 blocking overlap；落稳后有 walkable floor 支撑，稳定高度，
   无持续下沉或恢复循环。以实际胶囊与地面约 z=-140 的关系判断。
3. 自由通道单次持续输入期间记录至少三个不同 frame 的实际位置/速度，
   再松开核对停止；转向单独采证。两张不同画面不能证明连续移动。
4. 通过正常步行分别接近墙和栏杆；在非零输入区间取得对应实际 blocking
   Actor/Component、法线/位置及初始穿透信息，确认未穿越并可反向脱离。
5. 远离入口后 Tab 到总览，操作历史/转向，再返回。核对 Pawn/ViewTarget、
   模式和步行位置；总览不导致角色漂移、重生或权威推进。
6. 正常步行触发近侧边缘安全恢复，记录原因/阈值和前后位置，恢复后无
   穿透、可站立和继续移动。若实现提前在安全阈值返回，不要求先坠落。
7. 步行/总览各短按一次 Space，逐次等新 ack，恰好 tick0→1→2；随后
   history0/1/2、H、R 分别核对新响应与画面，发现重复提交即失败。
8. 每项导航、转向、Tab、边缘恢复、历史/刷新分别保存全部权威文件集合
   与前后哈希；同一区间无 Advance。不得以路线首尾一对摘要代替逐项检查。
9. 保存 tick2 实体并正常关窗，核对退出与清理；同 UserDir 重启恢复 tick2，
   无新增 Advance，再做一组导航/历史/Tab 只读和 CmdQ。跨进程只要求权威
   恢复与角色重新安全出生，不新增访客 pose 持久化契约。

每次采证显式传入 run/log/stateDir/PID，按操作前 offset 找新 ack。原件独占
创建，重试另建 attempt。工具超时先核对原进程，不重启活跃实例；丢失记录
披露并排除。会话锁屏时仅做不依赖界面的准备，不据无窗口结果判 UE 失败。

## Act

逐项 pass/fail/inconclusive。输入/位置/Tab/恢复错误退回 H6B；环境阻挡错误
退回 H6A；启动/退出按日志分类。导航改变权威时停止相关检查并保留现场。
通过只接受准确本机组合版本的有限访客路径，写实美术、正式性能、载具、
真人体验、PIE/打包/其他平台及原默认退出路径可靠性仍开放。独立 scoped PR，
统筹复核原始证据/CI后集成，再更新上下文与清理。

人工鼠标单次物理事件已由非owner独立复核；相关源码/配置/输入路径身份未变时可复用并明确来源，不称作H6C自身新鼠标运行。其它路线仍须本卡独立执行；只有新风险才再请求人工动作。
