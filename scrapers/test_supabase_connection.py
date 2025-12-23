#!/usr/bin/env python3
"""
Test script to verify Supabase connection is working.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Testing Supabase Connection")
print("=" * 60)

try:
    from supabase_client import get_supabase_client, SUPABASE_KEY, SUPABASE_URL
    
    print(f"\nSUPABASE_URL: {SUPABASE_URL}")
    print(f"SUPABASE_KEY: {'SET' if SUPABASE_KEY else 'NOT SET'}")
    if SUPABASE_KEY:
        print(f"Key length: {len(SUPABASE_KEY)} characters")
        print(f"Key starts with: {SUPABASE_KEY[:20]}...")
    
    print("\nAttempting to create Supabase client...")
    supabase = get_supabase_client()
    
    if supabase:
        print("✅ Supabase client created successfully!")
        
        # Test a simple query
        print("\nTesting database connection with a simple query...")
        try:
            result = supabase.table('themes').select('theme_name').limit(1).execute()
            print(f"✅ Database connection successful! Found {len(result.data)} theme(s)")
        except Exception as e:
            print(f"⚠️  Client created but query failed: {e}")
    else:
        print("❌ Failed to create Supabase client")
        print("\nTroubleshooting:")
        print("1. Make sure .env file exists in project root")
        print("2. Make sure SUPABASE_KEY is set in .env file")
        print("3. Make sure python-dotenv is installed: pip install python-dotenv")
        print("4. Make sure you're running from the venv if using one")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

