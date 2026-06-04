import logging
from querymindai_backend.logging_config import setup_logging

def test_setup_logging():
    # Calling setup_logging should not raise errors
    setup_logging()
    
    # Verify root logger level is INFO
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    
    # Test log output does not raise error
    logger = logging.getLogger("test_logger")
    logger.info("Logging configuration test message")
