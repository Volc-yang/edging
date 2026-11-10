# I20B presentation contract fixtures

These are **synthetic contract-only inputs**, never UE assets or an authorized runtime profile. Payload strings are created as `.fixture` files in an isolated temporary directory; no product, authority, original CC0 source or user `.venv` is changed.

- `profile.schema.json`: exact local presentation profile structure. Native import metadata is either unresolved/null, or a proposal carrying actual evidence references; a claimed observed status never authenticates itself.
- `view-binding.schema.json`: authoritative source identity plus separate realistic presentation mode, profile SHA, independently pinned renderer build and view generation.
- `positive-profile.json`: explicitly synthetic, unimported fern/rock/ground declaration; it cannot demonstrate correct UE geometry or PBR.
- `expected-synthetic.json`: independent test expectations, including initial rectangular forest limits and observed source triple.
- `synthetic-payloads.json`: literal temp-file bytes; the synthetic license note is not a real third-party grant.

Run the bounded CPU checks using the pinned evidence-directory requirements in an isolated environment:

```bash
python3 -m venv /private/tmp/edgeworld-i20b-contract-env
/private/tmp/edgeworld-i20b-contract-env/bin/python -m pip --isolated install -r doc/evidence/universe-I20B/requirements.lock.txt
/private/tmp/edgeworld-i20b-contract-env/bin/python -B doc/evidence/universe-I20B/check_contract.py
```

JSONSchema checks structure; the harness separately hashes actual temporary files, checks path/symlink safety, dependency closure/cycles, source roles, material recipe omissions, exact integer transforms and independent cross-time/world/profile/renderer bindings. Hashing a license reference proves bytes only. Matching declared slots does not prove native slots, sampler wiring, alpha coverage or HUD atomicity. All UE build, rendering, authority-preservation and UI-transaction gates remain unexecuted by this fixture.

The source contract is intentionally not the authority's `basicshapes-proxy.v0.2` record schema. No fields or versions in the old verified observation are rewritten. See [design and D3/D4 cards](../../design/universe-realistic-presentation-profile.md).
