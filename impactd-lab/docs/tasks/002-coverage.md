# Task 002: isolated named-test coverage

Objective: identify which named tests previously executed a source line, with
explicit evidence identity and honest limits.

Acceptance criteria (checked by `make check`):
1. The original 40 behavioral checks still pass.
2. `--list` returns 40 unique names; `--test NAME` executes exactly one check.
3. An unknown test exits 2, rather than reporting zero-test success.
4. The mutation demo still confirms weak-pass / strong-fail on the injected defect.
5. Coverage contains all 40 passing named executions.
6. `entry_at_payload_end` reaches the entry guard; `bad_magic` and `null` do not.
7. A query reports observed tests for the entry guard, with no safety guarantee.
8. Changing any recorded source identity causes query rejection, not stale reuse.

The harness bootstrapping change adds these gates. On subsequent tasks, run the
existing gate before editing and extend it only for a concrete new acceptance need.
Do not change the acceptance expectations merely to accommodate a regression.
