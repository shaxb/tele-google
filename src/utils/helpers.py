"""
Helper Utilities for Tele-Google
Common utility functions used across the application
"""
from datetime import datetime
from typing import Optional
import re


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a string to be used as a filename
    
    Args:
        filename: Original filename
        max_length: Maximum length of filename (default: 255)
        
    Returns:
        Sanitized filename safe for all operating systems
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Limit length
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        name = name[:max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name
    
    return filename


def format_price(price: Optional[float], currency: str = "USD") -> str:
    """
    Format price for display
    
    Args:
        price: Price value
        currency: Currency code (USD, UZS, etc.)
        
    Returns:
        Formatted price string (e.g., "$750", "5,000,000 сум")
    """
    if price is None:
        return "Price not specified"
    
    # Format based on currency
    if currency == "USD":
        return f"${price:,.0f}"
    elif currency == "UZS":
        return f"{price:,.0f} сум"
    else:
        return f"{price:,.0f} {currency}"


def format_timestamp(timestamp: datetime, format_type: str = "short") -> str:
    """
    Format timestamp for display
    
    Args:
        timestamp: Datetime object
        format_type: "short", "long", or "relative"
        
    Returns:
        Formatted timestamp string
    """
    if format_type == "short":
        return timestamp.strftime("%Y-%m-%d %H:%M")
    elif format_type == "long":
        return timestamp.strftime("%B %d, %Y at %H:%M:%S")
    elif format_type == "relative":
        # Calculate relative time
        now = datetime.now()
        delta = now - timestamp
        
        if delta.days > 365:
            return f"{delta.days // 365} year(s) ago"
        elif delta.days > 30:
            return f"{delta.days // 30} month(s) ago"
        elif delta.days > 0:
            return f"{delta.days} day(s) ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} hour(s) ago"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} minute(s) ago"
        else:
            return "Just now"
    else:
        return timestamp.isoformat()


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


def normalize_uzbek_text(text: str) -> str:
    """
    Normalize Uzbek text for better search matching
    
    Args:
        text: Original text in Uzbek/Russian
        
    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower()
    
    # Common Uzbek character replacements for better matching
    replacements = {
        "o'": "o",
        "g'": "g",
        "sh": "sh",
        "ch": "ch",
        "ʻ": "",  # Remove apostrophes
        "'": "",
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text.strip()


def extract_price_from_text(text: str) -> Optional[tuple[float, str]]:
    """
    Extract price and currency from text
    
    Args:
        text: Text containing price information
        
    Returns:
        Tuple of (price, currency) or None if not found
        
    Examples:
        "iPhone 15, 900$" -> (900.0, "USD")
        "5,000,000 сум" -> (5000000.0, "UZS")
    """
    # Try to find USD price
    usd_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*\$', text)
    if usd_match:
        price_str = usd_match.group(1).replace(',', '')
        return (float(price_str), "USD")
    
    # Try to find UZS price
    uzs_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:сум|som|soʻm)', text, re.IGNORECASE)
    if uzs_match:
        price_str = uzs_match.group(1).replace(',', '')
        return (float(price_str), "UZS")
    
    return None


# Usage examples
if __name__ == "__main__":
    """Test helper functions"""
    
    # Test filename sanitization
    filename = sanitize_filename("iPhone 15: Pro Max <256GB>")
    print(f"Sanitized filename: {filename}")
    
    # Test price formatting
    print(f"Price (USD): {format_price(750, 'USD')}")
    print(f"Price (UZS): {format_price(5000000, 'UZS')}")
    
    # Test timestamp formatting
    now = datetime.now()
    print(f"Short format: {format_timestamp(now, 'short')}")
    print(f"Long format: {format_timestamp(now, 'long')}")
    
    # Test text truncation
    long_text = "This is a very long text that needs to be truncated"
    print(f"Truncated: {truncate_text(long_text, 30)}")
    
    # Test price extraction
    price_info = extract_price_from_text("iPhone 15 Pro, zo'r holatda, 900$")
    print(f"Extracted price: {price_info}")
