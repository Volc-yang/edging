# G2-AUTHORITY finite integration probe

Input: `doc/fixtures/abstract_seed_genesis_v1.md` at base `48cf26d`; macOS Metal, `genesis-world 1.4.3`, `.venv-genesis/bin/python`. Raw files are under `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/AuthorityProbes/run-b2WglA/`. They remain local to this machine; this Git file is an index.

Each phase used a fresh state directory and the four-request JSONL fixture. The same directory was restarted for `status` and historical `observe(1)`, then a matching command retry, conflicting command payload and stale revision were sent. Both first and restart processes exited 0. The four initial responses were `ok:true` for each phase. `influence_mm` was `-7` for `shaoyang` and `-35` for `taiyang`. Restart `observe(1)` was equal to its first response. Retry returned the same domain result; conflict and stale revision returned `command_id_conflict` and `revision_conflict`. The manifest SHA256 was identical immediately before and after the latter three requests.

| Phase | Initial responses SHA256 | Restart responses SHA256 | Retry/negative responses SHA256 | Final manifest SHA256 |
| --- | --- | --- | --- | --- |
| shaoyang | `485238e71abbcf6b818437e0f226b8022b4c2b91791fcbfa22827de3f4329c2f` | `3029b40e6a4d141d0d26118928048fc9d41b5219575262544ea7c07c61b7a9e7` | `b913a59b9995011c585cd33aa7396ca1663838e1f0c56f0fbd33f9d3f78ad78d` | `eb514215b0603b24145b7786aacc63c6454b298b5713dd5779aa81d54eef73ad` |
| taiyang | `8e42b91fd0936630a99cf4082bddfe6883caa62ca13c82c3a5f2ffa6fbf0876e` | `2752a5e88de6f4547748ebd6774331c9f3092769d15afc716ce951ec5b313190` | `12fe5184b087ae3a6e8c36c3a9d422d9d76cadd507500ed40938787ecfd5411e` | `b4122c8f5837cf98db30f51d58cd86ff07506784d92da80a06a6e395178c7e78` |

The first `status` shares a window with creation of the initial manifest. This probe does not assign that write to `status`. The test result covers only one tick and the listed error paths; the full G3 UE↔worker↔Genesis run, performance, multi-tick recovery and product rules remain open.
