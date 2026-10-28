import base64
import hashlib
import hmac
import os


def _material(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()


def _stream(secret: str, nonce: bytes, size: int) -> bytes:
    key = _material(secret)
    output = b""
    counter = 0
    while len(output) < size:
        output += hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return output[:size]


def seal(secret: str, text: str) -> str:
    nonce = os.urandom(16)
    raw = text.encode()
    cipher = bytes(left ^ right for left, right in zip(raw, _stream(secret, nonce, len(raw)), strict=True))
    mac = hmac.new(_material(secret), nonce + cipher, hashlib.sha256).digest()
    return base64.b64encode(nonce + mac + cipher).decode()


def open_secret(secret: str, token: str) -> str:
    blob = base64.b64decode(token)
    nonce, mac, cipher = blob[:16], blob[16:48], blob[48:]
    expect = hmac.new(_material(secret), nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expect):
        raise ValueError("Sır açılamadı")
    raw = bytes(left ^ right for left, right in zip(cipher, _stream(secret, nonce, len(cipher)), strict=True))
    return raw.decode()
