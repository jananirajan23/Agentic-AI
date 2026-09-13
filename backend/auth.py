"""
Password hashing and JWT auth for the faculty login/dashboard.

Password hashing deliberately uses only the standard library (PBKDF2-HMAC
via `hashlib`, 260k iterations, a random salt per password) rather than
adding a bcrypt/argon2 dependency — it's a NIST-approved KDF, has zero
extra install/build surface, and is more than adequate for a
single-institution faculty tool. JWTs are signed HS256 via PyJWT.
"""

import datetime
import hashlib
import hmac
import secrets

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import config
import models_db as models
from database import get_db

PBKDF2_ITERATIONS = 260_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, hex_digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), hex_digest)


def create_access_token(user: models.User) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {"sub": user.id, "email": user.email, "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.get(models.User, user_id)
    if user is None:
        raise credentials_exception
    return user
