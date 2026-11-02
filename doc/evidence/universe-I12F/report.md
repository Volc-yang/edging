# I12F installed-editor standalone asset audit

Base: 227a7501516a819a92e27d5f0551dd52839c6fe5. Implementation pending static check.

The installed editor launched with -game has GIsEditor=false. Its verified
observation reached asset auditing, where the editor-only entry rejected it.
Collect now has a default Editor context preserving the prior guard semantics,
plus explicit InstalledEditorStandalone restricted to non-editor game,
non-commandlet, uncooked platform, initialized engine, game thread and valid ID.
Both remain WITH_EDITOR-only; no GEditor dependency or shipping support.
GameMode.VerifyInstalledAssets requests this explicit context after the existing
strict observation verification. Collector body, audit schema, DAG/native/file
checks and resolved/zeroGap/exact manifest comparisons are unchanged.

Native selector: `edgeWorld.UniverseHost.StandaloneAssetAudit` (Editor|Client).
It requires actual standalone game mode, checks default rejection and invalid
world rejection, then runs the actual collector requiring resolved/zero gaps
and a canonical candidate/digest. It reads installed content only; no GS,
transport, actor or authority operations. Native compile/run and actual-session
full collect remain pending root's separately budgeted R12. ProtocolIds also
remains pending native execution despite actual ID/worker progress.

Agent may execute stdlib static checks only <=120s/raw16MiB, first plus at most
one justified targeted rerun, after ordinary source commit. No UE, build, GS,
CUA, environment mutation or authority access is authorized here.
