import json
import logging
import sys

import pytest

from ai_lld_lab.core.logging import JSONFormatter, configure_logging, get_request_id, set_request_id


@pytest.fixture(autouse=True)
def _reset_root_logger():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)
    set_request_id("-")


def test_request_id_default_is_placeholder():
    assert get_request_id() == "-"


def test_set_and_get_request_id():
    set_request_id("req-abc")
    assert get_request_id() == "req-abc"


def test_json_formatter_outputs_valid_json():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    formatted = JSONFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["message"] == "hello"
    assert "request_id" in payload


def test_json_formatter_includes_exc_info():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=True,
        )
        record.exc_info = sys.exc_info()

    formatted = JSONFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["message"] == "failed"
    assert "ValueError: boom" in payload["exc_info"]


def test_configure_logging_writes_json_line_to_stdout(capsys):
    configure_logging("INFO")
    set_request_id("req-123")

    logging.getLogger("test_logger").info("hello from test")

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert payload["message"] == "hello from test"
    assert payload["request_id"] == "req-123"
    assert payload["level"] == "INFO"
