# 共通エラー形式 {"error": {code, message, details}} を返すための例外とハンドラ
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    default_message = "リクエストが不正です。"

    def __init__(
            self,
            message: str | None = None,
            details: list[dict[str, Any]] | None = None,
            headers: dict[str, str] | None = None,
    ):
        self.message = message or self.default_message
        self.details = details or []
        self.headers = headers
        super().__init__(self.message)

    def to_response(self) -> JSONResponse:
        return error_response(self.status_code, self.code, self.message, self.details, self.headers)


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"
    default_message = "認証に失敗しました。"

    def __init__(self, message: str | None = None, details=None):
        super().__init__(message, details, headers={"WWW-Authenticate": "Bearer"})


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    default_message = "リソースが見つかりません。"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    default_message = "現在の状態では操作できません。"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    default_message = "入力内容を確認してください。"


class ExternalServiceError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "EXTERNAL_SERVICE_ERROR"
    default_message = "外部サービスとの通信に失敗しました。"


# FastAPI/Starlette標準のHTTPExceptionを変換するときのコード
_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    502: "EXTERNAL_SERVICE_ERROR",
}


def error_response(
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
        headers=headers,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return exc.to_response()


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            # 先頭の "body" / "query" などは除いたフィールド名にする
            "field": ".".join(str(part) for part in error["loc"][1:]),
            "reason": error["type"],
        }
        for error in exc.errors()
    ]
    return error_response(
        ValidationError.status_code,
        ValidationError.code,
        ValidationError.default_message,
        details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "エラーが発生しました。"
    return error_response(exc.status_code, code, message, headers=exc.headers)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
