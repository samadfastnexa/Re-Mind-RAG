"""
Import territories from a JSON file.

Usage:
    python import_territories_from_json.py territory_data.json
"""

import requests
import json
import sys
from pathlib import Path


# API Configuration
API_BASE_URL = "http://localhost:8001"
USERNAME = "admin"  # Change to your admin username
PASSWORD = "admin123"  # Change to your admin password


def login() -> str:
    """Login and get access token."""
    print("🔐 Logging in...")
    response = requests.post(
        f"{API_BASE_URL}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    print("✅ Login successful!")
    return response.json()["access_token"]


def import_territories(token: str, data: list, clear_existing: bool = False):
    """Import territory data."""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{API_BASE_URL}/api/admin/territories/import",
        headers=headers,
        json={
            "clear_existing": clear_existing,
            "data": data
        }
    )
    response.raise_for_status()
    return response.json()


def main():
    """Main import function."""
    if len(sys.argv) < 2:
        print("Usage: python import_territories_from_json.py <json_file>")
        print()
        print("Example:")
        print("  python import_territories_from_json.py territory_data.json")
        sys.exit(1)

    json_file = sys.argv[1]

    # Check if file exists
    if not Path(json_file).exists():
        print(f"❌ File not found: {json_file}")
        sys.exit(1)

    print("=" * 70)
    print("Territory Import Script - JSON File Import")
    print("=" * 70)
    print()
    print(f"📁 Reading data from: {json_file}")

    # Load JSON data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} territory entries")
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        sys.exit(1)

    # Validate data structure
    print()
    print("🔍 Validating data structure...")
    required_fields = ["region", "city", "zone", "territories"]

    for i, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                print(f"❌ Entry {i} missing required field: {field}")
                sys.exit(1)

    print("✅ Data structure valid!")

    # Login
    print()
    try:
        token = login()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)

    # Ask if user wants to clear existing data
    print()
    clear_existing = input("⚠️  Clear existing territory data? (yes/no): ").lower() == "yes"

    if clear_existing:
        print("⚠️  WARNING: This will delete all existing territory data!")
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm != "DELETE":
            print("❌ Import cancelled")
            sys.exit(0)

    # Import territories
    print()
    print(f"📥 Importing territories...")
    print()

    try:
        result = import_territories(token, data, clear_existing=clear_existing)

        print("✅ Import completed successfully!")
        print()
        print("📊 Import Statistics:")
        print(f"  • Regions:      {result['stats']['regions']}")
        print(f"  • Cities:       {result['stats']['cities']}")
        print(f"  • Zones:        {result['stats']['zones']}")
        print(f"  • Territories:  {result['stats']['territories']}")
        if result['stats']['skipped'] > 0:
            print(f"  • Skipped:      {result['stats']['skipped']}")

    except Exception as e:
        print(f"❌ Import failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"   Details: {error_detail}")
            except:
                pass
        sys.exit(1)

    print()
    print("=" * 70)
    print("Import complete! You can now access the data via:")
    print()
    print("  • View all regions:    GET http://localhost:8001/api/territories/regions")
    print("  • View hierarchy:      GET http://localhost:8001/api/territories/hierarchy")
    print("  • Search territories:  GET http://localhost:8001/api/territories/search?q=<query>")
    print()
    print("API Documentation: http://localhost:8001/docs")
    print("=" * 70)


if __name__ == "__main__":
    main()
