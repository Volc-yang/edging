# I12D bounded session namespace

Status: implementation prepared; targeted stdlib checks pending. Base01b16d1.
Owned runner + this evidence directory; no product/launcher/layout changes.

Optional root-card session_namespace defaults to literal sessions. It may only be
sessions or sessions-[a-z0-9-]+, ASCII and total length<=64. One helper returns a
strict safe_path direct child of storage; both initialize completion lookup and
new session output use that same root. Existing revisit still requires matching
card SHA, accepted source and normal initialize completion. Missing completion
in a new namespace cannot borrow one from sessions/another namespace.

No free paths/external roots/role changes or overwrites. Supervisor consumes the
already prepared output unchanged. Full tree_bytes(storage) accounting stays
unchanged, so old caches/failed sessions/originals remain counted; no copy, deletion
or budget reset. A new namespace requires a new approved card/hash, not hidden retry.
Runtime source layout/rpath fixes are I12-owner work, not part of this leaf.

Five synthetic prepare-only cases exercise default compatibility, explicit retry
without overwriting or omitting old bytes, invalid names/symlink refusal, cross-
namespace completion rejection, and unchanged card/source/normal requirements.
The existing metadata fixture is reused; subprocess.Popen is forbidden in all
cases. No actual authority, venv, UE, GS or CUA is touched. Commit source before
CPU<=120s/raw16MiB first + at most one justified targeted retry; no full suite.
