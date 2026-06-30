import hashlib
import hmac
import json
import os
import time
import base64
from typing import Any

from app.conf.app_config import app_config


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def _hmac_sha256(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(payload: dict[str, Any]) -> str:
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload["exp"] = int(time.time()) + app_config.auth.jwt_expire_minutes * 60
    payload_enc = _b64encode(json.dumps(payload, ensure_ascii=False).encode())
    signature = _hmac_sha256(f"{header}.{payload_enc}", app_config.auth.jwt_secret)
    return f"{header}.{payload_enc}.{signature}"


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_enc, payload_enc, signature = parts
        expected_sig = _hmac_sha256(f"{header_enc}.{payload_enc}", app_config.auth.jwt_secret)
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(_b64decode(payload_enc))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 密码哈希（含随机 salt）"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=600000)
    return f"pbkdf2:sha256:600000:{salt.hex()}:{dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """验证 PBKDF2 密码哈希（兼容旧版 SHA256）"""
    # 旧版 SHA256 兼容
    if not hashed.startswith("pbkdf2:"):
        return hashed == hashlib.sha256(password.encode()).hexdigest()
    # PBKDF2 验证
    try:
        parts = hashed.split(":")
        if len(parts) < 5 or parts[0] != "pbkdf2" or parts[1] != "sha256":
            return False
        iterations = int(parts[2])
        salt = bytes.fromhex(parts[3])
        expected = parts[4]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=iterations)
        return dk.hex() == expected
    except (ValueError, IndexError):
        return False
