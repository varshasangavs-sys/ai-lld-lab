class AppError(Exception):
    code = "internal_error"
    status_code = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "An internal error occurred."
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Resource not found."
        super().__init__(self.message)


class ValidationError(AppError):
    code = "validation_error"
    status_code = 400

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Validation error."
        super().__init__(self.message)


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "Unauthorized access."
        super().__init__(self.message)


class UpstreamError(AppError):
    code = "upstream_error"
    status_code = 502

    def __init__(self, message: str | None = None) -> None:
        self.message = message or "An upstream service failed."
        super().__init__(self.message)
