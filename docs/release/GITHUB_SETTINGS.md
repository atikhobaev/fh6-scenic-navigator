# GitHub launch settings

Description and all 12 requested topics were set successfully through the authenticated GitHub API (HTTP 200). They are not pending manual work.

## Social preview

Open the repository **Settings → General → Social preview → Edit → Upload an image**. Upload `docs/images/social-preview.png` (1280×640). `social-preview.svg` is the editable source. This task has not installed the preview in GitHub Settings.

## VirusTotal

Repository secret `VT_API_KEY` was checked through the API and is absent.

Open **Settings → Secrets and variables → Actions → New repository secret**. Name: `VT_API_KEY`. Paste the API key only into the GitHub secret value, never into an issue, README or chat.

After the release passes every manual gate and is published, open **Actions → Release Security → Run workflow**, choose the default branch and enter the actual published tag. Confirm the workflow processes the final published EXE, and check that its returned hash matches the release checksum before sharing the report. There is no VirusTotal URL for the new candidate yet.

## Publish the prepared draft

Review `VERIFICATION.md`; finish all outstanding gates first. Merge the PR, verify the release target commit includes the reviewed payload, and rebuild if any payload/code input changed. Replace draft assets and hashes after any rebuild. Only then publish the draft as latest and run Release Security. Keep the current README release block on v1.19.2 until the replacement is actually published.
