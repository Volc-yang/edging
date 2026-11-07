# I17：Mac Native 完整四项验证

2026-11-07；**in progress**。输入0965d97；[方案](design/universe-i17-native-completion-plan.md)f8d4822、短路径裁决61a05b1，N独立审查接受。仅执行I16已知最小缺口，不改UE源码/physics/C++。root唯一运行owner，旧I16/I15/I12失败保留；本轮还未dispatch。

| 节点 | owner / 固定输入 | 状态 / Check |
| --- | --- | --- |
| 0 | root，i17_review独立审查 | 方案接受，含最多两次有条件纠正/每卡单次、总首dispatch连续900s/2GiB/每次≥270s预留 |
| C | i17_controller；`.worktrees/i17-native-completion` / `codex/i17-native-completion` @f8d4822 | 实现中：无$且源码prefix唯一性、独占97字符DDC、真实wait/写者静默/三原件稳定后引用、seal重核；CPU/非owner审查/PR/CI待完成 |
| P/R | root准备，N ready审查 | 已重核成功构建5a6cca0关键source/Host/plugin/UE binary SHA均匹配，Native源无diff，计划复用；DevSSD新独占I17子目录已创建，已知外部候选写域metadata baseline保存，无内容/私钥读取 |
| T | root | 尚未执行，离线准备/CI/授权在clock前完成；每Native180s，无Metal/worker/solver |
| A | i17_review，root结算 | 等实际Found4/四完整Success/case3/normalwait/完整后代静默/稳定原件/61-file authority map/预算；不以源码或CPU冒称运行通过 |

原output_root仍为`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe`，本轮原件目录`I17-20261107-native-completion/`；DDC同root下run+controller绑定短目录，所有继承/新增root字节一并计量。外部baseline候选为Zen、两个UBT工具/日志域、两个DDC位置；19254+698+55项metadata、errors0，未读取其内容。新run/tool/prepared/card/manifest/provenance待C合入后冻结，product/native保持5a6cca0，原owner/context/inputs/keys不重建不迁移。

## 当前权限与发布事实

本轮sandbox限制写workspace、DevSSD写/ps/联网需正式升级。独占DevSSD mkdir及metadata baseline/ps已分别获自动审批允许。第一次git push升级被拒，理由remote ownership/trust和payload发布授权未建立；没有改用其它渠道绕过。随后GitHub只读连接get_user_login返回Volc-yang/56686828，owner列表确认同用户拥有公开Volc-yang/edging/1291093087、admin/push true且origin匹配；附此新增证据重提同一git push获批准，f8d4822/61a05b1已成功推送。后续权限仍按具体操作审查，不把此次批准当无限授权。

用户主checkout、I12B恢复树与既有构建树保留；旧blocked goal状态不改。未安排网站/DNS/API、crash report发送或UE引擎源码修改。
