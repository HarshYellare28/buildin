"""Contract error shape: {"error": {"code": ..., "message": ...}}."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def body(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


class NotFound(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=404)


class Conflict(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=409)
