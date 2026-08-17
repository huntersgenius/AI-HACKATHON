"""Application errors and the global handlers that shape them into responses.

Routes and services raise `AppError` (or one of its subclasses); nobody builds
an error payload by hand. `register_error_handlers()` converts anything that
escapes a request into the single API envelope for /api/* paths.
"""

from flask import request
from werkzeug.exceptions import HTTPException

from core.responses import fail


class AppError(Exception):
    """Expected, user-visible failure. `message` is Uzbek (shown to users)."""

    code = "app_error"
    status = 400
    message = "Xatolik yuz berdi."

    def __init__(self, message=None, code=None, status=None, details=None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if code:
            self.code = code
        if status:
            self.status = status
        self.details = details


class NotFound(AppError):
    code = "not_found"
    status = 404
    message = "Topilmadi."


class ValidationError(AppError):
    code = "validation_error"
    status = 422
    message = "Ma'lumot noto'g'ri."


class FeatureDisabled(AppError):
    code = "feature_disabled"
    status = 403
    message = "Bu imkoniyat hozircha o'chirilgan."


def _wants_envelope():
    """API paths always answer in the envelope; pages keep HTML errors."""
    path = request.path or ""
    return path.startswith("/api/") or path == "/health"


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def _handle_app_error(exc):
        if _wants_envelope():
            return fail(exc.code, exc.message, status=exc.status,
                        details=exc.details)
        return exc.message, exc.status

    @app.errorhandler(HTTPException)
    def _handle_http_error(exc):
        if _wants_envelope():
            code = (exc.name or "http_error").lower().replace(" ", "_")
            message = _HTTP_MESSAGES_UZ.get(exc.code, "So'rov bajarilmadi.")
            return fail(code, message, status=exc.code or 500)
        return exc

    @app.errorhandler(Exception)
    def _handle_unexpected(exc):
        app.logger.exception("unhandled error: %s", exc)
        if _wants_envelope():
            return fail("internal_error", "Ichki xatolik yuz berdi.", status=500)
        return "Ichki xatolik yuz berdi.", 500


# User-facing text is Uzbek (Latin script).
_HTTP_MESSAGES_UZ = {
    400: "So'rov noto'g'ri.",
    403: "Ruxsat yo'q.",
    404: "Topilmadi.",
    405: "Bu amal qo'llab-quvvatlanmaydi.",
    422: "Ma'lumot noto'g'ri.",
    429: "So'rovlar juda ko'p. Biroz kuting.",
    500: "Ichki xatolik yuz berdi.",
}
