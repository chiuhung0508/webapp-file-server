#!/usr/bin/env python3
"""
Webapp File Server Launcher
Starts the HTTPS file manager server with automatic SSL certificate management.
"""

import sys
import argparse
import socket
from pathlib import Path
import uvicorn

# Ensure parent directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import HOST, PORT, USE_SSL, SSL_CERT_PATH, SSL_KEY_PATH
from certs.generate_cert import ensure_ssl_certificates

def get_local_ip() -> str:
    """Attempt to detect the primary local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    parser = argparse.ArgumentParser(description="Webapp File Server - HTTPS File Manager")
    parser.add_argument("--host", default=HOST, help=f"Host address to bind (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port number (default: {PORT})")
    parser.add_argument("--ssl", action="store_true", default=USE_SSL, help="Enable HTTPS TLS listener")
    parser.add_argument("--no-ssl", action="store_false", dest="ssl", help="Disable HTTPS listener (HTTP mode)")
    parser.add_argument("--cert", default=str(SSL_CERT_PATH), help="Path to TLS certificate file")
    parser.add_argument("--key", default=str(SSL_KEY_PATH), help="Path to TLS private key file")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload for development")

    args = parser.parse_args()

    ssl_certfile = None
    ssl_keyfile = None

    protocol = "https" if args.ssl else "http"
    local_ip = get_local_ip()

    if args.ssl:
        cert_p = Path(args.cert)
        key_p = Path(args.key)
        ensure_ssl_certificates(cert_p, key_p)
        ssl_certfile = str(cert_p)
        ssl_keyfile = str(key_p)

    print("\n" + "=" * 60)
    print("🚀  WEBAPP FILE SERVER")
    print("=" * 60)
    print(f"  • Status:      Running ({protocol.upper()})")
    print(f"  • Local URL:   {protocol}://localhost:{args.port}")
    if local_ip != "127.0.0.1":
        print(f"  • Network URL: {protocol}://{local_ip}:{args.port}")
    if args.ssl:
        print(f"  • SSL Cert:    {args.cert}")
        print("  • Note:        If using self-signed cert, accept the browser warning once.")
    print("=" * 60 + "\n")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
