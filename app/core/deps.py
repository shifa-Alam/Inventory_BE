from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from jose import jwt, JWTError, ExpiredSignatureError

from app.core.security import SECRET_KEY, ALGORITHM

security = HTTPBearer(auto_error=False)

ADMIN_ROLES = {"system_admin", "admin"}


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(payload: dict = Depends(get_current_user)):
    if payload.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


def get_tenant_id(payload: dict = Depends(get_current_user)) -> int:
    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=403,
            detail="No tenant context. system_admin cannot use tenant-scoped endpoints."
        )
    return int(tenant_id)


def require_system_admin(payload: dict = Depends(get_current_user)):
    if payload.get("role") != "system_admin":
        raise HTTPException(status_code=403, detail="System admin access required")
    return payload
