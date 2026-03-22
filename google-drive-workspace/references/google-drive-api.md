# Google Drive API quick reference

Use this reference when the task needs exact API behavior or export format reminders.

## Required setup

1. Create a Google Cloud project.
2. Enable the **Google Drive API**.
3. Configure an **OAuth client ID** for a Desktop app.
4. Download the OAuth client secrets JSON and place it at `~/.codex/google-drive/client_secret.json`, or pass a custom path with `--client-secrets`.
5. Set `GDRIVE_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/google-drive-workspace"`.
6. Run `python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" auth --print-url` to print the consent URL, open it in a browser, grant read-only Drive access, and rerun with `--code` using the code from the redirect URL.

## Important constraints

- Do not rely on an already logged-in Firefox session. Codex cannot safely or consistently reuse your interactive browser profile from a separate execution environment.
- Prefer `https://www.googleapis.com/auth/drive.readonly` unless the task truly requires write access.
- Shared-drive access requires `supportsAllDrives=true` and `includeItemsFromAllDrives=true` on list or get requests.
- Folder listing query pattern: `'<folder_id>' in parents and trashed = false`.

## MIME types and export choices

### Native Google file types

- Folder: `application/vnd.google-apps.folder`
- Google Doc: `application/vnd.google-apps.document`
- Google Sheet: `application/vnd.google-apps.spreadsheet`
- Google Slide: `application/vnd.google-apps.presentation`

### Recommended exports

- Google Docs → `text/plain`, `text/markdown`, `application/pdf`, or DOCX.
- Google Sheets → `text/csv`, `text/tab-separated-values`, XLSX, or PDF.
- Google Slides → PDF, PPTX, or plain text.
- PDFs and other binary files → download with `alt=media`.

## Useful commands

```bash
GDRIVE_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/google-drive-workspace"
python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" auth --print-url
python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" auth --code '<copied-auth-code>'
python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" whoami
python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" tree 'https://drive.google.com/drive/u/0/folders/163sVFTefcAOznEYacdLulGfmQgL3rYUu'
python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" export '<file-id-or-url>' --format pdf
```

## Workflow for the user's company folder

1. Authenticate with the Drive account that has access to the shared folder.
2. Run `tree` on `163sVFTefcAOznEYacdLulGfmQgL3rYUu` to discover the folder layout.
3. Use `ls` for JSON output when another tool needs structured results.
4. Use `export` on target Docs, Sheets, or PDFs after locating the relevant file ID.
