import hmac

from fastapi import Request

from app import config


def check_login(username: str, password: str) -> bool:
    return hmac.compare_digest(username, config.USERNAME) and hmac.compare_digest(
        password, config.PASSWORD
    )


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_user(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise Unauthenticated()
    return user


class Unauthenticated(Exception):
    pass
