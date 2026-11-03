# I16：执行已准备的 Native old3 回放

2026-11-03；用户“执行”授权接续 I15 的唯一第一步；输入 d128053。root 审定范围：只执行四个已冻结精确 selectors、三个原始 proof，经独立审核；不增加产品功能，不开 Metal/worker/solver，不授 G-B2。CUA 当前可用，Metal 不安排是本轮范围决定，不能伪称 CUA 不可用。

依赖：0范围审查 → C最小跳过理由适配/独立PR/CI → P离线核现有构建和新版本输入 → R独立ready review → T唯一Native窗口 → A独立结果复核 → 上下文/commit/push/清理。root 唯一运行owner；N reviewer只读代码/公开原件，不读owner/key，不启动进程。旧失败/卡/准备/源码不覆盖，用户主checkout不碰。

C：排他 capability.py 的 skip_metal 理由允许新增 `approved-native-only-iteration`，显式同schema/inconclusive/未派发；保留旧不可用理由兼容与拒绝未知理由，不放宽私密路径、一次性和其它门。对应CPU定向检查，独立worktree/PR，非owner审查和CI后集成；不改UE源码，因此复核成功构建5a6cca0的所有Native源和实际binary后直接复用。

P/root：独占新公共prepared/card/manifest/output目录，派生prepared保留原product/native/binary/owner/context/inputs/authority/scratch及source pins，更新run_id/tool source/output_root与created_at；新output_root只含本轮输出，旧构建root和authority为显式继承只读依赖（不是新产物字节）。既有validator要求binary与scratch处于output_root，故最窄方案继续引用原I15 output_root并完整计量其约1.47GB，I16独占子目录；不放宽校验。所有原件保留，旧prepared/manifest不覆盖。准备、PR/CI全部在运行clock开始之前完成。

T/root：通过现有typed卡准入后，持续controller/observer依次明确skip Metal→冻结新manifest→一次Native→actual parent wait→seal。沿用900s/2GiB卡上限，Native180s，启动前至少270s完整预留；本轮只一个Native，无自动重试。固定四selectors/四env、原始logs/result/argv/PID/start/parentwait与连续observer均保留。任何失败保留并最窄结算，不因新日期重新跑旧失败来凑pass。

C/A：真实Found4与四精确Success、case_count3、原始status信任链与三个精确输入SHA、typed/static/transition实际strict parser、正常exit0、observer≤2s间隔、前后完整authority map不变与全字节/时间预算。缺原件inconclusive，矛盾fail；独立review只覆盖这三个原始响应。Metal输入/PNG、标准双会话、完整Genesis新solve和G-B2仍开放。下轮只根据实际最小缺口行动。
