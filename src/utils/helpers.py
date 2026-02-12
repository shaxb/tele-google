"""
Helper Utilities for Tele-Google
Common utility functions used across the application
"""


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Original text
        max_length: Maximum length
        suffix: Suffix to add when truncated (default: "...")
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
