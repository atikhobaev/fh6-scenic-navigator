# 🛡️ Security & Release Verification

FH6 Scenic Navigator is distributed as a portable Windows executable. The repository therefore treats release integrity as a first-class part of the publishing process.

## Automated release checks

For each GitHub Release, `.github/workflows/release-security.yml` is designed to:

1. identify the release's versioned `.exe` asset;
2. create a stable `FH6_Scenic_Navigator_Windows_x64.exe` alias;
3. calculate SHA-256;
4. publish `FH6_Scenic_Navigator_Windows_x64.exe.sha256` beside the download;
5. submit the executable to VirusTotal when `VT_API_KEY` is configured;
6. wait for the VirusTotal analysis to complete;
7. publish a small VirusTotal summary asset;
8. update the release-verification block in `README.md`.

The workflow also supports a manual run so an existing release can be rechecked without rebuilding it.

## VirusTotal is a signal, not a guarantee

VirusTotal aggregates results from many security engines. A clean report is useful evidence, but it is **not a guarantee** that software is safe. Likewise, a detection can be a false positive, especially for unsigned or uncommon portable executables.

The README reports the observed engine counts rather than making an absolute "safe" claim. If VirusTotal reports one or more engines as `malicious`, the release-security workflow exits with a failure after recording the result so it cannot be overlooked.

## Manual SHA-256 verification

On Windows PowerShell:

```powershell
Get-FileHash .\FH6_Scenic_Navigator_Windows_x64.exe -Algorithm SHA256
```

Compare the printed hash with the `.sha256` asset attached to the same GitHub Release.

## Source hygiene checks

The regular CI workflow rejects source commits containing:

- raw FH6 navigation files: `.nav`, `.owt`, `.oww`, `.owbs`;
- committed `.exe` binaries.

Release executables belong in GitHub Releases, not in the source tree.

## Reporting a security concern

Because this repository is private, open a private repository issue describing the concern and include:

- affected version/tag;
- SHA-256 of the file you tested;
- relevant VirusTotal or antivirus report;
- reproduction details if the issue is behavioral.
