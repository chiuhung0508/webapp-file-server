# Webapp File Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-teal.svg)](https://fastapi.tiangolo.com/)
[![HTTPS](https://img.shields.io/badge/Protocol-HTTPS%20Native-success.svg)](https://en.wikipedia.org/wiki/HTTPS)

A secure, responsive, mobile and desktop-friendly file upload, download, and management web server running over HTTPS.

---

## ✨ Features

- 🔒 **End-to-End HTTPS / TLS**:
  - Automatically generates self-signed TLS certificates on first startup for immediate local / LAN encrypted communication.
  - Supports custom SSL certificates or reverse proxy setups (Caddy / Nginx / Cloudflare).
- 🛡️ **Secure First-Run Onboarding & Authentication**:
  - Built-in setup wizard on initial launch to create the master administrator account.
  - Passwords secured with industry-standard `bcrypt` hashing.
  - Session tokens stored in secure, `HttpOnly`, `SameSite=Lax` cookies.
- 📁 **Sandboxed File Management**:
  - All user files reside strictly inside `data/storage/`.
  - Enforces strict path normalization and sandbox bounds (`is_relative_to()`).
  - Guards against path traversal attacks (`../`), null-bytes, and protects OS system directories (`/etc`, `/root`, `/usr`, etc.) and server source code from deletion or exposure.
- 💻 **In-Browser Text & Code Editor**:
  - Integrated **CodeMirror** editor with syntax highlighting for `.txt`, `.md`, `.py`, `.js`, `.json`, `.yaml`, `.html`, `.css`, `.sh`, `.sql`, etc.
  - Line numbers, keyboard shortcut save (`Ctrl+S` / `Cmd+S`), mobile touch-friendly controls, and unsaved changes confirmation.
- 📱 **Mobile & Desktop Responsive Design**:
  - Modern, dark-themed UI built with Tailwind CSS.
  - Desktop drag-and-drop file upload overlay.
  - Mobile touch action buttons and responsive list/grid view toggle.
- 🚀 **High Performance Transfers**:
  - Multi-file chunked streaming upload (supports large files without memory spikes).
  - Single-click streaming file downloads.
  - On-the-fly `.zip` directory compression and download.
  - In-place file and folder renaming and deletion.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `pip`

### 2. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/chiuhung0508/webapp-file-server.git
cd webapp-file-server

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Launching the Server

Run the server launcher:

```bash
python3 run.py
```

By default, the server binds to `0.0.0.0:8443` over HTTPS. On first boot, it will automatically generate `certs/cert.pem` and `certs/key.pem`.

Access the web interface in your browser:
- **Local**: `https://localhost:8443`
- **LAN / Mobile**: `https://<server-ip>:8443`

> [!NOTE]
> When accessing the server using the auto-generated self-signed certificate, your browser will display a security warning (e.g. *Your connection is not private* or *Self-signed certificate*). This is expected—click **Advanced** -> **Proceed to localhost (unsafe)** to establish the encrypted HTTPS connection.

---

## ⚙️ Configuration & CLI Options

The server can be customized using CLI arguments or environment variables:

```bash
# Custom port and host
python3 run.py --host 0.0.0.0 --port 443

# Run without HTTPS (if behind a reverse proxy like Caddy or Nginx)
python3 run.py --no-ssl --port 8080

# Use custom trusted SSL certificates
python3 run.py --cert /path/to/fullchain.pem --key /path/to/privkey.pem
```

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8443` | Port number to listen on |
| `HOST` | `0.0.0.0` | Network interface to bind |
| `USE_SSL` | `true` | Enable built-in TLS listener |
| `STORAGE_DIR` | `./data/storage` | Path to the sandboxed storage directory |
| `DB_PATH` | `./data/app.db` | Path to SQLite database file |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days) | JWT session cookie lifetime in minutes |

---

## 📂 Project Structure

```
webapp-file-server/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment configuration & paths
│   ├── database.py            # SQLite database for administrator account
│   ├── security.py            # bcrypt hashing, JWT cookie session, sandbox guard
│   ├── main.py                # FastAPI app, security headers, routing
│   ├── routers/
│   │   ├── auth.py            # /api/auth (setup wizard, login, logout, status)
│   │   ├── files.py           # /api/files (list, mkdir, rename, delete)
│   │   ├── editor.py          # /api/editor (read, save text files)
│   │   └── transfer.py        # /api/transfer (streaming upload, download, zip)
│   ├── static/
│   │   ├── css/app.css        # Custom styles & CodeMirror themes
│   │   └── js/app.js          # File manager SPA controller & editor logic
│   └── templates/
│       ├── index.html         # Main responsive file manager interface
│       ├── login.html         # Login page
│       └── setup.html         # First-run admin onboarding wizard
├── certs/
│   └── generate_cert.py       # Automated self-signed TLS cert generator
├── requirements.txt           # Python package dependencies
├── run.py                     # CLI launcher script
└── README.md
```

---

## 🔒 Security Design

1. **Chrooted Storage Isolation**:
   All user file interactions pass through `get_safe_path(rel_path)`. Any attempt to access paths outside `data/storage` triggers an immediate `HTTP 403 Forbidden`. The storage root itself is protected from deletion or renaming.
2. **First-Run Onboarding Protection**:
   The setup wizard (`/setup`) is permanently disabled once the initial administrator account is registered.
3. **Password Protection**:
   Passwords are never stored in plaintext and are salted and hashed using `bcrypt`.
4. **Cookie Security**:
   Session tokens are transmitted using `HttpOnly`, `SameSite=Lax`, and `Secure` attributes, preventing JavaScript extraction and cross-site tampering.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).