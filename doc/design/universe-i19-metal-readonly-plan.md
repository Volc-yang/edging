# I19：真实 existing 世界只读 Metal 能力采证

2026-11-09；输入 `3a15f594bda3403af9d87d8efbfaf1eac706176e`，integration `codex/plan-consolidation`。root 统筹裁决；用户“继续”承接已记载下一步。当前 **C-only方案经独立reviewer接受，P/R/M未就绪、运行未派发**；I18 exact3 有限门及旧失败保持。

## Plan / 方案树

目标：以 UE5.8.3 发布版和既有 `5a6cca0` 构建，从已存在世界取得真实 Metal 画面、输入、原生 PNG 与正常退出证据。单 writer，空 grants 的 readonly owner，不初始化、不推进、不新 Genesis solve。不授标准双会话/G-B2；新响应不能套用 I18 exact3。

`0只读调查/独立审定 → [C控制器小修 | P动作与运行原件准备] → R集成/CPU/CI/准确输入ready → M一次Metal → X本次≤3原始响应 → T一次Native → A独立验收 → root结算`

0：两个只读 subagents 已查明 Metal 尚缺 Native 已有 NoTrace/短独占 DDC/稳定写者 barrier。UI 控制器已连通但首次 inventory 超时、重试约30s；这不是 UE 失败，必须在 dispatch 前确认短动作可行性。0审查通过后才创建写任务 worktree，固定在仓库 `.worktrees/`。不新增通用运行框架。

## 叶任务与 P/D/C/A

| 节点 | owner/排他路径 | 固定步骤与 Check | Act |
| --- | --- | --- | --- |
| C | runtime agent；`scripts/universe_iteration/capability.py`、定向 CPU tests、`doc/evidence/universe-I19C/` | Metal 加 NoTrace、phase独占短DDC，退出三新quiet样本+console/log稳定fingerprint，实际DDC/Zen核对及seal再校验。复用现有Native规则，不改变parser、预算或标准门。负例覆盖晚写/残留/路径冲突/假正常退出；独立代码审查和最终CI | 拒绝则仅返工C；不得靠新UE运行调试工具 |
| P | root；`doc/evidence/universe-I19R/`及新DevSSD运行原件 | 复用既有inputs/source/binary/build，绑定新tool/run/before_map/card及两phase DDC。按现有probe_manifest v1先核48-call/2s普通步/10s chord实际可行性，原生Shot走capture API。动作成本不实测则不伪称ready | 若当前界面延迟不可满足，明确记录最小阻塞/提出版本化范围，不能静默放宽旧阈值 |
| R | root集成，独立reviewer | exact diff/实际CPU/CI、source/binary/runtime引用全核，六域metadata before、61-file map、UI连通且未锁屏、无别的UE、全部审批在clock前 | 任一缺证no-go；保留旧构建，不自动重试 |
| M/X/T | root唯一GPU/UE/CUA owner | 一次Metal，existing startup→只读矩阵/真实输入/SDR原PNG→正常quit/actualwait/稳定seal；只将实际完整新Observe≤3加入一次Native回放，四完整selector和actualwait不变 | 若M无完整响应则partial/abort不运行T；仅UI缺证但新响应完整、已静默且预算足，T可独立验新响应，M仍partial |
| A | 独立reviewer；`doc/evidence/universe-I19A/` | 独立核原件/argv/env/PID/wait/全部字节与map/Native exact SHA/PNG和真实输入。正式machine review按稳定路径再复验；各门分别评价 | 实际缺失仍fail/inconclusive，不以任一成功代替父目标 |

## 运行边界

沿I15完整计量root新I19子目录，不覆旧原件；复用原owner/context及空grants派生配置，key不读/复制/hash，authority不迁移。只metadata检查Zen、UBT两域、全局DDC两域、Trace六域；不冒称全OS I/O审计。global900s/2GiB、Metal420s、Native180s，最迟Metal360s主动quit，所有权限/ready在clock前。已有约1.587GB，Metal shader/DDC新增可能超余量，实际运行前重算；不事后抬门槛。

每UI批次先核精确PID/日志/余量，优先独立Space/全屏且不改系统显示设置；退出后不用getApp/状态刷新重启UE。Space先于H的held顺序未证明时不伪造通过。当前CUA仅原生pressKey/drag等能力，不能用shell或CGEvent替代UI。原PNG必须来自稳定UE视口，核magic、尺寸、实际Metal/SDR及文件原件，不转码外部截图冒充。

主checkout用户改动、旧goal、I12B恢复树/I15构建树、网站/DNS/API不动。C产品工具需独立PR；纯计划/执行/独立文档可按仓库等价审查记载集成。任务结束更新backlog/register、范围commit/push，依赖核对后仅non-force清理本轮干净临时树。

## 0独立审查裁决

`/root/i19_review` 2026-11-09只读审查：接受C-only隔离实现，P/R/M仍no-go。C额外冻结trace目录清单/全部原件，Native前及最终seal再核Metal frozen；phase DDC不碰撞，Native旧schema/行为不改。root接受；写树从本方案提交固定，不等UI成本问题解决才修确定的Python缺口。P必须测物理操作和真实往返，不把48逻辑命令当48物理操作，不改旧计时起点。审查本身未运行UI/UE/worker/solver或读owner/key。

## v2：小批次显式成本与范围（已审定，尚未运行）

CUA预检工具wall为12.9134s而内部仅822ms；v1的2s不能满足。root与独立`/root/i19_review`接受新显式opt-in cardformat/scope及**精确固定subset manifest**，旧v1/48步/2或10秒全部不变，不是旧门通过。新20s步骤上限是dispatch前暂定成本，不回溯更改失败；全部物理console打开/输入/提交/关闭/AX及往返、map/receipt都计入，实际物理数另记。

固定14逻辑步骤：probe4/90s（Arm、实际viewport/guard readback、1张原生PNG、Disarm）；history1/25s（ObserveExact 0 1 1）；history拒写5/110s（Arm、真实Space、真实R、released readback、Disarm）；final3/70s（Arm、restored readback、Disarm）；quit1/40s。交互295≤300，startup60、Metal420/Native180/global900/2GiB不变，不重试。只得3真实请求status/current/history和2新Observe，final selectedH1/trustedH2；没有H/latest。camera/visibility/FPS/pause/held明确deferred。5s交互余量很窄，未实测不称ready，运行时不再扩上限。

P写任务排他`probe_actions.py`、新定向tests、`doc/evidence/universe-I19P/`，固定新manifest/receipt/evidence验证，旧入口不变；C2在C已集成后独占`capability.py`，仅严格新card/scope/精确manifest可20s，CLI形状不变；各自PR/CPU/独立审查/CI。C和P不同文件可并行，C2依赖C与P冻结接口。root拥有执行原件/driver，A在最终源冻结后审ready。完整矩阵及G-B2持续open。
