# Public Preview preparation

Approved scope: preserve Horizon Command and existing README positioning/support; real application captures; 1280x640 social preview; provenance review before an owner-selected code license; v1.20.0 candidate and release only after verification.

- [x] Clone current main, confirm 45f6f0d; inspect CI and portable build.
- [x] Reproduce Windows SQLite handle leak with a failing regression test.
- [x] Close database connections and validate commit/rollback; run full pytest on Windows and CI.
- [x] Capture actual DRIVE/PLAN UI; identify any replayed telemetry explicitly.
- [x] Add English showcase and Russian introduction without removing history.
- [x] Review upstream licenses, data provenance and redistribution boundaries.
- [x] Build v1.20.0 with pinned embedded Python; validate PE and hash exact binary.
- [x] Verify Go tests/race/vet, hygiene, links, embedded controller startup/shutdown and synthetic UDP 1234.
- [ ] Verify native GUI Start/Close flow, real FH6, physical second screen and Windows Firewall.
- [x] Prepare draft release/PR and document remaining manual gates.
- [ ] Publish only after required gates.
