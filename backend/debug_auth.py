#!/usr/bin/env python3
"""
Debug script to test database connection and authorization checks.

Usage:
    python debug_auth.py <email>

This script will:
1. Test database connection
2. List all approved users
3. Check if the provided email is approved
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent
project_root = backend_dir.parent

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / "local.env")
load_dotenv(project_root / ".env")

# Import Flask app
from app import create_app

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_auth.py <email>")
        print("\nExample: python debug_auth.py user@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        from app.models import ApprovedUser, User, db
        from app.db import is_email_approved, check_db_connection
        
        print("=" * 60)
        print("Database Authorization Debug")
        print("=" * 60)
        
        # Test database connection
        print("\n1. Testing database connection...")
        db_healthy, db_message = check_db_connection()
        if db_healthy:
            print(f"   ✓ {db_message}")
        else:
            print(f"   ✗ {db_message}")
            print("\n   ERROR: Database connection failed!")
            print("   Check your DATABASE_URL in local.env")
            sys.exit(1)
        
        # List all approved users
        print("\n2. Listing all approved users...")
        try:
            approved_users = ApprovedUser.query.all()
            if approved_users:
                print(f"   Found {len(approved_users)} approved user(s):")
                for au in approved_users:
                    print(f"   - {au.email} (active={au.is_active}, added_at={au.added_at})")
            else:
                print("   ⚠ No approved users found in database!")
                print("   Add users with: INSERT INTO approved_users (email, note) VALUES ('email@example.com', 'Note');")
        except Exception as e:
            print(f"   ✗ Error querying approved_users: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Check specific email
        print(f"\n3. Checking authorization for: {email}")
        try:
            is_approved = is_email_approved(email)
            if is_approved:
                print(f"   ✓ Email is APPROVED and active")
            else:
                print(f"   ✗ Email is NOT approved or not active")
                
                # Check if email exists but is inactive
                approved_user = ApprovedUser.query.filter_by(email=email).first()
                if approved_user:
                    print(f"   ⚠ Email found in database but is_active={approved_user.is_active}")
                else:
                    print(f"   ⚠ Email not found in approved_users table")
                    print(f"   Make sure the email matches exactly (case-sensitive)")
        except Exception as e:
            print(f"   ✗ Error checking authorization: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # List all users
        print("\n4. Listing all users...")
        try:
            users = User.query.all()
            if users:
                print(f"   Found {len(users)} user(s):")
                for u in users:
                    print(f"   - {u.email} (google_sub={u.google_sub[:20]}..., active={u.is_active})")
            else:
                print("   No users found (users are created automatically on first login)")
        except Exception as e:
            print(f"   ✗ Error querying users: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("Debug complete")
        print("=" * 60)

if __name__ == "__main__":
    main()


