# Public Preview preparation

Approved scope: preserve Horizon Command and existing README positioning/support; real application captures; 1280x640 social preview; provenance review before an owner-selected code license; v1.20.0 candidate and release only after verification.

- [x] Clone current main, confirm 45f6f0d; inspect CI and portable build.
- [x] Reproduce Windows SQLite handle leak with a failing regression test.
- [ ] Close database connections and validate commit/rollback; run full pytest on Windows and CI.
- [ ] Capture actual DRIVE/PLAN UI; identify any replayed telemetry explicitly.
- [ ] Add English showcase and Russian introduction without removing history.
- [ ] Review upstream licenses, data provenance and redistribution boundaries.
- [ ] Build v1.20.0 with pinned embedded Python; validate PE and hash exact binary.
- [ ] Verify Go tests/race/vet, hygiene, links, startup/shutdown, telemetry and second screen.
- [ ] Publish only after required gates; record outstanding manual checks truthfully.
