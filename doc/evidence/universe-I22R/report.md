# I22 root Native import correction

Status: **partial**. The final capability probe passed; actual asset import and reload
were not dispatched. The exact source 768b1ac and context 5f2bbe3 were subsequently
published after specific user approval; source remains unmerged. The immutable
published manifest/status capture the earlier pre-approval state; the later local
publication-receipt.json records approval, remote verification and PR disposition.

Approved plan: `doc/design/universe-i22-import-correction-plan.md`, SHA256
`0ebce94464c98becd8297833ab574b698dc9118363f5fedaafd9297761cb6f24`.
Execution root: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import`.
Continuous 1200-second budget starts at the preserved `campaign-start.json`; preparation,
review, failed attempts and final fsync remain in that same clock. Existing I21 failures
and the main checkout are preserved.

## Probe 01

Source `99ea747f3b703a7454e6629e1b9ea4b44bf81013`; exact execution card
`probe-01-card.json`, SHA256 `973d60af9eed1818bd0104b2a15930c0c4a47b8ddf4783b09b9844266e00ddaa`.
Real UE PID 57035, supervising parent 56985, actual wait 255, nonforced, no cleanup,
no owned survivors. Native result SHA256
`6310bee6c44c2f38c6110c9dfa9da1e54d52ecb41d61e959f56a4e15a63e7c67`.

Result: **FAIL**, `transient texture flags/dimensions did not restore`.
The process reached `run_probe` after module activation and the non-None subsystem
guard. This is evidence of progress past the I21 entry failure, not a complete
capability pass. The failing finally wrapper did not retain actual before/after
fields, so the differing field and any preceding exception cannot be recovered
from this process. Preserve that evidence limitation.

Project Content file maps before/after are empty and identical; identity and final pinned-input
checks passed. At phase receipt: elapsed 35.196654458 seconds, run-root 15,728,140 B,
project Content 0 B, isolated DDC 1,988,511 B. Original raw logs and process samples
remain in `p1/` and `supervision-probe-01/` on DevSSD.

## Boundaries

No visible UI, rendering acceptance, worker, Genesis or Universe mutation is in scope.
No engine source changes or C++ builds. Static `a1` preparation was not executed;
its source cohort must not be used for a corrected `p2`. A failed final probe blocks
both import and reload. Native-failing implementation is retained on its task branch.

## Correction and Probe 02

Implementation commit `877696e7ef61a2fbfbc50fb0cd88ba10ceacb644` changes restoration to
compression → sRGB → flip and retains primary traceback plus per-clone actual before,
after and diff. Installed `Texture.cpp:772–778` independently confirms that MASKS and
NORMAL compression force sRGB false. This establishes a concrete restoration-order
defect; p1 itself did not record the differing field. All original strict dimensions,
flags, Engine UObject getters and fixture package hash checks remain in force.
Six targeted CPU checks and independent source review passed.

The exact second/last card `probe-02-card.json` has SHA256
`edfab7084de3a1c74c51a6ae4884c3057c07f13ebd6d0b75496f149973d14f6b`.
Its 818 pins were independently checked before dispatch. Actual UE PID 86365,
parent PID 86354, wait 0, nonforced, no cleanup or surviving owned descendants.
Native result `p2/result.json` SHA256
`1a88df030a7619b34d68ca2210183c1502f336401505333d8bc1301822b38676`
is **PASS**, bound to the exact job, recipe, index and source script hashes.

Actual subsystem, mesh getters/setters and collision/slot restoration worked.
All three transient textures remained 128×128 and restored all checked fields with
empty diffs. Material links, real Alpha disconnect/restore, pipeline overrides,
original Engine fixture getters and package byte checks passed. Both Content file
maps stayed `{}`; UE did create empty Collections/Developers directories. This is
a bounded API capability result, not I20 texture provenance, imported geometry,
rendering, runtime or build acceptance.

## Import NO-GO and final seal

Static `a2` was independently prepared from source 877696e and late-bound to the
actual p2 result SHA. Neither `a1` nor `a2` was executed. New `import-02-card.json`
SHA256 `f2eb47cf8a403e7784cf0456f1becb4248d5a4f73bc5ab32e99cc081202ef6a1`
was generated but never C1-accepted or dispatched. Root had shortened this unused
card to 120 seconds within the approved ≤240 ceiling; only 130.865 seconds remained,
less than 120 + 30 seconds of seal reserve. Root and C agreed **NO-GO** without
further shortening, retrying, resetting the clock or appending to the sealed run.
Reload was skipped. Four Host Content file maps contain no files; there is no
import result, reload directory or `.uasset`.

Final seal SHA256 `89c19c9c6b745f41eed7042064515cbd7d4b176f063408235c2dab5df5c9f144`.
The post-fsync original stdout records **1148.5123171668965 seconds**,
**27,805,158 B** total / **0 B** project Content / **3,977,022 B** isolated DDC.
Process/domain checks passed: no remaining processes, no input errors, and zero
metadata changes/errors in the six declared external domains. This is a limited
declared-domain metadata comparison. The seal exits 2 / partial because no complete
probe→import→reload chain exists; `selected_probe_ok=false` is that chain selector,
not a rejection of p2's independently successful capability result.

The original observation is transcribed with tool provenance in
`post-seal-observation.json`. All subsequent checks read the DevSSD root without
writing to it. Root's first replay checker incorrectly rejected UE's empty Content
directories; `parent-check-01-failure.json` retains the failure and correction.
`check_parent.py` / `parent-replay-02.json` then passed, rehashing the 818 unique used
pins and all 34 I20 originals, confirming 274 sealed files and exactly unchanged
27,805,158 bytes. No UE rerun was involved in that checker correction.

## Disposition and next cycle

A is partial: implementation and bounded capability pass, actual import/reload
unverified. Its branch/worktree is retained and source is not integrated into the
integration or baseline branch. C independently accepts the limited capability
and partial settlement; D3-IMPORT remains unaccepted. Root integrates only scoped
review/context records after inspecting them. The main checkout, historical
build/recovery worktrees, original I20/I21/I22 data and failed attempts are preserved.

A's final status-only commit is `768b1ac4a608bd4a3b6eed39001117e1b8f2692b`.
C's independent commit `e78c1a8d54f87e8653ba791edaac7dacb7ca81ad` was reviewed and
cherry-picked as `7e2846b2b75cb0ea87c11ba76d27ff1222d09030`. All twelve C artifacts
remain byte-identical. The C2 checker reran successfully from the stable integration
tree (`integrated-C2-replay/c2-run-review.json`). The clean review worktree was then
removed without force after dependency checking and byte-identical relocation of its
one historical source-report reference; its branch is retained. A remains retained
and unintegrated. See `worktree-settlement.json`; no other worktree was removed.

Next cycle: prepare and independently review static inputs before the clock;
use a new run root and explicit budget for the exact source 877696e cohort.
Review whether the unchanged engine/source/fixture pins allow reusing the exact
p2 capability evidence, then execute real 5-mesh / 14-texture / 3-material import,
Native metadata and genuine negatives, followed by independent-process reload.
No additional capability framework, source edit or visual claim is justified yet.
Never append execution to this sealed I22 root.
