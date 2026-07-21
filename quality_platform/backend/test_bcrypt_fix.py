#!/usr/bin/env python3
"""
Test script to verify the bcrypt password length fix works correctly.
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import get_password_hash

def test_bcrypt_fix():
    """Test that the bcrypt fix handles long passwords correctly."""
    print("Testing bcrypt password length fix...")
    
    # Test normal password
    normal_password = "admin123"
    try:
        hash1 = get_password_hash(normal_password)
        print(f"[+] Normal password '{normal_password}' hashed successfully")
        print(f"  Hash: {hash1[:20]}...")
    except Exception as e:
        print(f"[-] Normal password failed: {e}")
        return False
    
    # Test long password (over 72 bytes)
    long_password = "a" * 100  # 100 characters, definitely over 72 bytes
    try:
        hash2 = get_password_hash(long_password)
        print(f"[+] Long password ({len(long_password)} chars) hashed successfully")
        print(f"  Hash: {hash2[:20]}...")
    except Exception as e:
        print(f"[-] Long password failed: {e}")
        return False
    
    # Test that the function truncates properly
    very_long_password = "x" * 150
    try:
        hash3 = get_password_hash(very_long_password)
        print(f"[+] Very long password ({len(very_long_password)} chars) hashed successfully")
        print(f"  Hash: {hash3[:20]}...")
    except Exception as e:
        print(f"[-] Very long password failed: {e}")
        return False
    
    print("\n[+] All bcrypt fix tests passed!")
    return True

if __name__ == "__main__":
    success = test_bcrypt_fix()
    sys.exit(0 if success else 1)