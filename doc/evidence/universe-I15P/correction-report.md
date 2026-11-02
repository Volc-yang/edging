# I15 P correction：RHI 直接依赖与保留失败的准备记录

Root 在准确产品 `e51dcf8a48a34cef04ed3863e5628d83c29e13fc` 执行官方 CPU 构建，实际父 wait=6、32.628994s。原件 `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe/prep/build-{console.log,raw.json}` 保留。日志明确 Host 链接 `_GDynamicRHI` undefined；新 getter 使用其符号，Host private dependencies 缺 `RHI`。按 root 限定授权，只增加发布版 Host 的 RHI 模块直接依赖；不改 UE 源码，不运行构建或 UE。

Root 已创建原 `preparation.json`，product SHA 固定失败构建源。本纠正不覆盖原件：freeze 允许 root 显式选择**同 prep 目录**的 `preparation-corrected-<40位product_source_sha>.json`。新记录必须是原记录仅修改 `product_source_sha`、实际当前 `helper_ref`，以及新增 `previous_preparation_ref`、`build_failure_ref`。两 provenance ref 必须绑定固定原准备和同目录真实非零 CPU build receipt；保留世界、owner、inputs、map、links、runtime/Python/key metadata 等所有其他字段逐项相同。仅允许一次纠正，不允许把通过构建伪作旧失败。成功 freeze 仍核对全部 Native 文件与指定 git commit 的逐字节 SHA，以及真实 build wait、实际二进制、RPATH、源/metadata/authority 不变。

CLI 新增 `--preparation-ref /.../prep/preparation-corrected-<sha>.json`，默认仍为原准备路径。helper 不自动生成纠正记录，不重试准备或构建；显式 root 保存新记录后，使用其独立 SHA freeze。prepared 仍精确36字段，provenance 保存在其 preparation_ref 所引用的纠正记录。

实际 Check：13/13 新 probe/prepare CPU synthetic 检查 pass，其中纠正路径测试验证原件保持、protected metadata 不变、filename/source 一致、helper 精确字节、父 provenance 和旧失败的非零退出；`git diff --check` pass。原 43 checks 记录仍保留；本纠正没有实际运行官方 build、Native/UE/Genesis/UI。RHI 修复需由 root 在剩余 CPU 卡预算内实际重构建验证，不能凭本报告宣称链接通过。
