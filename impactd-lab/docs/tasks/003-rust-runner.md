# Task 003: native execution runner with coverage parity

Requirement: move command supervision, isolated workspaces, counter resets,
and named executions into Rust without changing observed line counts.

Acceptance gate: `make rust-check` (mandatory in CI, no Cargo registry dependencies).
- Cargo unit tests exercise JSON escaping and nonzero/timeout child failures.
- Collect baseline Python and independent Rust executions of all 40 checks.
- Compare every positive validator line count for every test, not just totals.
- Validate the Rust report's input identities, successful one-check outputs,
  raw gcov source selection and executable identity.
- Reject altered counters and stale input hashes in disposable report copies.
- A failed new Rust collection must remove the previous successful report.

Boundaries: Rust records raw gcov JSON; Python normalizes and compares it.
This avoids introducing a handwritten JSON parser or dependencies merely to
bootstrap the native runner. It is a staged migration, not complete Python removal.
Timeouts kill and reap the direct child. Descendant process-tree containment,
arbitrary untrusted commands, filesystem/network isolation and output quotas
remain outside this trusted-fixture runner.
