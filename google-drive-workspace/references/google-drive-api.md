# Google Drive API quick reference

Use this reference when the task needs exact API behavior or export format reminders.

## Required setup

1. Create a Google Cloud project.
2. Enable the **Google Drive API**.
3. Configure the Google Auth Platform branding and consent screen. For personal Gmail accounts, use **External** because **Internal** is only available for Google Workspace organizations.
4. While the app is in **Testing**, add the intended Google account as a **test user** under Audience.
5. Create an **OAuth client ID** for a **Desktop app** and download the JSON credentials file.
6. Place that file at `~/.codex/google-drive/client_secret.json`, or pass a custom path with `--client-secrets`.
7. Set `GDRIVE_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/google-drive-workspace"`.
8. If `~/.codex/google-drive/token.json` already exists, run `python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" whoami` first and reuse the existing token when it succeeds.
9. Run `python3 "$GDRIVE_SKILL_DIR/scripts/gdrive_workspace.py" auth --print-url` only when the token is missing, revoked, or tied to the wrong Google account. Open the URL in a browser, grant read-only Drive access, and rerun with `--code` using the code from the redirect URL.

## Important constraints

- Do not rely on an already logged-in Firefox session. Codex cannot safely or consistently reuse your interactive browser profile from a separate execution environment.
- Prefer `https://www.googleapis.com/auth/drive.readonly` unless the task truly requires write access.
- Shared-drive access requires `supportsAllDrives=true` and `includeItemsFromAllDrives=true` on list or get requests.
- Folder listing query pattern: `'<folder_id>' in parents and trashed = false`.
- Reuse `token.json` across future agents. Do not repeat browser auth when `whoami` succeeds.
- The access token is short-lived; the script refreshes it automatically when the saved `refresh_token` is still valid.
- If `whoami` or another API call fails because the token can no longer be refreshed, rerun `auth --print-url`, complete browser consent, and rerun `auth --code '<copied-auth-code>'` to write a fresh `token.json`.

## Common auth failures

- `access blocked` or a consent-screen error while the app is in Testing: add the Google account as a test user in Google Cloud Console.
- A redirect to `http://localhost/...` that fails to load after approval: this is expected. Copy the `code=` value from the browser address bar.
- A valid `client_id` pasted into chat without the JSON file on disk: this is not enough. The script needs the downloaded Desktop app OAuth JSON file.
- If the app remains in **Testing**, Google may require periodic re-auth because refresh tokens can expire for testing apps.

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
