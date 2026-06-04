import logging
import sys

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configures the standard Python logging configuration.
    
    Includes timestamp, level, logger name, and message.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
