# GitHub launch settings

Description and all 12 requested topics were set successfully through the authenticated GitHub API (HTTP 200). They are not pending manual work.

## Social preview

Open the repository **Settings → General → Social preview → Edit → Upload an image**. Upload `docs/images/social-preview.png` (1280×640). `social-preview.svg` is the editable source. This task has not installed the preview in GitHub Settings.

## VirusTotal — deferred by owner

Repository secret `VT_API_KEY` is absent. v1.20.0 was published without a VirusTotal scan; the release and README do not claim a result.

When resuming this work, add the API key in **Settings → Secrets and variables → Actions → New repository secret** as `VT_API_KEY`. Then run **Actions → Release Security → Run workflow** with the published tag. Verify the returned hash matches the published executable before sharing a report.

## Publication complete

[PR #2](https://github.com/atikhobaev/fh6-scenic-navigator/pull/2) is merged. [v1.20.0 Public Preview](https://github.com/atikhobaev/fh6-scenic-navigator/releases/tag/v1.20.0) is published as latest with owner-approved limitations. Public downloads, stable alias and SHA-256 were verified. See `VERIFICATION.md` for evidence and the manual checks that remain unverified.
