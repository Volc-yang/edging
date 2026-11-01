# E4/E5/I9 统筹复核

2026-11-02，parent=I。以下为已完成的局部接受，不是I根或真实组合门通过。

| 卡 | 最终source / PR / merge | 实际Check及父级复核 |
| --- | --- | --- |
| E5 recovery/proof | `0db45fe21db42927f2a137287c8a22d5f7817c50` / #90 / `33c4fcb09769d433da9dfc17710518e6a4282463` | 155tests（13新增）、5.613s；四proof含64字符request ID约24–32KB；root核对13原件及最终head CI run41331718855/job124923051875 |
| I9 UE严格解析 | `0a905cfff46113bfc2d9dced1d83185d48fcf136` / #86 / `e47065a3319cddf20d6a757b85cbdcbabab10ae4` | UE5.8.3 Build PID14577 exit0/7.07s；真实.app PID14649 StrictV02 Completed Success且exit0/17.15s；67golden/5proof/27适用negative/14exact-F/28strict-text组；最终CI run41331471676/job124922306467 |
| E4 commands/prepare | `1fcae8b06d37623bb072b872b013dd1d189fe29e` / #91 / `a4c86b382df01876a811af771df86af8a2fdb899` | 164tests（19新增）、12.276s/exit0；root核对2321原件及最终head CI run41333022760/job124926920833 |

## 审查结论与接口

E5完整恢复检查全部历史JSON/raw/MAC，Observe选集proof与完整恢复分别计证；Store新增纯读domain_version/deployment_context，不扩HEAD。E4 prepare先鉴权再缓存查询，新prepare严格expiry=expected revision，历史execute/archive维持expiry有效性；已提交retry不重签，retain不调provider，物理候选在最终准入前完整校验。codec仅最小ApprovalSigner协议补充，无存档字节变化。各项已有非作者审查和root准确差异复核。

I9只新增三份新域parser/header/test文件，旧parser/引擎未修改。Mac使用系统CommonCrypto，其他未支持平台fail closed。严格文本修复覆盖大小写、嵌入NUL、Unicode scalar长度/排序及TMap.GetKeys默认折叠；30个writer-only MAC/raw/archive负例不冒称UE覆盖。

## 原始证据与失败保留

原件根 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/`，root已在本交接前独立核对索引及文件：

- E5：`E5-20261102-attempt1/index.json` SHA256 `ac68fd14904b80be0c858c0323b23688f6c6bb2460ecb6eb08d1dcd4b58daef2`。
- E4：`E4-20261102-attempt1-t_29wrmc/raw-index.json` SHA256 `8ffccb1a71720458d4599f0a40588b500bd342a957a74207df3451a8b8d98144`。
- I9S首失败：`I9S-20261102-parser-attempt1/raw-index.json` SHA256 `fd26fac09b1899dc0a688f5b4db341034191b6d3beed54779bbfff4105cd5f95`，96文件/真实exit3。
- I9S最终：`I9S-20261102-parser-attempt2/raw-index.json` SHA256 `75802abe876e6b3ab3622a2fd8d3e9beb6cc5641ca1ee168391e14c481dd69ad`，97文件/真实exit0。

I9的UBA DevSSD链接失败、扩展启动flags下EditorInit fatal、Mac Core SHA stub assert及strict-text TMap折叠失败均保留；未把某单个启动flag断言为已证根因。通过入口使用-NoUBA build和紧凑NullRHI automation命令。E4/E5无额外重跑。

三卡已完成scoped PR合并，source为集成祖先，干净任务worktree已移除、分支和原件保留。I9五个任务生成输出链接及DefaultInput.ini先归档核验再删除，DevSSD目标保留；清理档 `I9-20261102-cleanup-review/`。没有清理用户主工作区。

## Act

接受三项局部交付，I9只证明解析及本机Build/NullRHI。E6独立blob/trust进程门、I0A实际资产、I8真实Genesis、I10/11接线和I12独立真实组合继续执行。G-S1.2/G-P1/G-B1/G-B2不得由这些PR或测试数代替；typed计数及G-Q仍未接受。
