# Verification — v1.20.0 Public Preview candidate

Status: **not published; release gates remain open**. Work started from main `45f6f0d9955352fc095ec2df8a7aedc5954dd28b`.

## Executed locally on Windows

| Check | Result |
| --- | --- |
| Python full regression | `python -m pytest tests -q`: **164 passed, 3 skipped**, 3 subtests passed; CPython 3.12.14. Skips require a local raw Brio game asset, intentionally absent. CI also runs Python 3.13. |
| JavaScript regression | `node --test tests/*.test.mjs`: **154 passed**. |
| Go unit tests | Go 1.23.2, `go test -count=1 ./...`: passed on Windows. Linux FIFO test is correctly platform-scoped. |
| Go vet | `go vet ./...`: passed on Windows. |
| Go race detector | **Passed in Linux CI** (`go test -race ./...`). Local Windows invocation was attempted but lacks a CGO C compiler. |
| Portable build | `scripts/build_portable_launcher.ps1`: passed; Windows x64 PE32+, GUI subsystem 2, 18,531,840 bytes. Pinned CPython ZIP verified. |
| Embedded runtime integration | `FH6_PORTABLE_SMOKE=1` build gate passed: launcher controller extracted and started bundled CPython with PATH restricted to System32 and an empty isolated LOCALAPPDATA. `ResolvePython` confirmed no system Python available. |
| Exact EXE startup | Candidate EXE started with PATH restricted to System32 and isolated LOCALAPPDATA; process responsive and native window created. Test process was terminated after observation; normal GUI close remains a manual gate. |
| Startup / shutdown | Same integration test reached real HTTP health, served DRIVE and PLAN, received synthetic UDP on **1234**, called controller Stop and successfully rebound HTTP/UDP ports. No orphan server in that controller test. |
| Real browser UI | Headless Edge rendered actual app UI; selected Grand Tour Japan in PLAN, resolved 129 km route, clicked Start Navigation, opened DRIVE with car position and left-turn guidance. Screenshots are not mockups. |
| Telemetry scope | Controlled 323-byte UDP packets from loopback, not an actual FH6 session. This does not prove game configuration or in-game behavior. |
| Images | Visually inspected DRIVE/PLAN and 1280×640 social preview. No personal paths/usernames/private LAN address shown. Loopback 127.0.0.1 is test-local. |
| README links | Both READMEs: all local file links resolve; all **14 unique external URLs returned HTTP 200**. Section anchors and required `Open **DRIVE**` / `Open **PLAN**` wording retained. |
| Repository hygiene | Passed local tracked/new-source checks and CI hygiene. No raw navigation files or EXEs in source; toolchains/release binaries stay under ignored `.worktrees`. |

## Exact candidate artifact

`FH6_Scenic_Navigator_v1.20.0_Windows_x64.exe`

```text
6a38a85221f2a2266a98745ca942692c175ff6528993c1fe2d22c7791b8917e1
```

[Draft release](https://github.com/atikhobaev/fh6-scenic-navigator/releases/tag/untagged-708230b6a8c76bbe7b3f) contains both EXEs and checksums. Both uploaded EXEs were downloaded back through the authenticated API and matched this hash. GitHub repository secret `VT_API_KEY` was checked through the API and is absent.

The local stable alias `FH6_Scenic_Navigator_Windows_x64.exe` has the same hash. Both have adjacent `.sha256` files. Rebuilding after a payload/code change requires rehashing and rerunning checks. This is a candidate hash, not a claim about a published latest release.

## Required manual / remaining gates

- Launch the **exact candidate EXE**, click Start Navigator, verify DRIVE/PLAN and close the native window; confirm no orphan process or occupied port. Controller integration is not equivalent to clicking the built GUI. Native computer-use tools crashed in this environment, so interactive GUI smoke is not claimed.
- Verify FH6 Data Out ON / host IP / **1234** in a real driving session. Replace the explicitly labelled test-telemetry DRIVE capture if an in-game screenshot is preferred.
- Open the launcher LAN URL from another physical phone/tablet/PC. A browser viewport or second local tab is not proof of cross-device LAN access.
- Verify the Windows Firewall prompt/private-network permission flow on the target PC. No firewall rules were modified in this task.
- CI completed successfully: Python 3.13 on Linux and Windows, JavaScript, Go tests/race/vet and repository hygiene. [Run 33933917131](https://github.com/atikhobaev/fh6-scenic-navigator/actions/runs/33933917131) verifies source commit `704abcf7c7dc68ab27cd25d5350a5ce14b03c816`.
- Review unresolved data permissions in `../PROVENANCE_REVIEW.md`; approve original-code licensing separately.
- Publish only after those gates; then verify downloaded published EXE hash and alias. Submit that exact published binary to VirusTotal. No VT scan or report URL is claimed for this candidate.

## First-time visitor UX review

The opening explains HUD-free second-screen navigation, provides one prominent EXE download, and shows a real PLAN screenshot after Why I built it. Quick Start covers launch, Data Out and DRIVE/PLAN. LAN/Firewall instructions, Issues and the coffee link are visible. Russian documentation now has the same user-focused entry and preserves all technical history below. POI accuracy and uncached-map internet requirements are explicit. Download currently remains the existing published v1.19.2 until the new candidate clears release gates.
