import hmac

from fastapi import Request

from app import config
from app.security.v1.types import LoginCredentials


class Unauthenticated(Exception):
    pass


def check_login(credentials: LoginCredentials) -> bool:
    return hmac.compare_digest(
        credentials.username, config.settings.username
    ) and hmac.compare_digest(credentials.password, config.settings.password)


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_user(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise Unauthenticated()
    return user
