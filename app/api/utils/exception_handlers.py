"""
Global exception handlers for FastAPI application.

Converts all errors into standardized error responses without exposing
framework internals or stack traces.
"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts validation errors into standard error response format.

    Args:
        request (Request): FastAPI request object.
        exc (RequestValidationError): Validation exception from Pydantic.

    Returns:
        JSONResponse: Standardized error response.

    Examples:
        >>> # User sends invalid data:
        >>> POST /wallet/deposit
        >>> {"amount": -100}
        >>> # Response:
        >>> {
        >>>   "error": "VALIDATION_ERROR",
        >>>   "message": "Validation failed",
        >>>   "status_code": 400,
        >>>   "errors": {
        >>>     "amount": ["Input should be greater than 0"]
        >>>   }
        >>> }

    Notes:
        - Maps Pydantic error locations to field names.
        - Never exposes internal validation logic.
    """
    errors = {}

    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body' prefix
        message = error["msg"]

        if field in errors:
            errors[field].append(message)
        else:
            errors[field] = [message]

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Validation failed",
            "status_code": status.HTTP_400_BAD_REQUEST,
            "errors": errors,
        },
    )


def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions (401, 403, 404, etc.).

    Converts HTTPException into standard error response format.

    Args:
        request (Request): FastAPI request object.
        exc (StarletteHTTPException): HTTP exception.

    Returns:
        JSONResponse: Standardized error response.

    Examples:
        >>> # User tries to access protected endpoint without auth:
        >>> GET /wallet/balance
        >>> # Response:
        >>> {
        >>>   "error": "UNAUTHORIZED",
        >>>   "message": "Authentication required",
        >>>   "status_code": 401,
        >>>   "errors": {}
        >>> }

    Notes:
        - Maps status codes to error codes.
        - Never exposes internal exception details.
    """
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
    }

    error_code = error_code_map.get(exc.status_code, "ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "errors": {},
        },
    )


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions (500 errors).

    Converts any unhandled exception into standard error response.

    Args:
        request (Request): FastAPI request object.
        exc (Exception): Any unhandled exception.

    Returns:
        JSONResponse: Standardized error response.

    Examples:
        >>> # Internal server error occurs:
        >>> # Response:
        >>> {
        >>>   "error": "INTERNAL_SERVER_ERROR",
        >>>   "message": "An unexpected error occurred",
        >>>   "status_code": 500,
        >>>   "errors": {}
        >>> }

    Notes:
        - NEVER expose exception details in production.
        - Log full exception for debugging.
        - Return generic message to users.
    """
    # Log the full exception for debugging
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "errors": {},
        },
    )
