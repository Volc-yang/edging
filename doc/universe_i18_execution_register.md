# I18：NoTrace Native 封存复测

2026-11-07；in progress；输入a19ea4f，[审定方案](design/universe-i18-native-seal-plan.md)cf76b7a。N独立审查方案与[固定driver](evidence/universe-I18R/driver.py)行为/语法接受，root补齐metadata onerror与frozen异常fail封存后再次接受。仅执行已合入PR123/124修复，不新编译、不改产品工具、不重复CI、不安排Metal/worker/solver。

| 节点 | owner | 当前事实 |
| --- | --- | --- |
| 0 | root，i17_review独立审查 | complete；一次Native180s/global900s/2GiB，oldI17失败不覆，全部权限/ready在clock前 |
| P | root | Native/source5a6cca0三source/三binary实际SHA全部匹配，当前Native源无diff；新prepared/card/manifest与独占I18原件待冻结 |
| R/T | root唯一运行owner | fixed driver先typed输入/driver SHA/六外域metadata/authority/ps，再一次CLI五命令，自动after数据/immutable refs/ps/map/资源seal；尚未dispatch |
| A | i17_review | actual后独立审四Success/三个原case/NoTrace-NoZen/writer稳定/正常退出/完整声明资源，旧formal helper门不放宽；报告路径稍后独占分配 |

输出为原I15完整计量root下I18-20261107-native-seal新目录，DDC run/controller绑定短目录。复用旧owner/context/inputs/native/build，不读key或迁移世界；新run/tool/before_map/created_at变更另存provenance。声明六写域含Zen/UBT两域/DDC两域/Trace，均metadata-only before/after，非全OS I/O审计；若实际缺口仍不通过。用户主checkout、构建/I12B恢复树、旧goal及网站/DNS/API不改。
