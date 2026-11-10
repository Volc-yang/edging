# I22：纠正Native导入入口

2026-11-10；**partial，运行已封存**。上下文计划d194b4b；source前置为未合并的cd3b26f/PR130。[计划](design/universe-i22-import-correction-plan.md)已独立C0接受，SHA0ebce94464c98becd8297833ab574b698dc9118363f5fedaafd9297761cb6f24。[R报告](evidence/universe-I22R/report.md)记录两次真实UE：p1失败、p2能力检查通过；实际导入/reload未派发，旧I21失败不改，无新goal。

| 节点 | owner / branch / worktree | 状态 |
| --- | --- | --- |
| P0 | root + i20_assets_plan | complete，只读提案已纳入显式模块激活/真实能力和Nanite计数 |
| C0 | i20_review | accepted；[计划门](evidence/universe-I22R/plan-review.json)，准确source/card仍须C1 |
| A | i20_assets_plan；codex/i21-import / .worktrees/i21-import，base cd3b26f | partial；源码aa52727→99ea747→877696e，6CPU/独立C1/p2能力pass；实际导入/reload未验证，未集成/未publish，树保留 |
| R | root / .worktrees/plan-consolidation | partial；p1 wait255/恢复失败，窄修后p2 wait0/真实能力pass；a1/a2仅静态准备，实际余130.865s不足120+30，import NO-GO/reload skipped；1148.512s内封存 |
| C1/C2 | i20_review；codex/i22-review / .worktrees/i22-review，base d194b4b | 独立C1及C2完成，接受有限能力pass与partial证据，拒绝授D3-IMPORT；报告提交/整合/树结算见下文 |

真实证据root：`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import`。p2原结果1a88df03…、准确卡edfab708…、实际UE PID86365/wait0/nonforced/全部后代静默；3临时纹理128×128逐项恢复相等、真实Alpha断开/恢复、原Engine getter与包不变。p1错误未保存字段差异，修复依据为安装源码的compression→sRGB约束，未编造原错字段。原件全部保留；没有第三probe。

[终fsync观察](evidence/universe-I22R/post-seal-observation.json)：1148.512317s，27,805,158B<4GiB，项目Content文件0B<512MiB，DDC3,977,022B；六声明外域0差异/0错误、全部使用输入hash与34份I20原件不变、自有进程静默。原seal exit2/partial；无reload选择链不能授完整导入门。root [复核](evidence/universe-I22R/parent-replay-02.json)通过；首复核误把UE空目录当文件的失败另存，未覆写、未重启UE。

**下一步：**新run-root/新明确预算，先在clock前完成全部静态准备和审查，保留877696e准确源码；审查未变engine/source/fixture pins是否可复用p2准确能力证据，直接进行5mesh/14texture/3material真实导入→Native负例→新进程reload。禁止在已封存I22目录续跑；不再重复扩展工具，不把CPU/能力pass说成真实导入/画质pass。

**本地任务收尾：**A状态报告提交768b1ac（仅文档；实际执行源码仍877696e），未摘取任何导入源。C独立提交e78c1a8已由root审读并等效摘取为7e2846b；12份审查文件逐字节一致，C2 checker在统筹稳定路径再次执行通过（[回放](evidence/universe-I22R/integrated-C2-replay/c2-run-review.json)）。C树干净、历史引用已映射到同SHA稳定副本、无运行依赖后non-force移除；分支保留。A树因部分完成/未集成保留；其他树不动，见[结算](evidence/universe-I22R/worktree-settlement.json)。统筹分支仅包含计划、审查与上下文；主checkout仍d6298e3，原用户未提交修改保留。I22只做本地提交，公开范围见最终publication-manifest，待用户许可。

I21固定清单的公开授权与PR130已完成；自动审批本次拒绝推送新增I22计划d194b4b，认定旧授权未覆盖新增I22内容。已停止所有I22 push/API替代；先完成本地可审交付和真实测试，再请求具体公开范围确认，不影响本地A/C1/R/C2。Native未通过的代码不merge。主checkout用户改动、I15构建/I12B恢复及I20/I21全部原件保留。
