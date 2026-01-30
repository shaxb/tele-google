"""
Logging Configuration for Tele-Google
Provides easy-to-read, structured logging with Loguru

The logger automatically captures:
    - Module name (e.g., src.crawler, src.bot)
    - Function name where log was called
    - Line number
    - Timestamp
    - Log level

Usage:
    from src.utils.logger import get_logger
    
    log = get_logger(__name__)  # Pass __name__ to get proper module name
    log.info("Starting process")
    log.error("An error occurred", extra={"user_id": 123})
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
        
    Note:
        Call this once at application startup before using get_logger()
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
            "<cyan>{extra[module]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
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
            "{extra[module]}:{function}:{line} | "
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
            "{extra[module]}:{function}:{line} | "
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
    
    # Log initialization with proper module name
    logger.bind(module="logger").info(f"Logger initialized - Level: {log_level}")
    return logger


def get_logger(module_name: str = None):
    """
    Get a logger instance bound to a specific module
    
    Args:
        module_name: Name of the module (use __name__ from calling module)
    
    Returns:
        Logger instance bound to the module name
        
    Example:
        # In src/crawler.py
        from src.utils.logger import get_logger
        
        log = get_logger(__name__)  # Will show 'src.crawler' in logs
        log.info("Crawler started")
        
        # Output: 2026-01-30 12:00:00 | INFO | src.crawler:main:25 | Crawler started
    """
    if module_name:
        # Clean up module name for better readability
        # __main__ -> script name, src.module -> module
        if module_name == "__main__":
            # Try to get the script name from sys.argv
            import sys
            import os
            script_name = os.path.basename(sys.argv[0]).replace('.py', '')
            return logger.bind(module=script_name)
        else:
            return logger.bind(module=module_name)
    
    # Fallback to 'app' if no module name provided
    return logger.bind(module="app")


# Usage examples for documentation
if __name__ == "__main__":
    """Test logging configuration"""
    
    # Setup logger first
    setup_logger(log_level="DEBUG")
    
    # Get logger with module name
    log = get_logger(__name__)
    
    # Test different log levels
    log.debug("This is a debug message - detailed information")
    log.info("This is an info message - normal operation")
    log.warning("This is a warning - something to pay attention to")
    log.error("This is an error - something went wrong")
    
    # Demonstrate proper module naming in a real module
    print("\n" + "="*60)
    print("DEMONSTRATION: How to use in your modules")
    print("="*60)
    print("""
    # In src/crawler.py:
    from src.utils.logger import setup_logger, get_logger
    
    # Setup once at startup
    setup_logger(log_level="INFO")
    
    # Get logger for this module
    log = get_logger(__name__)  # Will show 'src.crawler' in logs
    
    # Use it
    log.info("Crawler started")
    log.error("Connection failed", extra={"channel": "@TestChannel"})
    """)
    
    # Test with extra context
    log.info("Processing message", channel="@TestChannel", msg_id=12345)
    
    # Test exception logging
    try:
        result = 1 / 0
    except Exception as e:
        log.exception("An error occurred while processing")
    
    log.success("✓ Logging test completed!")
    
    # Show log file location
    print("\n" + "="*60)
    print(f"Logs saved to:")
    print(f"  - Main log: logs/app.log")
    print(f"  - Errors:   logs/error.log")
    print("="*60)
