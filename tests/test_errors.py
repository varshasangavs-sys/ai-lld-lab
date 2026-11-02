import pytest

from ai_lld_lab.core.errors import AppError, NotFoundError, UnauthorizedError, ValidationError


def test_app_error_defaults():
    error = AppError()
    assert error.code == "internal_error"
    assert error.status_code == 500
    assert error.message == "An internal error occurred."


def test_not_found_error_defaults():
    error = NotFoundError()
    assert error.code == "not_found"
    assert error.status_code == 404
    assert error.message == "Resource not found."
    assert isinstance(error, AppError)


def test_not_found_error_custom_message():
    error = NotFoundError("booking 123 not found")
    assert error.message == "booking 123 not found"
    assert error.code == "not_found"


def test_validation_error_defaults():
    error = ValidationError()
    assert error.code == "validation_error"
    assert error.status_code == 400
    assert error.message == "Validation error."
    assert isinstance(error, AppError)


def test_unauthorized_error_defaults():
    error = UnauthorizedError()
    assert error.code == "unauthorized"
    assert error.status_code == 401
    assert error.message == "Unauthorized access."
    assert isinstance(error, AppError)


def test_raising_subclass_is_catchable_as_app_error():
    with pytest.raises(AppError):
        raise NotFoundError("missing")


def test_subclasses_are_exceptions():
    assert issubclass(NotFoundError, Exception)
    assert issubclass(ValidationError, Exception)
    assert issubclass(UnauthorizedError, Exception)
