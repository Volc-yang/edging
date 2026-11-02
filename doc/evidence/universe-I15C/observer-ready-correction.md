# I15 C observer readiness correction

Root's first controller attempt failed before UE dispatch: the real observer callback indexed `phase['pid']` on an explicit skipped Metal phase. Its transcript, first sample and abort remain preserved; no UE window was consumed. This defect had escaped CPU coverage because earlier observer and skip tests were separate.

The callback now ignores skipped or not-yet-PID phases and iterates a stable phase snapshot. `start_observer()` waits at most two seconds for its first completed actual ps sample, then returns its raw reference. Observer errors or missing first samples remain explicit admission failures; there is no fallback sample or automatic restart. This removes the pipelined no-sample race without requiring an external sleep.

Base `5a6cca0c36b7dc89997d1a0bf35f154346f86e99`; branch `codex/i15-controller-observer-ready`. Only controller readiness, CPU regressions and this report changed. Root separately authorizes any pre-dispatch recovery, retains the failed attempt and accounts cumulative resource time from the original dispatch; this correction grants no retry or fresh resource budget.

Actual Check: `python3 -m unittest discover -s doc/evidence/universe-I15C -p 'test_*.py' -v` — 15 CPU tests passed. New regression uses the actual ps observer, immediate skip and actual strict Native-manifest freeze against N's synthetic public trace fixture, then observes a further real callback across skipped/pre-PID phase metadata; no startup sleep is used. Another regression preserves an actual first-sample exception as failure. No UE, worker, Genesis, build or DevSSD mutation ran. Root still owns real runtime acceptance.
