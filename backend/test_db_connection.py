#!/usr/bin/env python3
"""
Test database connection and help fix DATABASE_URL format issues.

This script will:
1. Test the current DATABASE_URL
2. Show URL encoding for special characters
3. Help format the connection string correctly
"""

import os
import sys
from urllib.parse import quote, unquote
from pathlib import Path

# Load environment
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
from dotenv import load_dotenv
load_dotenv(project_root / "local.env")

def url_encode_password(password):
    """URL encode special characters in password."""
    # Characters that need encoding in PostgreSQL URLs
    special_chars = {
        '!': '%21',
        '@': '%40',
        '#': '%23',
        '$': '%24',
        '%': '%25',
        '^': '%5E',
        '&': '%26',
        '*': '%28',
        '(': '%28',
        ')': '%29',
        '+': '%2B',
        '=': '%3D',
        '?': '%3F',
        '/': '%2F',
        '\\': '%5C',
        '|': '%7C',
        '{': '%7B',
        '}': '%7D',
        '[': '%5B',
        ']': '%5D',
        ':': '%3A',
        ';': '%3B',
        ',': '%2C',
        '<': '%3C',
        '>': '%3E',
        '"': '%22',
        "'": '%27',
        ' ': '%20'
    }
    
    encoded = password
    for char, encoded_char in special_chars.items():
        encoded = encoded.replace(char, encoded_char)
    
    return encoded

def test_connection(database_url):
    """Test database connection."""
    try:
        from sqlalchemy import create_engine, text
        
        print(f"Testing connection string...")
        print(f"URL (masked): {database_url.split('@')[0]}@[HOST]/[DB]")
        
        engine = create_engine(database_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Connection successful!")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False

def main():
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        print("ERROR: DATABASE_URL not set in local.env")
        sys.exit(1)
    
    print("=" * 60)
    print("Database Connection String Helper")
    print("=" * 60)
    print(f"\nCurrent DATABASE_URL (masked):")
    if "@" in database_url:
        parts = database_url.split("@")
        print(f"  {parts[0]}@[HOST]")
    else:
        print(f"  {database_url[:50]}...")
    
    # Check for common issues
    print("\nChecking for common issues...")
    
    issues = []
    
    # Check for unencoded special characters
    if "!" in database_url and "%21" not in database_url:
        issues.append("Password contains '!' which should be URL-encoded as '%21'")
    
    if "@" in database_url:
        at_count = database_url.count("@")
        if at_count > 1:
            issues.append(f"Connection string has {at_count} '@' symbols (should have exactly 1)")
    
    if issues:
        print("\n⚠ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("  ✓ No obvious format issues detected")
    
    # Test connection
    print("\n" + "=" * 60)
    print("Testing Connection")
    print("=" * 60)
    success = test_connection(database_url)
    
    if not success:
        print("\n" + "=" * 60)
        print("Troubleshooting")
        print("=" * 60)
        print("\nCommon Supabase connection string formats:")
        print("\n1. Direct Connection (port 5432):")
        print("   postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        print("\n2. Session Pooler (port 6543):")
        print("   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres")
        print("\n3. Transaction Pooler (port 6543):")
        print("   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true")
        
        print("\nSpecial characters in password must be URL-encoded:")
        print("  ! → %21")
        print("  @ → %40")
        print("  # → %23")
        print("  $ → %24")
        print("  % → %25")
        print("  & → %26")
        print("  ( → %28")
        print("  ) → %29")
        print("  + → %2B")
        print("  = → %3D")
        print("  ? → %3F")
        print("  / → %2F")
        print("  : → %3A")
        print("  ; → %3B")
        
        print("\nTo get your connection string:")
        print("1. Go to Supabase Dashboard")
        print("2. Project Settings > Database")
        print("3. Copy the 'Connection string' (URI format)")
        print("4. If password has special characters, URL-encode them")
        
        print("\nExample fix:")
        print("  Before: postgresql://postgres:pass!word@db.xxx.supabase.co:5432/postgres")
        print("  After:  postgresql://postgres:pass%21word@db.xxx.supabase.co:5432/postgres")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()


