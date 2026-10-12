import os
import secrets
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", DATA_DIR / "storage"))
CERTS_DIR = Path(os.environ.get("CERTS_DIR", BASE_DIR / "certs"))
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "app.db"))

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CERTS_DIR.mkdir(parents=True, exist_ok=True)

# Secret Key for JWT Tokens
SECRET_KEY_FILE = DATA_DIR / ".secret_key"
if not SECRET_KEY_FILE.exists():
    generated_key = secrets.token_urlsafe(64)
    SECRET_KEY_FILE.write_text(generated_key)
    SECRET_KEY = generated_key
else:
    SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY_FILE.read_text().strip())

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))  # 7 days

# Server Network Settings
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8443"))
USE_SSL = os.environ.get("USE_SSL", "true").lower() in ("true", "1", "yes")

SSL_CERT_PATH = Path(os.environ.get("SSL_CERT_PATH", CERTS_DIR / "cert.pem"))
SSL_KEY_PATH = Path(os.environ.get("SSL_KEY_PATH", CERTS_DIR / "key.pem"))

COOKIE_NAME = "session_token"
