# I21 import producer

Only the root supervisor runs UE or prepares DevSSD outputs. These scripts do not launch processes. `prepare.py preflight` is read-only; it verifies all 20 pinned I20 inputs, UE version/binary, reviewed script snapshots, user startup absence and installed Content/Python source inventory. Installed plugin inventory is a conservative superset of enabled mounts. It is an identity check of trusted installed code, not a claim that startup does not execute.

```sh
python3 -B scripts/realism_import/prepare.py preflight
python3 -B scripts/realism_import/prepare.py import --attempt 1
```

The second command creates `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import/a1/` exclusively. It snapshots the descriptor/config/recipe/producer and I20 index, then emits and saves `dispatch.json`. Root passes **the exact `argv` list and `env` mapping** to its reviewed supervisor with `shell=False`, `cwd=dispatch.cwd`, real parent wait/descendant checks and the approved global budget. Do not wrap `-script` in shell quotes or concatenate a shell command. `-script` contains only the whitespace-free snapshot script path; it reads the adjacent session `job.json`, bound by independent `I21_IMPORT_JOB_SHA256` in the exact root dispatch environment. This avoids relying on Mac/commandlet parsing of script arguments containing spaces. No inherited I21 environment value is used.

After a positive first import, root runs:

```sh
python3 -B scripts/realism_import/prepare.py reload --attempt 1
```

This exclusively creates the single `reload/` session, selecting the successful Host/Content, with independent UserDir/log/DDC and a new commandlet process. It reads existing packages, performs Native getters and real in-memory negative injections/restoration, and never calls a save path. Both phases verify source files again. Import negatives also run only after packages are saved; their edits are restored without saving.

If the first import fails, preserve it; root may authorize one narrow code fix and `import --attempt 2` under the same continuous clock, using a new Host/Content/Saved/DDC. Maximum two imports at 240s each, one reload at 180s, dispatch→seal total 900s, new root≤4GiB and all Content combined≤512MiB. The root supervisor—not a producer status string—enforces those aggregate limits, observes external write domains and records real exit/normal/quiet status. No third attempt is permitted.

`result.json` format `edgeworld.i21.native-import-result.v0.1` distinguishes actual UObject snapshots from source convention/recipe expectations. It includes source-linked Texture2D import data, real material property input/output channels, real mesh/section/slot/bounds/triangles, project dependencies, installed external content hashes and Content file maps. `status=PASS` requires all local checks; it does not grant parent process/resource gates, Metal/visual quality, normal-direction appearance or runtime authority/HUD gates. Failure raises in UE (commandlet returns nonzero) and exclusively preserves a `FAIL` result where possible.

The source GL normal remains a separately identified file/Texture2D with its GL→DX sampling flip. Materials explicitly select the separately imported DX source with `flip_green_channel=false`. No source glTF is rewritten. Fern uses separate Alpha R→OpacityMask, clip0.5/Masked/TwoSided. Ground imports only textures and its material; ground geometry is deferred.

On CPU, `python3 -B -m unittest tests.test_realism_import -v` checks real source identity and temporary missing/corrupt Alpha, traversal/symlink/exclusive evidence/strict JSON, environment cleanup and untrusted startup rejection. It neither imports `unreal` nor uses a mock, and cannot prove Native APIs succeeded.
