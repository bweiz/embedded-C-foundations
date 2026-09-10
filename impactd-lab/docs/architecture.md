# Architecture

`fixture/image.c` implements the byte-format contract in `README.md`.
`fixture/test_image.c` supplies named behavioral checks and two explicit demo probes.
`scripts/demo.py` challenges one assertion with one temporary source mutation.
`scripts/coverage.py` records isolated GCC/gcov line coverage per named test.
`scripts/check.py` supervises the local acceptance gate and writes `build/check.json`.

The coverage collector compiles one instrumented executable in a fresh temporary
directory. Before each named test it removes all `.gcda` counters; after the test
it consumes gcov JSON. Tests execute serially. The temporary directory is unique
to the collector, so parallel independent collectors cannot share counters.

Reports bind observations to SHA-256 identities for the validator, header,
test source, and collector. A query rejects a stale identity before looking up
an observed line. This is conservative file-level freshness, not semantic
invalidation, cross-version line mapping, or proof that unchanged code is safe.

Coverage means `observed_execution`. Requirements remain human-authored.
There is no inferred dependency graph or eBPF sensor yet.

`runner/src/main.rs` independently supervises compilation and named executions,
resets counters in its own disposable workspace, and records raw gcov JSON in
`build/rust-coverage.json`. It uses Rust's standard library plus existing Linux
tools (GCC, gcov, gzip, sha256sum); Cargo has no registry dependencies.
`scripts/parity.py` validates report identity and compares every positive line
count against separate Python executions. It writes `build/parity.json` only
after comparison and negative checks pass. `make rust-check` also exercises
direct-child timeout and failure handling. Raw gcov JSON is normalized by Python;
the Rust runner is not yet a replacement for the Python `explain` query.
