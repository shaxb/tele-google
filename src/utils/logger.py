"""
Logging Configuration for Tele-Google
Provides easy-to-read, structured logging with Loguru
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "logs/app.log"):
    """
    Configure application-wide logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (default: logs/app.log)
    
    Features:
        - Console output with colors and emoji
        - File output with rotation (10MB per file, keep 7 days)
        - Structured format with timestamp, level, module, message
        - Error logs saved separately
    """
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Console handler - colorful and emoji-based for development
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )
    
    # File handler - detailed logs with rotation
    logger.add(
        log_file,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        level="DEBUG",  # Always log DEBUG to file
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="7 days",  # Keep logs for 7 days
        compression="zip",  # Compress rotated logs
        enqueue=True,  # Thread-safe logging
    )
    
    # Separate error log file
    error_log = log_path.parent / "error.log"
    logger.add(
        str(error_log),
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}\n"
            "{exception}"
        ),
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,  # Include full traceback
        diagnose=True,  # Include variable values in traceback
        enqueue=True,
    )
    
    logger.info(f"Logger initialized - Level: {log_level}")
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__ of the module)
    
    Returns:
        Configured logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


# Usage examples for documentation
if __name__ == "__main__":
    """Test logging configuration"""
    
    # Setup logger
    log = setup_logger(log_level="DEBUG")
    
    # Test different log levels
    log.debug("This is a debug message - detailed information")
    log.info("This is an info message - normal operation")
    log.warning("This is a warning - something to pay attention to")
    log.error("This is an error - something went wrong")
    
    # Test with context
    log.info("Processing message", extra={"channel": "@TestChannel", "msg_id": 12345})
    
    # Test exception logging
    try:
        result = 1 / 0
    except Exception as e:
        log.exception("An error occurred while processing")
    
    log.success("Logging test completed! ✓")
