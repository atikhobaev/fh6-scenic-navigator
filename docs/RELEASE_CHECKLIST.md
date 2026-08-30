# ✅ FH6 Scenic Navigator — Release Checklist

The goal is to make normal releases mostly automatic. Once the one-time VirusTotal secret is configured, each release should need only the normal build/publish action and a quick review of the resulting checks.

## One-time setup

- [ ] Create a VirusTotal account if needed.
- [ ] Copy your VirusTotal API key.
- [ ] In GitHub open **Repository → Settings → Secrets and variables → Actions**.
- [ ] Create repository secret **`VT_API_KEY`** with the VirusTotal API key as its value.
- [ ] Return to **Actions → Release Security → Run workflow** and run it once for `v1.19.2` so the current release gets a VirusTotal report.

Do not paste the VirusTotal key into README, workflow YAML, issues, commits, or this chat. Store it only as a GitHub Actions secret.

## Every release

Before publishing:

- [ ] Python CI is green.
- [ ] JavaScript CI is green.
- [ ] Go test / race / vet checks are green.
- [ ] Repository hygiene check is green.
- [ ] Version and release notes are correct.
- [ ] The portable EXE launches successfully on Windows.

After publishing the GitHub Release:

- [ ] **Release Security** workflow starts automatically.
- [ ] Stable download asset `FH6_Scenic_Navigator_Windows_x64.exe` appears in the release.
- [ ] `FH6_Scenic_Navigator_Windows_x64.exe.sha256` appears beside it.
- [ ] VirusTotal analysis completes.
- [ ] README latest-release block shows the new tag, SHA-256 and VirusTotal counts.
- [ ] If VirusTotal reports a malicious detection, inspect the report before sharing the release.

## Manual verification command

```powershell
Get-FileHash .\FH6_Scenic_Navigator_Windows_x64.exe -Algorithm SHA256
```

The result must match the `.sha256` file attached to the same release.
