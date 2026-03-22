#!/usr/bin/env python3
import argparse
import json
import mimetypes
import os
import sys
import textwrap
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DOCS_EXPORT = {
    "google-doc": "text/plain",
    "txt": "text/plain",
    "md": "text/markdown",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
SHEETS_EXPORT = {
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}
SLIDES_EXPORT = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
}


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


class GoogleDriveClient:
    def __init__(self, secrets_path: Path, token_path: Path) -> None:
        self.secrets_path = secrets_path
        self.token_path = token_path
        self.secrets = self._load_json(secrets_path, required=True)
        self.tokens = self._load_json(token_path, required=False) or {}

    def _load_json(self, path: Path, required: bool) -> Optional[Dict[str, Any]]:
        if path.exists():
            return json.loads(path.read_text())
        if required:
            raise FileNotFoundError(f"Missing JSON file: {path}")
        return None

    @property
    def client_id(self) -> str:
        return self.secrets["installed"]["client_id"]

    @property
    def client_secret(self) -> str:
        return self.secrets["installed"]["client_secret"]

    @property
    def redirect_uri(self) -> str:
        uris = self.secrets["installed"].get("redirect_uris") or []
        return uris[0] if uris else "http://127.0.0.1"

    def save_tokens(self) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps(self.tokens, indent=2) + "\n")

    def authenticate(self, code: str) -> None:
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        token_data = self._post_form(TOKEN_URL, payload)
        token_data["expires_at"] = int(time.time()) + int(token_data.get("expires_in", 3600))
        self.tokens = token_data
        self.save_tokens()

    def refresh_access_token(self) -> str:
        refresh_token = self.tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(
                f"No refresh_token in {self.token_path}. Run the auth command first."
            )
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        token_data = self._post_form(TOKEN_URL, payload)
        self.tokens["access_token"] = token_data["access_token"]
        self.tokens["expires_in"] = token_data.get("expires_in", 3600)
        self.tokens["expires_at"] = int(time.time()) + int(token_data.get("expires_in", 3600))
        self.save_tokens()
        return self.tokens["access_token"]

    def access_token(self) -> str:
        if self.tokens.get("access_token") and self.tokens.get("expires_at", 0) > time.time() + 60:
            return self.tokens["access_token"]
        return self.refresh_access_token()

    def auth_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.readonly",
            "access_type": "offline",
            "prompt": "consent",
        }
        return AUTH_URL + "?" + urllib.parse.urlencode(params)

    def api_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = DRIVE_API + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.access_token()}")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def api_download(self, url: str) -> bytes:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.access_token()}")
        with urllib.request.urlopen(req) as resp:
            return resp.read()

    def _post_form(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())


def extract_id(value: str) -> str:
    if "/folders/" in value:
        return value.rstrip("/").split("/folders/")[-1].split("?")[0]
    if "/file/d/" in value:
        return value.rstrip("/").split("/file/d/")[-1].split("/")[0]
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme and parsed.netloc:
        query = urllib.parse.parse_qs(parsed.query)
        if "id" in query:
            return query["id"][0]
    return value


def command_auth(args: argparse.Namespace) -> int:
    client = GoogleDriveClient(Path(args.client_secrets), Path(args.token_file))
    if args.print_url:
        print(client.auth_url())
        return 0
    if not args.code:
        eprint("Open this URL in a browser, approve access, then rerun with --code <value>:")
        print(client.auth_url())
        return 0
    client.authenticate(args.code)
    print(f"Saved OAuth tokens to {args.token_file}")
    return 0


def command_whoami(args: argparse.Namespace) -> int:
    client = GoogleDriveClient(Path(args.client_secrets), Path(args.token_file))
    about = client.api_get("/about", {"fields": "user,storageQuota"})
    print(json.dumps(about, indent=2))
    return 0


def list_children(client: GoogleDriveClient, folder_id: str, page_size: int = 100) -> Iterable[Dict[str, Any]]:
    page_token = None
    while True:
        resp = client.api_get(
            "/files",
            {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size, parents, webViewLink)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "pageSize": page_size,
                "orderBy": "folder,name_natural",
                "pageToken": page_token,
            },
        )
        for item in resp.get("files", []):
            yield item
        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def print_tree(client: GoogleDriveClient, folder_id: str, indent: str = "") -> None:
    for item in list_children(client, folder_id):
        icon = "📁" if item["mimeType"] == "application/vnd.google-apps.folder" else "📄"
        print(f"{indent}{icon} {item['name']} [{item['id']}] {item['mimeType']}")
        if item["mimeType"] == "application/vnd.google-apps.folder":
            print_tree(client, item["id"], indent + "  ")


