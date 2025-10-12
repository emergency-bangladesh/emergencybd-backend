from datetime import timedelta
from typing import Any

import jwt

from ..core.config import config
from ..utils.time import get_utc_time


def encode_token(
    data: dict[str, Any],
    expiry_timedelta: timedelta | None = None,
) -> str:
    now = get_utc_time()
    exp = now + (
        expiry_timedelta or timedelta(seconds=config.jwt_access_token_expiration)
    )

    payload: dict[str, Any] = {
        **data,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(
        payload=payload, key=config.jwt_private_key, algorithm=config.jwt_algorithm
    )


def decode_token(token: str, verify_exp: bool = True) -> dict[str, Any]:
    return jwt.decode(
        jwt=token,
        key=config.jwt_public_key,
        algorithms=[config.jwt_algorithm],
        leeway=30,
        options={"verify_exp": verify_exp},
    )
