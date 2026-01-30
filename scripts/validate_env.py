"""
Environment Validation Script
Tests that all required environment variables are set and valid
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, validate_environment


def main():
    """Run environment validation"""
    print("=" * 60)
    print("ENVIRONMENT VALIDATION")
    print("=" * 60)
    print()
    
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found!")
        print()
        print("To fix this:")
        print("  1. Copy .env.template to .env")
        print("  2. Fill in all required values")
        print("  3. Run this script again")
        print()
        return 1
    
    print("✓ .env file found")
    print()
    
    # Try to load configuration
    try:
        config = Config.get_instance()
        print("✓ Configuration loaded successfully")
        print()
        
        # Print configuration summary
        config.print_summary()
        print()
        
        # Validate configuration
        if validate_environment():
            print("=" * 60)
            print("✅ VALIDATION PASSED - All settings are valid!")
            print("=" * 60)
            print()
            print("You can now run the application:")
            print("  - Start crawler: python src/crawler.py")
            print("  - Start bot:     python src/bot.py")
            print()
            return 0
        else:
            print("=" * 60)
            print("❌ VALIDATION FAILED - Fix the errors above")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print("=" * 60)
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("  - Missing required environment variables")
        print("  - Invalid values (check format requirements)")
        print("  - Typos in variable names")
        print()
        print("Check your .env file against .env.template")
        return 1


if __name__ == '__main__':
    sys.exit(main())
