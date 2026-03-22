---
name: google-drive-workspace
description: Authenticate to Google Drive with a desktop OAuth client, browse personal or shared Drive folder trees, and export Google Docs, Google Sheets, Google Slides, PDFs, and other files for local inspection. Use when Codex needs to navigate Google Drive, inspect a shared folder URL or Drive file ID, download/export Docs or Sheets, or work with files stored in Drive instead of the local filesystem.
---

# Google Drive Workspace

Use this skill to work with Google Drive content through the Google Drive API instead of relying on a local browser session.

## Quick start

1. Confirm that `~/.codex/google-drive/client_secret.json` exists, or pass `--client-secrets` with a Desktop-app OAuth client secret file.
2. Run `python google-drive-workspace/scripts/gdrive_workspace.py auth` to print the Google consent URL.
3. Open the URL in any browser where the correct Google account is signed in.
4. After approval, copy the `code=` value from the redirect URL and rerun `auth --code '<value>'`.
5. Run `whoami` to verify the token belongs to the expected Google account.
6. Run `tree` or `ls` on a folder URL or folder ID to inspect Drive contents.
7. Run `export` on any target file URL or file ID to download the file or export a Google-native document.

## Workflow

### 1. Authenticate safely

- Prefer the bundled script over ad hoc OAuth code.
- Keep OAuth scope read-only unless the user explicitly asks for write access.
- Treat saved tokens as secrets. Do not print them into chat.
- Do not assume Codex can reuse a Firefox login session; use API authentication unless the environment provides a dedicated browser automation tool.

### 2. Discover folders and files

- Accept either raw IDs or Drive URLs; the script extracts IDs from common folder and file URL formats.
- Use `tree` for human-readable exploration.
- Use `ls` for structured JSON output that can be filtered by other tools.
- For shared drives or shared folders, leave the script defaults intact because it already requests `supportsAllDrives=true` and `includeItemsFromAllDrives=true`.

### 3. Export or download files

- Google Docs: prefer `--format txt` or `--format md` for text analysis, and `--format pdf` or `--format docx` for layout-sensitive review.
- Google Sheets: prefer `--format csv` for one-sheet tabular analysis, `--format xlsx` when formulas or multiple sheets matter, and `--format pdf` for presentation review.
- PDFs and other non-Google files download with their original bytes.
- If you need a file repeatedly, save it to a deterministic local path with `--output`.

## Commands

```bash
python google-drive-workspace/scripts/gdrive_workspace.py auth
python google-drive-workspace/scripts/gdrive_workspace.py auth --code '<copied-auth-code>'
python google-drive-workspace/scripts/gdrive_workspace.py whoami
python google-drive-workspace/scripts/gdrive_workspace.py tree '<folder-id-or-url>'
python google-drive-workspace/scripts/gdrive_workspace.py ls '<folder-id-or-url>'
python google-drive-workspace/scripts/gdrive_workspace.py export '<file-id-or-url>' --format md --output /tmp/doc.md
```

## Resources

- `scripts/gdrive_workspace.py`: OAuth helper plus `whoami`, `ls`, `tree`, and `export` commands.
- `references/google-drive-api.md`: setup checklist, API reminders, and export guidance.
