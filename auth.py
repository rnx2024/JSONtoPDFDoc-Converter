import hmac

from fastapi import Header

from config import API_KEY


class ApiKeyError(Exception):
    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


async def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if not API_KEY:
        raise ApiKeyError("API_KEY_NOT_CONFIGURED", 503)
    if not hmac.compare_digest(x_api_key, API_KEY):
        raise ApiKeyError("INVALID_API_KEY", 401)
