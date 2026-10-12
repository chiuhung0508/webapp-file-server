import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

# Use a clean temporary data directory for test isolation
temp_data = tempfile.mkdtemp()
os.environ["DATA_DIR"] = temp_data
os.environ["STORAGE_DIR"] = str(Path(temp_data) / "storage")
os.environ["DB_PATH"] = str(Path(temp_data) / "test.db")
os.environ["USE_SSL"] = "false"

from app.main import app
from app.database import init_db
from certs.generate_cert import ensure_ssl_certificates

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    init_db()
    yield
    shutil.rmtree(temp_data, ignore_errors=True)

@pytest.fixture
def client():
    return TestClient(app)

def test_initial_status_unconfigured(client):
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert data["configured"] is False
    assert data["authenticated"] is False

def test_setup_admin(client):
    res = client.post("/api/auth/setup", json={"username": "superadmin", "password": "securepassword123"})
    assert res.status_code == 200
    assert "superadmin" in res.json()["username"]

    # Setup should now be disabled
    res2 = client.post("/api/auth/setup", json={"username": "superadmin2", "password": "securepassword123"})
    assert res2.status_code == 400

def test_login_and_logout(client):
    # Bad credentials
    bad_res = client.post("/api/auth/login", json={"username": "superadmin", "password": "wrongpassword"})
    assert bad_res.status_code == 401

    # Good credentials
    res = client.post("/api/auth/login", json={"username": "superadmin", "password": "securepassword123"})
    assert res.status_code == 200

    # Status check with cookie
    status_res = client.get("/api/auth/status")
    assert status_res.status_code == 200
    assert status_res.json()["authenticated"] is True
    assert status_res.json()["username"] == "superadmin"

def test_file_operations_and_sandbox(client):
    # Authenticate client
    client.post("/api/auth/login", json={"username": "superadmin", "password": "securepassword123"})

    # 1. Create a subfolder
    mkdir_res = client.post("/api/files/mkdir", json={"parent_path": "", "folder_name": "my_folder"})
    assert mkdir_res.status_code == 200

    # 2. List directory
    list_res = client.get("/api/files/list?path=")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(item["name"] == "my_folder" and item["is_dir"] for item in items)

    # 3. Create and save a text file online
    save_res = client.post("/api/editor/save", json={
        "path": "my_folder/hello.txt",
        "content": "Hello Antigravity File Server!",
        "create_if_missing": True
    })
    assert save_res.status_code == 200

    # 4. Read text file back
    read_res = client.get("/api/editor/read?path=my_folder/hello.txt")
    assert read_res.status_code == 200
    assert read_res.json()["content"] == "Hello Antigravity File Server!"

    # 5. Rename file
    rename_res = client.post("/api/files/rename", json={
        "path": "my_folder/hello.txt",
        "new_name": "greeting.txt"
    })
    assert rename_res.status_code == 200

    # 6. Upload file to specific directory
    upload_res = client.post(
        "/api/transfer/upload",
        data={"target_folder": "my_folder"},
        files={"files": ("sample.md", b"# Markdown Content", "text/markdown")}
    )
    assert upload_res.status_code == 200
    assert len(upload_res.json()["files"]) == 1

    # 7. Download file
    dl_res = client.get("/api/transfer/download?path=my_folder/sample.md")
    assert dl_res.status_code == 200
    assert dl_res.content == b"# Markdown Content"

    # 8. Download directory as zip
    zip_res = client.get("/api/transfer/zip?path=my_folder")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"

    # 9. Path traversal security test: try to break out of sandbox
    traversal_res = client.get("/api/files/list?path=../../../../etc")
    assert traversal_res.status_code == 403

    traversal_editor = client.get("/api/editor/read?path=../../etc/passwd")
    assert traversal_editor.status_code == 403

    # 10. Attempt to delete storage root: must be blocked
    root_del = client.request("DELETE", "/api/files/delete?path=")
    assert root_del.status_code in (400, 403)

    # 11. Delete created files and folder
    del_file = client.request("DELETE", "/api/files/delete?path=my_folder/greeting.txt")
    assert del_file.status_code == 200

    del_folder = client.request("DELETE", "/api/files/delete?path=my_folder")
    assert del_folder.status_code == 200

def test_ssl_certificate_generation():
    temp_cert_dir = Path(temp_data) / "certs"
    cert_path = temp_cert_dir / "test_cert.pem"
    key_path = temp_cert_dir / "test_key.pem"

    ensure_ssl_certificates(cert_path, key_path)
    assert cert_path.exists()
    assert key_path.exists()
    assert b"BEGIN CERTIFICATE" in cert_path.read_bytes()
    assert b"BEGIN RSA PRIVATE KEY" in key_path.read_bytes()
