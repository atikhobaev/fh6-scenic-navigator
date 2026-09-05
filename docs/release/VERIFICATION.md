# Verification — v1.20.0 Public Preview

Status: **published with owner-approved preview limitations on 2026-09-05**. The owner approved publication with the manual checks below still unverified and explicitly deferred VirusTotal. Work started from main `45f6f0d9955352fc095ec2df8a7aedc5954dd28b`.

## Executed locally on Windows

| Check | Result |
| --- | --- |
| Python full regression | `python -m pytest tests -q`: **165 passed, 3 skipped**, 6 subtests passed; CPython 3.12.14. Skips require a local raw Brio game asset, intentionally absent. CI also runs Python 3.13. |
| JavaScript regression | `node --test tests/*.test.mjs`: **154 passed**. |
| Go unit tests | Go 1.23.2, `go test -count=1 ./...`: passed on Windows. Linux FIFO test is correctly platform-scoped. |
| Go vet | `go vet ./...`: passed on Windows. |
| Go race detector | **Passed in Linux CI** (`go test -race ./...`). Local Windows invocation was attempted but lacks a CGO C compiler. |
| Portable build | `scripts/build_portable_launcher.ps1`: passed; Windows x64 PE32+, GUI subsystem 2, 18,533,888 bytes. Pinned CPython ZIP verified. |
| Embedded runtime integration | `FH6_PORTABLE_SMOKE=1` build gate passed: launcher controller extracted and started bundled CPython with PATH restricted to System32 and an empty isolated LOCALAPPDATA. `ResolvePython` confirmed no system Python available. |
| Exact EXE startup | Candidate EXE started with PATH restricted to System32 and isolated LOCALAPPDATA; process responsive and native window created. Test process was terminated after observation; normal GUI close remains a manual gate. |
| Startup / shutdown | Same integration test reached real HTTP health, served DRIVE and PLAN, received synthetic UDP on **1234**, called controller Stop and successfully rebound HTTP/UDP ports. No orphan server in that controller test. |
| Real browser UI | Headless Edge rendered actual app UI; selected Grand Tour Japan in PLAN, resolved 129 km route, clicked Start Navigation, opened DRIVE with car position and left-turn guidance. Screenshots are not mockups. |
| Telemetry scope | Controlled 323-byte UDP packets from loopback, not an actual FH6 session. This does not prove game configuration or in-game behavior. |
| Images | Visually inspected DRIVE/PLAN and 1280×640 social preview. No personal paths/usernames/private LAN address shown. Loopback 127.0.0.1 is test-local. |
| README links | Both READMEs: all local file links resolve; all **14 unique external URLs returned HTTP 200**. Section anchors and required `Open **DRIVE**` / `Open **PLAN**` wording retained. |
| Repository hygiene | Passed local tracked/new-source checks and CI hygiene. No raw navigation files or EXEs in source; toolchains/release binaries stay under ignored `.worktrees`. |

## MIT follow-up

Owner-approved MIT and LICENSE_SCOPE.md are now included in the embedded payload. A regression test verifies their selection, and a post-build ZIP check verified all license/notices bytes. Full local tests and embedded-runtime smoke were rerun after rebuilding; the exact rebuilt EXE also created a responsive native window without Python on PATH.

## Exact candidate artifact

`FH6_Scenic_Navigator_v1.20.0_Windows_x64.exe`

```text
0fc438f25ad998bb5f9f457e46457168ea59083e3148a2b755f7d2022b4e9278
```

[Published release](https://github.com/atikhobaev/fh6-scenic-navigator/releases/tag/v1.20.0) targets merge commit `0e25d31f95bffefeef6d88aa3411310d767cce74`. Both public EXE downloads (versioned and stable alias) were downloaded and matched the SHA-256 above; the public checksum matched too. Repository secret `VT_API_KEY` is absent; VirusTotal was not run.

[Main CI](https://github.com/atikhobaev/fh6-scenic-navigator/actions/runs/33935065005) passed all five jobs. [Release integrity workflow](https://github.com/atikhobaev/fh6-scenic-navigator/actions/runs/33936170232) succeeded, refreshed the stable alias/checksums and README, and skipped VirusTotal.

This report records the published binary checks. Later documentation-only status updates do not change the release artifact.

## Unverified manual checks / deferred work

- Launch the **exact candidate EXE**, click Start Navigator, verify DRIVE/PLAN and close the native window; confirm no orphan process or occupied port. Controller integration is not equivalent to clicking the built GUI. Native computer-use tools crashed in this environment, so interactive GUI smoke is not claimed.
- Verify FH6 Data Out ON / host IP / **1234** in a real driving session. Replace the explicitly labelled test-telemetry DRIVE capture if an in-game screenshot is preferred.
- Open the launcher LAN URL from another physical phone/tablet/PC. A browser viewport or second local tab is not proof of cross-device LAN access.
- Verify the Windows Firewall prompt/private-network permission flow on the target PC. No firewall rules were modified in this task.
- CI covers Python 3.13 on Linux/Windows, JavaScript, Go tests/race/vet and hygiene; results are linked above. [PR #2](https://github.com/atikhobaev/fh6-scenic-navigator/pull/2) was merged with owner approval.
- Review unresolved data permissions in `../PROVENANCE_REVIEW.md`; original-code MIT licensing has now been approved by the owner and added.
- The owner accepted publication without the manual checks above and reported no way to test another LAN device. These checks remain unverified, not passed. VirusTotal is deferred; no scan result or report URL is claimed.

## First-time visitor UX review

The opening explains HUD-free second-screen navigation, provides one prominent EXE download, and shows a real PLAN screenshot after Why I built it. Quick Start covers launch, Data Out and DRIVE/PLAN. LAN/Firewall instructions, Issues and the coffee link are visible. Russian documentation now has the same user-focused entry and preserves all technical history below. POI accuracy and uncached-map internet requirements are explicit. The download now resolves to published v1.20.0 Public Preview.
