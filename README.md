# RECORD

RECORD is a lightweight document library for HTML, text, SQL, Word, and Excel files. It can run in two modes:

- **Local mode:** open `record.html` directly in Chrome or Edge and grant access to category folders through the File System Access API.
- **Remote mode:** run `server.py` and access the same interface over HTTP/HTTPS. Files are then managed through an authenticated Flask API on the Raspberry Pi.

The deployed instance is available at:

`https://report.shitikanthay.co.in`

## Features

- Separate HTML, Text, SQL, Word, and Excel tabs
- Multiple-file uploads with category-specific extension validation
- Nested folders and subfolders inside every file category
- Folder-grouped browsing with a selectable upload destination
- Duplicate-file confirmation before replacement
- File listing, content indexing, relevance search, and per-file filtering
- In-browser viewing for HTML, text, Word, CSV, and modern Excel files
- Editing for HTML and text-based records
- Confirmed deletion flow
- Light, dark, and high-contrast themes
- Persistent server-side file storage
- HTTP Basic authentication for the remote application and API

## Storage layout

Files are stored directly in category directories under the repository:

| Tab | Directory | Accepted extensions |
| --- | --- | --- |
| HTML | `html/` | `.html`, `.htm` |
| Text | `text/` | `.txt`, `.md`, `.markdown`, `.log`, `.csv`, `.json`, `.text`, `.sql`, `.xml`, `.yml`, `.yaml` |
| SQL | `sql/` | `.sql` |
| Word | `word/` | `.docx` |
| Excel | `excel/` | `.xlsx`, `.xlsm`, `.csv` |

Uploaded files survive application restarts and Raspberry Pi reboots because they are written to these directories, not held in browser or process memory.

Folders can be nested to any practical depth. Select an existing folder in the **Upload folder** control, use **New folder** to create a child folder, and then upload files into it. Searching continues across every folder in the active file-type tab. Results retain their relative folder path, so files with the same basename can exist in different folders.

## Local mode

Open `record.html` directly in Chrome or Edge. For each tab, select the corresponding directory when prompted. Folder handles are remembered in IndexedDB, although the browser may ask for permission again after a restart.

The optional `reveal-helper.py` process lets the **Go** button reveal a file in the operating system's file manager:

```bash
python3 reveal-helper.py
```

## Remote mode

### Requirements

- Python 3.11 or newer
- Flask and Werkzeug
- Write permission to the category directories

Create a private `.env` file. It is intentionally ignored by Git:

```dotenv
RECORD_USERNAME=choose-a-username
RECORD_PASSWORD=choose-a-strong-password
RECORD_PORT=8090
```

Start the server manually:

```bash
set -a
source .env
set +a
python3 server.py
```

The server listens on `127.0.0.1:8090` by default. All pages and API endpoints require HTTP Basic authentication. The maximum request size is 50 MB.

### systemd service

The included `record.service` runs the application as user `pi` and restarts it after failures:

```bash
sudo install -m 0644 record.service /etc/systemd/system/record.service
sudo systemctl daemon-reload
sudo systemctl enable --now record.service
```

Useful commands:

```bash
sudo systemctl status record.service
sudo systemctl restart record.service
sudo journalctl -u record.service -n 100 --no-pager
```

### Cloudflare Tunnel

`cloudflared-config.yml` documents the deployed ingress routes. The RECORD route forwards the public hostname to the loopback-only application:

```yaml
- hostname: report.shitikanthay.co.in
  service: http://localhost:8090
```

The active tunnel on this Raspberry Pi reads `/home/pi/.cloudflared/config.yml`. After changing ingress configuration, validate and restart it:

```bash
cloudflared --config /home/pi/.cloudflared/config.yml tunnel ingress validate
sudo systemctl restart cloudflared.service
```

## HTTP API

All endpoints require the same HTTP Basic credentials as the web interface.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/files/<category>` | List files in a category |
| `GET` | `/api/files/<category>/<name>` | View or download a file |
| `POST` | `/api/files/<category>` | Upload one or more multipart `files` |
| `PUT` | `/api/files/<category>/<name>` | Update an HTML, text, or SQL file |
| `DELETE` | `/api/files/<category>/<name>` | Delete a file |
| `POST` | `/api/folders/<category>` | Create a folder or nested folder path |

File endpoints accept nested relative paths. The folder endpoint expects JSON such as `{"path":"projects/2026"}`. Upload requests may include a multipart `folder` field selecting the destination. The server independently validates category names, traversal-safe paths, filename safety, and extensions. Client-side `accept` filters are only a convenience and are not trusted for enforcement.

## Security notes

- Never commit `.env`; it contains the live credentials.
- The server binds only to loopback and is exposed through Cloudflare Tunnel.
- Uploaded filenames must be plain filenames without directory traversal characters.
- Only approved extensions can be uploaded to each category.
- Back up the category directories because deleting a record removes it from disk.
- Change credentials by editing `.env` and restarting `record.service`.

## Troubleshooting

- **Authentication prompt repeats:** verify the username/password in `.env`, then restart `record.service`.
- **502 from Cloudflare:** confirm `record.service` is active and listening on port 8090.
- **Public hostname returns 404:** confirm its ingress rule appears before the final `http_status:404` rule.
- **Uploads fail:** check file extension, request size, directory permissions, and service logs.
- **Files disappear after switching tabs:** ensure the file was uploaded to the matching category and accepted extension.
- **Local folder controls are unavailable:** use Chrome or Edge and open `record.html` from disk.

## Key files

- `record.html` — complete browser interface and local/remote mode logic
- `server.py` — authenticated remote API and static page server
- `record.service` — systemd unit for automatic startup
- `cloudflared-config.yml` — Cloudflare Tunnel ingress configuration reference
- `reveal-helper.py` — optional local file-manager integration
