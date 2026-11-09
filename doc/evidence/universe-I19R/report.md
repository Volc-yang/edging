# I19R — 工具接受，实机门未运行

2026-11-09；本轮 **partial，已结算**。三项独立工具 PR 均已审查、最终 CI 成功并集成；实机未启动，不能授 Metal、PNG、输入、新 Native 或 G-B2。I18 exact3 有限接受及既有失败保持。

## Plan / Do / 工具结算

| 任务 | 提交 / PR / 集成 | 实际检查与评价 |
| --- | --- | --- |
| C Metal NoTrace/DDC/writer barrier |453fa9c / PR125 /37a46ed|owner13新+11旧CPU、CLI6；独立24+6；CI42584966514 success，工具接受，Metal实测仍未执行|
| P 固定只读切片v2 |7b5349e / PR126 /8c3523d|owner23CPU，独立33；CI42586193156 success；14逻辑/1PNG/3请求/2新响应，final selectedH1/trustedH2，旧48步门保持|
| C2 版本化许可/完整计时 |7c37e3b / PR127 /ef3d44d|owner64CPU，独立40；CI42587829711 success；只有新精确卡/manifest可20s，v1未放宽|

没有 UE/C++/worker/solver 功能改动或重构建。root 执行原件经独立审查修正并冻结95bcb20；首次 prepared/card、61-file map、真实 build/source/binary 和两条独占短 DDC 均经 ready GO。真实无 UE CUA schema 预检由同一 parser 复核，而非按猜测生成原始记录。

## Check / 实际停止路径

唯一启动的实际执行进程是 root driver/controller6864。root 的 shell here-doc 包装把标准输入接给了 Python 启动程序，继承到 driver 后无法接收 TTY 命令。控制器输出 ready，但发送的 start 没有被它读取。**没有 UE Popen、worker 或 Native**，`abort.json` 的 phases 是空对象。root 用该终端的 Ctrl-C 停止它；exit2、normalfalse，111.178584834s。此为可避免的执行接线错误，不是 UE 错误，不能据此判断真实渲染/键盘行为。

首次 [DevSSD resource receipt](/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe/I19-20261109-metal-slice/prep/resource-review.json) SHA `a9654fc21cf83780910f37d4c62a82440706749812bddb3c3e7224df31085a06` 保留fail；进程静默、61-file authority map不变、六外域变化0、完整计量1,692,672,927B。观察和元数据原件照常保存，没有把失败重写为未发生。

root/独立审查只允许一张显式 attempt2 卡使用尚未消耗的唯一 UE 窗口，原 driver/inputs/失败原件逐字节不变。新执行原件471149c仅复制到独立文件和目录，额外绑定原父deadline `2026-11-09T09:08:10.799685+00:00`、独立关闭 watchdog、Metal启动至少510s及Native至少270s余量，绝不重置原900s。A2输入SHA `fb7ab0ac58f3d7008ed50eb840e89de1a1faf472acabb614cd2d7cb8cd493abc`；准备/独立审查后，实际只余419.89282s<510，ready **NO-GO**。A2 controller/DDC和UE均未创建，未另开第三卡。[独立结算](../universe-I19A/report.md) source0637eaa等价集成aeead0e，197份原始ps/maxgap0.574582458s复核无UE。父周期观察间隙仍fail/inconclusive；即使局部后来成功也不能补回，本轮没有此局部运行。

## Act / 下一轮直接入口

本轮工具节点接受；R运行节点失败；M/X/T为未派发/skipped；A独立停止审查完成。完整矩阵、Metal/真实输入/PNG/新响应Native和G-B2继续open，不把工具合并或ready检查代替产品门。

根因对应的修正已用[无UE的TTY健康检查](stdin-health.json)实际验证：`python3 -u -c SCRIPT`在同一TTY成功收取ping并exit0。下一轮应先用该直接TTY方式；执行driver命令直接使用`caffeinate -di python3 -B DRIVER INPUT_SHA`，**不使用here-doc占用driver stdin**。全部准备/权限/独立ready在新运行clock前完成，第一步先验证控制器stdin握手再派UE；无需再做工具功能实现、重构建或重复CI。新运行必须新身份/新预算/新原件并保留本轮失败，不能复用过期的A2父deadline或I18 exact3覆盖新响应。

[416文件索引](runtime-evidence-index.json)记录两次准备与首次控制器的全部公共原件，106,021,011B，提交前逐项重读size/SHA。没有复制凭据或私有owner内容。清理仅本轮干净且已集成/报告归档、无运行配置依赖的任务树，分支和DevSSD原件保留；详见[清理记录](worktree-cleanup.json)。integration/I15构建/I12B恢复树及其他历史树保留。主checkout用户改动、旧goal、网站/DNS/API均未改。
