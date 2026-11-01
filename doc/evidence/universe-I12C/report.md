# I12C exact Python interpreter pin

Status: implementation prepared; bounded stdlib checks pending. Base f854281.
Owned runner + this evidence directory; verifier/product/venv are unchanged.

PREP correctly refused general symlink evidence paths, but GS's approved lexical
venv executable is a symlink chain through its bin/python and Homebrew prefix.
Only optional root-card `python_environment_pin` authorizes that exact chain.
Without it original safe_path refusal remains. The launcher receives the original
lexical `python_executable` string, preserving venv behavior; no wrapper, copied
binary, canonical-target substitution or environment mutation is introduced.

Pin exact keys: entry; ordered links[{path,readlink}]; target{path,sha256};
pyvenv_cfg{path,sha256}; site_packages{path,device,inode,uid,mode}. Component walk
checks every leaf/ancestor link against the card **before following it**, rejects
unknown redirects/cycles/hop excess, and interprets '..' after preceding links.
The final target still uses general safe_path/hash/X_OK. cfg must be the actual
lexical venv-root/pyvenv.cfg; its fixed bytes provide version_info/version. Site
must be that same venv/lib/pythonX.Y/site-packages, no symlinks and exact identity.
Unrelated matching cfg/site files cannot satisfy the binding. It is an identity
pin, not recursive environment/package attestation.

Special-pin execution requires unset-or-empty PYTHONHOME/PYTHONPATH and refuses
nonempty values. Root clears/records these launch variables; no general inherited
environment management is added. Other evidence paths remain on unchanged strict
safe_path. runtime_files must use canonical immutable paths; helper suggests only
target/cfg. Mutable Host/plugin artifacts must not be pre-pinned: each session's
postbuild binary evidence is a separate root review task, not relaxed here.

collect_python_pin.py reads metadata/bytes and emits a proposed pin only; it never
executes Python/GS, modifies a card or touches the venv. Root still approves/hashes
the actual card. Synthetic stdlib cases cover exact/original argv, missing/extra/
changed links, parent redirects, cycles, '..', target/cfg/site changes, ambient
variables and unchanged evidence policy. Source ordinary commit precedes checks;
CPU<=120s/raw16MiB, first plus at most one justified targeted retry. No GS/UE/CUA.

## Logged launcher directory bridge (root-approved same leaf)

PREP also exposed a separate exact-source alias: launcher logs its mktemp path
through the approved product Saved symlink. Only the two logged run-dir parsing
sites now use a narrow bridge. Raw parent must equal product's exact
Saved/MacLauncher path or the card's canonical launcher_output_root. Leaf lstat
must be a real directory, not a symlink; resolve followed by unchanged safe_path
must yield a direct child of the canonical root. Source Saved mapping was already
exactly attested by validate_run/product_identity allowed_untracked. Unknown
prefixes, redirected roots or linked leaves are rejected. Launcher and generic
safe_path remain unchanged. Synthetic tests exercise both accepted parents and
rejection even when an unapproved prefix resolves to the same target. No check
had executed before adding this root-reviewed refinement to the first batch.