def command_tree(args: argparse.Namespace) -> int:
    client = GoogleDriveClient(Path(args.client_secrets), Path(args.token_file))
    folder_id = extract_id(args.folder)
    print_tree(client, folder_id)
    return 0


def command_ls(args: argparse.Namespace) -> int:
    client = GoogleDriveClient(Path(args.client_secrets), Path(args.token_file))
    folder_id = extract_id(args.folder)
    items = list(list_children(client, folder_id, page_size=args.page_size))
    print(json.dumps(items, indent=2))
    return 0


def get_file(client: GoogleDriveClient, file_id: str) -> Dict[str, Any]:
    return client.api_get(
        f"/files/{file_id}",
        {
            "fields": "id,name,mimeType,modifiedTime,size,parents,webViewLink,exportLinks",
            "supportsAllDrives": "true",
        },
    )


def resolve_export_mime(meta: Dict[str, Any], fmt: str) -> str:
    mime = meta["mimeType"]
    if mime == "application/vnd.google-apps.document":
        lookup = DOCS_EXPORT
    elif mime == "application/vnd.google-apps.spreadsheet":
        lookup = SHEETS_EXPORT
    elif mime == "application/vnd.google-apps.presentation":
        lookup = SLIDES_EXPORT
    else:
        return mime
    if fmt not in lookup:
        raise SystemExit(f"Unsupported format '{fmt}' for {mime}")
    return lookup[fmt]


def default_extension(meta: Dict[str, Any], export_mime: str) -> str:
    if meta["mimeType"].startswith("application/vnd.google-apps"):
        if export_mime == "text/plain":
            return ".txt"
        if export_mime == "text/markdown":
            return ".md"
        ext = mimetypes.guess_extension(export_mime)
        return ext or ".bin"
    guessed = mimetypes.guess_extension(meta["mimeType"])
    return guessed or ""


def command_export(args: argparse.Namespace) -> int:
    client = GoogleDriveClient(Path(args.client_secrets), Path(args.token_file))
    file_id = extract_id(args.file)
    meta = get_file(client, file_id)
    export_mime = resolve_export_mime(meta, args.format)

    if meta["mimeType"].startswith("application/vnd.google-apps"):
        url = f"{DRIVE_API}/files/{file_id}/export?mimeType={urllib.parse.quote(export_mime)}"
    else:
        url = f"{DRIVE_API}/files/{file_id}?alt=media"

    data = client.api_download(url)
    output = Path(args.output) if args.output else Path(meta["name"] + default_extension(meta, export_mime))
    output.write_bytes(data)
    print(str(output))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Authenticate with Google Drive and list or export files using the Drive API."
    )
    parser.add_argument(
        "--client-secrets",
        default=os.environ.get("GOOGLE_DRIVE_CLIENT_SECRETS", str(Path.home() / ".codex/google-drive/client_secret.json")),
        help="OAuth client secret JSON for a Desktop app.",
    )
    parser.add_argument(
        "--token-file",
        default=os.environ.get("GOOGLE_DRIVE_TOKEN_FILE", str(Path.home() / ".codex/google-drive/token.json")),
        help="Where to store OAuth tokens.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="Print the Google consent URL or exchange an auth code for tokens.")
    auth.add_argument("--code", help="Authorization code copied from the browser redirect URL.")
    auth.add_argument("--print-url", action="store_true", help="Only print the consent URL.")
    auth.set_defaults(func=command_auth)

    whoami = sub.add_parser("whoami", help="Show the Drive account tied to the saved token.")
    whoami.set_defaults(func=command_whoami)

    ls = sub.add_parser("ls", help="List files inside a Drive folder as JSON.")
    ls.add_argument("folder", help="Folder ID or full Drive folder URL.")
    ls.add_argument("--page-size", type=int, default=100)
    ls.set_defaults(func=command_ls)

    tree = sub.add_parser("tree", help="Recursively print a Drive folder tree.")
    tree.add_argument("folder", help="Folder ID or full Drive folder URL.")
    tree.set_defaults(func=command_tree)

    export = sub.add_parser("export", help="Download a Drive file or export a Google Doc/Sheet/Slide.")
    export.add_argument("file", help="File ID or supported Drive file URL.")
    export.add_argument(
        "--format",
        default="pdf",
        help=textwrap.dedent(
            """\
            Export format. Google Docs: google-doc/txt/md/pdf/docx.
            Google Sheets: csv/tsv/xlsx/pdf. Google Slides: pdf/pptx/txt.
            Binary files ignore this flag and download the original bytes.
            """
        ).strip(),
    )
    export.add_argument("--output", help="Destination path. Defaults to file name plus extension.")
    export.set_defaults(func=command_export)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        eprint(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
