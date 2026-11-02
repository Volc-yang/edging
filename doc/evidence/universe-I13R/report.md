# I13-R：离线工具集成与 no-go

父节点I13。owner=root，非owner reviewer待u9。输入基线 `5e8a81d5fb18fc87ee50178819c7d52942573df1`，包含已独立审查/CI集成的A/B/C（PR107/108/109）。本任务在 `.worktrees/i13-readiness` / `codex/i13-readiness` 排他修改shared runner的被动CLI、对应新CLI测试和本目录；不改旧verifier、launcher、产品、私钥或权威状态。没有发新实机卡/新UE运行。

## Do / Check

- `i13-plan` 组合三个已接受模块的版本/源码摘要、冻结20/5请求manifest、A阶段60/60/240/40/20及C原PNG限制；核对各session interaction项预算一致。只报告计划，不派发资源。
- `i13-readiness --spec ABS --accepted-source SHA40` 验证 `universe-i13-readiness-input.v1` 的准确源及公共能力review引用，输出持久化缺口；no-go退出2，矛盾/参数错误退出1。`--output`沿用exclusive写入，不覆盖已有失败。
- 旧R12 plan/run及严格解析保持；新CLI永不调用supervise、launcher、UE、worker、solver、UI或provision。即便能力review结构完整，也明确缺R13 dispatcher/最终bundle适配，仍no-go，不暗用旧subtotal绕过新资源门。
- 本地首轮5个CLI tests中4通过、1个测试夹具错误：沿用emit在给定--output时只写文件，夹具却读取空stdout。仅修测试读取输出文件，受影响1项复测通过。独立review将对最终5项复核；PR CI负责集成全suite。该失败不是实机失败或产品修复。

A root独立16项通过，C最终23项通过；B cd0994f root19项通过，之后42b03db仅retain0/null修正，root3受影响项通过，最终B有21项。各PR最终CI均success；原自检/限制见各owner报告，不能据重复检查累计虚构不同门数量。A每个tracked child实际wait要求尚未由实际adapter提供。

## R 决定：no-go，S1/S2 skipped

1. 现有UE没有B要求的结构化实际camera/visibility/input/pause等读回producer；历史拒写更须真实handler事件、计数和拒绝原因，状态同样不动不能代替输入抵达。
2. CUA文档仅pressKey/组合及duration，跨history→current持键/实际事件顺序没有证据。不能因API可调用就宣称held_input已测。
3. S1逐动作240s只有拟分配，没有全部命令/markers/maps/原PNG/恢复的可信耗时上限依据。
4. R13新卡、独立observer生命周期/真实wait/最终seal适配及新版bundle组合尚未实现。本轮只完成被动工具入口；完整R实现与运行放行均未接受。

`preflight-discovery.json`（先前统筹检查点）记录源/布局/API事实；它不是新部署实测。原生Shot方法有UE安装源依据、C有合成检查，但首次真实PNG仍待新窗口首段验证。原G-B2、I12资源门及真实双normal会话状态不变。

## Act / 下轮输入

接受A/B/C及本轮被动工具层；R运行ready门no-go，S1/S2未执行。V必须独立结算此停止路径，不把没跑写成pass。保留I12原失败/世界/原件；本轮没有覆盖或重置2566/1200账。

后续最小依赖：先发布只读UE诊断producer窄任务（固定B schema，实际handler计数、真实状态、默认关闭、不触碰权威写路径）与R13控制/最终verifier适配任务，路径隔离后可并行；再由独立review解决持键方法和可行性证据，重审冻结manifest及预算。耗时或输入不可行时版本化拆解任务/门而非静默降门；不把额外实机探针藏进离线准备。新运行仍须准确source/card和独立全局窗口，不追加本轮试跑。

此报告是工具交付和no-go检查，不是整个I13/G-B2接受。原始CPU/CLI产物保存在DevSSD，结束后记录索引与独立review；未对网站/DNS/API或用户脏checkout操作。

## 独立复核结算（2026-11-02）

u9非owner逐差异审查通过，在sourcef8e0e65独立运行最终5项CLI CPU检查全部通过（0.321s）；没有扩大到实机。u7对V停止路径核查5个公共原件bytes/SHA及模块源码pin一致，index SHA `989ec5e3bd32a45c71d01f11550b0238f0feaf7a478981d949e570fdb610ebd2`；支持R partial/no-go、S1/S2 skipped、V停止路径结算完成，未授整体I13/G-B2。

CLI单命令实测0.046756708s不是整个离线准备耗时、GPU窗口或全局资源门证据；本轮未建立实机全局observer账，不声称新1200s门通过。V没有从runtime_started=false推断全Mac进程静默，最终进程清单由统筹另作被动检查；消失/未见进程不冒充实际exit0。下一轮仍须原PNG/quit guard明确能力review及S1首段实际验证，不追加隐藏probe。
