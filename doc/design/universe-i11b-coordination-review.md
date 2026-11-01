# I11B 统筹验收与 I12 交接

## Plan / Do

I11B 独立交付 [PR100](https://github.com/Volc-yang/edging/pull/100)，final
`1d9f42f285c552216c3fb06cf991cfbf5f76f440`；root 审查准确四路径差异，
仅 GameMode h/cpp、ProtocolTest.cpp 与任务报告。运行 C++ source `ac9e430`，
运行 HEAD `6c16b55`；后续 final 仅报告更新，root 核对实际源码 SHA 不变。
首次已验证动态体提供一次相机 LookAt，历史和重连保留视角；共用产品安全
public-pins 读取和真实安装资产图比较。legacy 默认及引擎源码未改。

## Check

root 与非作者 u9 分别复核原始证据，未重新启动运行：

- 原件目录 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I11B-20261102-live-attempt3-persistent/`，
  89 文件 / 1,153,660B；逐项 length/SHA256 全部一致，index SHA256
  `1d3f8cede679ca4ba6de9e66905e3571af8536741b76eae3b034380cbebd3963`。
- authority90 / scratch6 全量 before/after 完全一致。u9 另核对当前实物的
  hash/mode/UID/inode/nlink/mtime；未读 owner 内容或私钥。
- 重组原始五次往返，仅 status、observe current(2,4)、history(0,1)、
  initial(0,0)、status。独立 pins 与 fresh binding 重验三 proof 通过；
  三 candidate canonical/digest 与九项实际资产 audit 精确匹配。
- NoUBA build PID38365 exit0/2.837s；UE PID38419 LiveReadOnly Success、
  实际 exit0/16.475s；worker38508 actual return0、normal EOF、reaped、
  trace_complete，无 operational_failure。三 PID 均已不存在，非以消失推定退出。
- 新卡实际19.498s/90s、无重试。旧 compile/stale-input 失败原件继续保留，
  u9 另核对旧18/39原件 hash。持久输入修复没有重置权威世界。
- final CI verify success：run41344717942 / job124961972946，head 精确匹配。

## Act / 准确边界

有限 **G-B1 接受**。PR100 已合入集成 branch，merge
`36d88ec7ea8e0ccd262a7781ffd7f42ec914d354`。这是真实 existing worker 的
NullRHI 只读入口与几何定位门，不是 Metal 图像、交互、写实或 I12 G-B2 门。
测试直接调用共享 transport/parser/资产与相机数学 helper，未覆盖真实 StartPlay
交互链；相机仅有执行断言，没有独立保存完整变换数值。两项须由 I12 补实机证据。

I12 owner 继续独占 verifier/runner/证据路径。当前 RUNNER 卡只允许 mock/CPU；
root 预审发现 product 全 untracked 拒绝与所需输出映射冲突，要求准确卡内
allowlist/readlink/hash/provenance，tracked 修改和未知 untracked 仍拒绝。
工具分支基线旧，实际产品必须选已集成 PR97/100 的准确 tree，不能运行旧 launcher。

Mac fresh CUA 仍明确报告 locked；既有手动解锁问题 pending。不开启可见会话，
不绕过锁屏，不将等待计成通过。完整 I0–I12 树继续进行中；下一步为审查
runner 及其负例检查、准确 head CI，再发带持久输入/输出映射/聚合预算的 R12 卡。
I11B 清理 owner 已获仅归档生成物和解除精确链接授权；root 确认干净、祖先及
间接部署依赖后才非 force 移除，DevSSD 目标、分支与原件保留。
