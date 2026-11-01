# H6B 早期独立代码审查

状态：代码层限定实现无阻塞；不是最终 PR 或运行验收通过。
审查者：非实现 owner `h1e_independent_review` 与统筹。
输入：`b1d526e`、`7c137dd`，基线 `489b97c`；测试夹具后续修改尚待最终提交复核。

CharacterMovement 接收连续输入；Tab 保持同一 Pawn，只切 ViewTarget、清理
速度/输入和切换 MovementMode，未修改 pose。安全入口验证实际地面斜率与
胶囊 blocking overlap，近侧阈值提前恢复符合安全目标。Space 只有一次
IE_Pressed 绑定；导航、Status、Trace 不调用权威推进。采样初始关闭，有限
0–10 世界秒；实际 capsule OnComponentHit 来自 UE 移动 sweep 阻挡。
未发现本次单人 Standalone 路径中的明确相机、委托或空指针功能阻塞。

独立审查发现进行中的测试夹具以 GameInstance 创建 `ULocalPlayer`，违反
安装 UE5.8 `LocalPlayer.h` 的 Within=Engine。已协调改用合法 Engine Outer。
前几次夹具失败必须保留，不归因为产品移动或碰撞结论。

统筹随后直接读取本地 `H6B-20261101/nullrhi-bchkcP9v/ue.log`：
`OverviewRetainsPawnAndPosition` 与 `SupportMovementCollisionRecovery` 均有
原生 Test Completed Success，未见 Error/ensure/assert；报告两项 state 也为
Success，但顶层 succeeded=1，须在最终报告披露，不把顶层字段改写成 2。
实际进程退出与源码/binary 身份仍以 owner 最终封存记录为准。

草稿 PR #66 的 CI 成功不能替代此 UE 检查，更不能替代真实键盘/Metal 运行。
Mac 会话锁屏，统筹已请求用户解锁。连续键盘运动、真实墙栏接触、Tab、正常
步行触发边缘、逐项权威文件哈希、显式 Space、恢复与退出门仍待 UI 采证。
最终须纳入 observation.md，排除本任务自动生成的 DefaultInput.ini，并复核
最新测试修改与证据；未合并，不移除该部分完成工作树。
