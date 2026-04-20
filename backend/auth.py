# ================================================
# JWT Authentication
# ================================================
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import USERS

SECRET_KEY  = "policyguard-secret-2024-local-llm"
ALGORITHM   = "HS256"
EXPIRE_MINS = 480   # 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def create_token(username: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINS)
    return jwt.encode(
        {"sub": username, "role": role, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM
    )


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role     = payload.get("role")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def authenticate(username: str, password: str):
    user = USERS.get(username)
    if user and user["password"] == password:
        return user["role"]
    return None
