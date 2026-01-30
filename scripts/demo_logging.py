"""
Demo: Proper Logger Usage in Different Modules

This demonstrates how logger will show proper module names
when used correctly across different parts of the application.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logger, get_logger


def crawler_example():
    """Simulate logging from crawler module"""
    # In real code, this would be in src/crawler.py
    log = get_logger("src.crawler")
    
    log.info("Crawler started - monitoring channels")
    log.debug("Connected to Telegram API", api_id=12345)
    log.warning("Channel @TestChannel has no new messages")
    

def ai_parser_example():
    """Simulate logging from AI parser module"""
    # In real code, this would be in src/ai_parser.py
    log = get_logger("src.ai_parser")
    
    log.info("Processing message with Router AI")
    log.debug("Detected category", category="electronics", confidence=0.95)
    log.info("Extracted data with Specialist AI")


def bot_example():
    """Simulate logging from bot module"""
    # In real code, this would be in src/bot.py
    log = get_logger("src.bot")
    
    log.info("Bot started - listening for commands")
    log.info("Received search query", user_id=123, query="iPhone 15")
    log.success("Search completed - 5 results found")


def error_example():
    """Demonstrate error logging with traceback"""
    log = get_logger("src.database")
    
    try:
        # Simulate database error
        connection = None
        connection.execute("SELECT * FROM users")  # type: ignore
    except Exception as e:
        log.exception("Database connection failed")


if __name__ == "__main__":
    # Setup logger once at application startup
    setup_logger(log_level="DEBUG")
    
    print("="*60)
    print("DEMONSTRATION: Logger with Proper Module Names")
    print("="*60)
    print("\nNotice how each log shows its source module:\n")
    
    # Simulate different modules logging
    crawler_example()
    print()
    
    ai_parser_example()
    print()
    
    bot_example()
    print()
    
    print("\nError logging with full traceback:\n")
    error_example()
    
    print("\n" + "="*60)
    print("✓ Demo completed!")
    print("="*60)
    print("\nKey points:")
    print("  1. Each module shows its name: src.crawler, src.ai_parser, etc.")
    print("  2. Function name and line number are captured automatically")
    print("  3. Extra context can be added: user_id=123, category='electronics'")
    print("  4. Errors include full traceback with variable inspection")
    print("  5. All logs are saved to logs/app.log with rotation")
    print("  6. Errors are also saved separately to logs/error.log")
