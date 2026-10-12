import os
import socket
import datetime
import ipaddress
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def ensure_ssl_certificates(cert_path: Path, key_path: Path) -> None:
    """Ensure SSL certificates exist, generating a trusted self-signed cert if missing."""
    if cert_path.exists() and key_path.exists():
        print(f"🔒 Using existing SSL certificate: {cert_path}")
        return

    print("🔑 Generating self-signed SSL certificate for HTTPS...")
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Subject name
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Webapp File Server"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    # Discover host IP addresses to include in SAN
    san_list = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv6Address("::1")),
    ]

    try:
        hostname = socket.gethostname()
        san_list.append(x509.DNSName(hostname))
        _, _, ips = socket.gethostbyname_ex(hostname)
        for ip in ips:
            try:
                san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))
            except ValueError:
                pass
    except Exception:
        pass

    # Build certificate
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Write private key
    key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(key_path, "wb") as f:
        f.write(key_bytes)
    os.chmod(key_path, 0o600)

    # Write cert
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    with open(cert_path, "wb") as f:
        f.write(cert_bytes)

    print(f"✅ Self-signed SSL certificate created:")
    print(f"   Certificate: {cert_path}")
    print(f"   Private Key: {key_path}")

if __name__ == "__main__":
    from app.config import SSL_CERT_PATH, SSL_KEY_PATH
    ensure_ssl_certificates(SSL_CERT_PATH, SSL_KEY_PATH)
