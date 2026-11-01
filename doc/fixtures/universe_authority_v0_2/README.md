# I0E authority v0.2 fixed static vectors

Contract: ../../contracts/universe_authority_v0_2.md. These files are static
review inputs, not a runtime world, key provisioning tool or Genesis checkpoint.

- schema.json: exact keys/refs/types, physical parameters, caps and trust framing.
- positive.json / golden.json: 67 topological records, literal canonical bytes
  and hashes; four retained roots (0,0),(0,1),(1,2),(1,3).
- proof_vectors.json: five selected Observe JSONL envelopes, independent from
  full archive validation; explicit outstanding query and trusted HEAD inputs.
- negative.json: 57 fixed rejected inputs with exact error codes. Some semantic
  variants were rehashed/re-signed during authoring using the public key so the
  intended semantic check is reached. No update/generator mode is shipped.
- fixture_key.json / trust_context.json: PUBLIC test key00…1f and synthetic
  externally injected owner context. Runtime must reject those key bytes for
  every world/root. The inert root string is never created.
- synthetic_blobs.json: two explicit non-Genesis text payloads (82 bytes total).
  They cannot be relabeled `.gstraj` or used as restore evidence.
- source_manifest.json: read-only installed-package Python source audit (264
  relative paths), not an import/solver/default execution result.
- inventory.json: current S30, H4, D6, declared A4, actual A unknown; per-kind
  JSON bytes, geometry and retained/supplied/orphan raw counts.

Run only the bounded stdlib checker:
`python3 scripts/validate_universe_authority_v0_2_fixtures.py`
It has no production imports, solver initialization, writer or golden repair.
PASS_STATIC_CONTRACT_ONLY is a self-check, not independent G-C0.2 acceptance,
production API validation, G-P1, G-B0, UE/Metal or storage recovery evidence.
Independent reviewers must recompute fixed goldens with their own implementation.
