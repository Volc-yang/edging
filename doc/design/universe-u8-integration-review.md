# U8 规模与质量预算：独立审查与集成 Check

日期：2026-11-01；parent=U。派发基线 `fb93c291fc594086c0115294e731e7501434b7c7`；source 演进 `d7e97d0 → f65d4b0 → 98890bafe73a1403a559f1a8ca6ef7270777ba26`；[PR #75](https://github.com/Volc-yang/edging/pull/75)，merge `06eb9eacdd7b87880df6cea9254935dcf91f7954`。

主统筹 `/root` 和 reviewer `/root/u2_physics_design` 均非 U8 文档作者。最终接受[U8](universe-scale-quality.md)为**有界设计交付**：工作完成、PR merged、独立/局部集成设计门 pass；新运行门全部 planned。所有新规模、数值阈值及运行配额仍 provisional，不批准世界规律、资产、目标硬件或压力运行。本次不替代 U9。

## 两轮定向修订

初稿未明确64条历史是否含初态、各测量阶段起始数据量和预热提交数。若接着64条历史测30次提交，已超上限；长跑另有相同风险。第一轮修订明确 H 为完整保留 root 数（含初态），各阶段独立归档/目录：R/C 从H1开始，C预热2+测量30后H33；长跑另从H1预热2+测量20后H23；H8/32/64恢复及流送归档只读，满额实例拒绝新增root，不以GC或重置掩盖增长。

第一轮当前结构 S 初态只列3存在+1节点，未把六类地理等纳入总typed口径。第二轮补完整域：地理、路线/段、水系/段、物理绑定、world及配置/规则/随机/预算描述计入；候选初态小计30+余量2，须实际schema枚举验证≤32。候选每步增长≤4，S上界改288：H64最坏32+4×63=284，不删节点/边。装饰D、资产A、几何点数/字节及历史/checkpoint/审计/孤立工件另域入账，外部引用不算零存储。计数不赋独立灵域含义，未列类别或超初态/增长界限必须重新估算，不能静默省略。

时间和证据不只逐项列上限：每阶段及完整剩余矩阵都须满足已用+后续上界+收尾预留≤总额，失败attempt仍计账。候选配额75分钟=70分钟阶段+5分钟保留，16GiB=14.5GiB阶段+1.5GiB保留；额外A/B或重试不自动扩预算。必要阶段缺证时全矩阵inconclusive，不以成功子集冒充完成。

## 实际执行的 Check

- 主统筹读初稿及两次 exact 修订，reviewer 分别复核；最终差异仅新增独占 `doc/design/universe-scale-quality.md`，8/8 本地链接、范围和 `git diff --check` 通过。
- 双方独立核算 H33/H23、初态30+2、S的R/C160/长跑120/H8、H32、H64分别60/156/284≤288，及时间/证据配额求和。此为设计算术，未生成或运行这些fixture。
- 核对帧/CPU/GPU时间不相加，错误快返不混成功Observe/commit延迟；A/V/D、完整性/D_recovery/ready分开，恢复全部历史引用不偷算；吞吐与延迟、启动/稳态/流送分组，失败/零/缺样及超时原件保留。
- 核对实际内部渲染像素与窗口points/HiDPI/ScreenPercentage分开，统一内存不同口径不双计，UE渲染+Genesis同会话是组合负载，整机采证归单owner，不能关闭UE替代组合测量。
- 主统筹只读取得当前 Mac16,8/M4 Pro/macOS26.6.2 及 `hw.memsize=51539607552 bytes=48GiB`，另记录DevSSD瞬时free bytes；未取GPU核心数、不猜目标规格。这些不是批准硬件或压力结果。旧600帧boot采样及其退出失败/只读缺证不外推为新性能证据。
- GitHub connector 复核 exact final head/base、单文件范围；CI `verify` SUCCESS（run `41311820376` / job `124863604328`），按 expected head 合并。fetch/fast-forward 后确认 source 是集成祖先，任务 worktree 干净后已移除，分支/PR/报告保留。

## 留给实施契约与 U9

实际fixture完整schema/逐步typed计数、所有字节/几何上界、授权资产、质量/目标机、有效渲染像素与存储profile仍须冻结。性能/延迟/内存/长跑数值未获产品批准，只报告观测与候选差距；已接受的权威只读/单writer等不变量不因数值未决而豁免。锁竞争、故障注入、真实物理、D_recovery保障、视觉和压力测量均未在本卡执行。

U2/U4/U6/U7 的设计依赖现已满足 U8，本卡局部设计接受后，**U9 最终跨卡审查与实现树 ready**；须由未承担 U1–U8 交付的 reviewer 执行。U9 前 U 总轮仍开放；V-HOME 产品总门也不因预算文档合并关闭。
