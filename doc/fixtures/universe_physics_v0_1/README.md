# I7 static-only physics inputs

These files describe one dynamic Sphere plus one fixed finite Box support.
They contain no captured Genesis result and no `.gstraj` checkpoint.

- `config.json`: exact proposed configuration; typed binary64 values preserve
  their declared bits, while the intended Metal solver precision is **32**.
- `source_audit.json`: version-specific read-only source identity/definition
  locations, not a record that the API was executed.
- `schema_proposal.json`: explicit authority **v0.2** records/limits awaiting
  reopened G-C approval; never a relaxation of kernel v0.1.
- `record_template.json` / `golden_static.json`: static config-only record and
  fixed byte/hash expectation, authored once. No world root is constructed.
- `static_vectors.json`: synthetic arithmetic examples including realizable
  scaled ties and neighboring binary64 inputs; **not physical measurements**.

Static check, no Genesis import:

```
python3 doc/fixtures/universe_physics_v0_1/validate_static.py --installed-source
```

The checker reads fixed expected inputs and never updates them. It compares
2000-digit Decimal difference/scale/half-even with independent exact Fraction
quotient/remainder rounding. Source hashing only reads installed files.
The config golden is an author self-check; independent G-C0.2 byte recomputation
and physical G-P1 measurements remain separate future evidence.

Actual single bounded static invocation passed: 2 participants, 11 exact-difference rounding vectors, 4 scaled half-even vectors, 9 source files plus package METADATA verified, and all fixture JSON hashes unchanged. No Genesis import or runtime physics occurred. Command/stdout/stderr and checker SHA are retained at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I7-20261101-static-attempt1/`; this is owner static evidence, not G-C0.2 or G-P1 acceptance.
All new solver, checkpoint, contact, coordinate, storage-extension and UE checks
remain planned. Size caps are experimental profile proposals, not approved
product performance or scale thresholds.
