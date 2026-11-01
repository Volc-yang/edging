# I0 统筹审查（2026-11-01）

准确源 `2aabfcba94e9daee7f243869a19435f8a994bb65`，PR [#77](https://github.com/Volc-yang/edging/pull/77)，目标 `codex/plan-consolidation`。仅七个契约/fixture/oracle文件；旧领域、主工作区和引擎未修改。

## Check 与边界

- Owner初检及一次定向重跑：24条固定记录、3个保留根、27个反例、同tick异revision历史；3.10语法及fixture前后SHA256一致。最终文档补丁不改变已测代码/数据。
- 非作者 `/root/u2_physics_design` 使用独立递归ASCII编码器（不导入oracle、不用json.dumps生成期望），在最终源快照逐字节/摘要复算24条golden及3个历史根、预算/游标/中性算术；exit0，0.033秒。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I0-20261101-independent-attempt1/` 的 `source-2aabfcb-index.json`、`recompute.py`、`recompute-2aabfcb-command.json`、stdout/stderr和result保留。
- 主审只读oracle：24/3/27 PASS，约0.051秒；执行前后fixture哈希一致，3.10 AST语法通过。该检查在owner最后提交前执行；对应positive `8af0e0df64af5034f502daf1d126845fecf1277188726129ed06117d4ce22bfe`、golden `47a6caddf39f9677c37ab1a9adaa02e54a9e0f671f444ecdf41ff3fc70062199`、negative `0fb0aa0fa942e364620f9cd4600e6540753ad756cb309bd40ad0fd4b77aa5ac3`、trust `1ddabb791acba93971c831f9bb8d7699d995672fe8f173a5543830e7b235c275`。最终源身份由独立快照绑定。
- 非作者UE兼容审查确认保留envelope v1、原始JsonLine重验、tick/revision分离、typed finite f64、超时未知提交和显式新域入口边界。
- 最终head CI `verify` success，run 41317152863 / job 124879507512；主审查看普通提交与限定diff。CI不是存储/GPU验证。

## Act

已纠正首事件前链、可重哈希截历史、principal作用域命令去重、外置trust、公共边界校验、EventId复用、3.10语法、identity精确编码、禁止内部hardlink、V未知清除旧snapshot、admission稳定ID，以及retained链之外孤立结果不得进入幂等成功表。

非作者最终无剩余阻断；主统筹接受 **G-C与G-S0契约门pass**，PR #77已按准确head合并，merge `a9506eb7cadce9c5646e89f2c9daa48bf447730e`。v0.1只冻结neutral kernel；I7真实checkpoint/六区schema必须显式版本扩展并重开受影响门，不能把fake候选改名当Genesis。

后续调度：G-C/G-S0接受后可并行实施I1、I2、I7。I2按冻结codec API写实现，但实际import/test依赖I1先合并；禁止复制stub或临时绕过production import。这是构建/Check边，不阻止接口已冻结的独占编码工作；I2验收不早于I1。

无真实锁/故障/恢复/Genesis/UE新域或断电证明；G-S1/G-P0/G-P1/G-B0/B1/B2保持planned。
