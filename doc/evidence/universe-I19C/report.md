# I19C — Metal cache and writer-completion repair

Status: complete implementation, pending independent review/CI/integration and live runtime checks. Parent `I19/C`, base `7eb3e9f`, worktree `.worktrees/i19-metal-controller`, branch `codex/i19-metal-controller`, target `codex/plan-consolidation`.

Metal now uses both fixed NoTrace arguments and an exclusive short FileSystem DDC graph. It calls the unchanged cache helper with the fixed `controller_output/metal` binding; Native keeps its existing `controller_output` binding, arguments, selectors and result schema. The directories are distinct, run-bound and exclusively created; an existing Metal cache refuses dispatch.

After actual parent wait, Metal requires three fresh quiet observer samples with stable console/log fingerprints and a complete recursive trace-directory inventory, spanning at least 0.75s. The barrier is bounded by the unchanged Metal/global limits and a 20s seal interval. It verifies actual writable isolated-cache log output, rejects Zen launch and parses the frozen trace originals. Failed barriers do not publish mutable trace refs or claim normal completion; exit0 alone or forced cleanup cannot satisfy normal completion.

Frozen logs, all trace files and directory names/identities are rechecked before manifest freeze, before Native dispatch, and on both sides of the final observer join. Adding, removing, changing or replacing a trace file invalidates the freeze. The retained Native-only skip-Metal path is unaffected.

## Checks actually run

- `python3 -B -m unittest discover -s tests -p 'test_universe_*completion.py' -v`: **24 passed / 9.723s**, comprising 13 new Metal CPU checks and 11 retained Native regressions. Four cases use actual synthetic Python parent/child processes and passive process snapshots; no UE, worker or solver runs.
- `python3 -B -m unittest discover -s tests -p 'test_universe_iteration_i15_cli.py' -v`: **6 passed / 0.002s**.
- `git diff --check`: pass.

Initial sandboxed legacy run had 8 pass / 3 environment errors because `/bin/ps` returned EPERM before synthetic dispatch. The explicitly authorized CPU-only run with process observation then passed all 24; the initial missing observation is not claimed as a product failure or a successful run.

Directed negative checks cover cache conflict, wrong/missing actual DDC, Zen launch, stale/pre-wait/nonquiet samples, delayed child log/trace write, trace additions/removals/changes/replacements/symlinks, incomplete wait/barrier, nonzero/forced exits, mutation before Native and mutation during final observer shutdown.

No C++/parser/worker/world changes, budget changes, UI calls, private owner/key reads, new build or live Metal/PNG/input acceptance. Resource accounting still covers the declared domains only; runtime evidence and independent review remain required. Root owns execution and integration. Preserve I18 exact3 and prior failures.
