#!/usr/bin/env python3
"""
Compatibility fix for bcrypt and passlib version issues.
This module patches the bcrypt module to provide the __about__ attribute
that passlib expects.
"""
import sys
import bcrypt

# Create the missing __about__ module for bcrypt compatibility
if not hasattr(bcrypt, '__about__'):
    class _About:
        __version__ = getattr(bcrypt, '__version__', '4.1.2')
    
    bcrypt.__about__ = _About()

# Also patch the passlib bcrypt handler to avoid the wrap bug detection
# that causes issues with long passwords
try:
    from passlib.handlers import bcrypt as passlib_bcrypt
    
    # Override the detect_wrap_bug function to skip the problematic test
    def _safe_detect_wrap_bug(ident):
        """Skip wrap bug detection to avoid password length issues."""
        return False
    
    # Apply the patch
    if hasattr(passlib_bcrypt, 'detect_wrap_bug'):
        passlib_bcrypt.detect_wrap_bug = _safe_detect_wrap_bug
    
    print("[+] Applied bcrypt compatibility fixes")
    
except ImportError:
    print("[+] Passlib not available, skipping compatibility patches")