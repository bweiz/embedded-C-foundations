# Impactd engineering harness

## Read before acting
- `README.md`: image contract, run commands, and current limitations.
- `docs/architecture.md`: component boundaries and evidence semantics.
- `docs/tasks/002-coverage.md`: acceptance criteria for the coverage milestone.
- `docs/tasks/003-rust-runner.md`: native runner and parity acceptance criteria.
- `docs/harness.md`: the workflow and how to improve this harness.

## Work loop
1. Identify the requirement and relevant files; state what evidence is needed.
2. Run `make doctor` and `make check` to establish the baseline when available.
3. Make a bounded change. Keep behavioral requirements separate from observations.
4. Run `make check` after the final edit; review the diff and generated summary.
5. Report what changed, commands/results, unverified claims, and the next step.

## Executable gates
- `make check`: fresh C build, boundary suite, mutation demo, coverage and acceptance checks.
- `make sanitize`: additional C memory/undefined-behavior check when C behavior changes.
- `make rust-check`: native runner unit tests, 40-test coverage parity and rejection cases.
  Required for runner changes; use CI to execute it if the local toolchain is unavailable.
- Do not turn a failed prerequisite or skipped check into a pass.
- If the environment blocks a check, retain the failure and disclose any narrower rerun.

## Evidence rules
- A line executed is not proof that its behavior was asserted.
- A missing observed edge is not evidence of no dependency.
- Reports apply only to their recorded source/header/test identities.
- Coverage must be isolated for each named execution; never reuse counters from another test.
- Mutations run on disposable source copies. Never weaken the normal suite for a demo.
- Do not add confidence percentages without a measured calibration method.

## Scope and completion
Use C for the fixture, Rust for native execution, and Python standard-library scripts
for reference collection, JSON normalization and harness checks. Preserve parity during migration.
Generated binaries and evidence belong under ignored `build/`.
Never infer production firmware safety or authenticity from this structural fixture.
