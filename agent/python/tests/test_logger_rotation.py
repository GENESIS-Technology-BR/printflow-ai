from logging.handlers import RotatingFileHandler

from core.logger import configure_logger


def test_file_log_has_rotation(tmp_path):
    logger = configure_logger(tmp_path, logger_name="rotation-test")
    handlers = [
        handler for handler in logger.handlers
        if isinstance(handler, RotatingFileHandler)
    ]

    assert len(handlers) == 1
    assert handlers[0].maxBytes == 5 * 1024 * 1024
    assert handlers[0].backupCount == 5
