"""
Territory import script for orange_live companies.

This script helps import region, zone, and territory data into the RAG system.
"""

import requests
import json
from typing import Dict, List

# API Configuration
API_BASE_URL = "http://localhost:8001"
USERNAME = "admin"  # Change to your admin username
PASSWORD = "admin123"  # Change to your admin password


def login() -> str:
    """Login and get access token."""
    response = requests.post(
        f"{API_BASE_URL}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def import_territories(token: str, data: List[Dict], clear_existing: bool = False):
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


# Sample data structure based on your orange_live companies
# Modify this data according to your actual data
TERRITORY_DATA = [
    # Eastern Hawks Region
    {
        "region": "Eastern Hawks",
        "city": "GUJRANWALA",
        "zone": "GREEN_ZONE_1",
        "territories": ["GHAKHAR", "EMINABAD", "WAZEERABAD", "ALI PUR CHATHA", "KAMOKE"]
    },
    {
        "region": "Eastern Hawks",
        "city": "SARGODHA",
        "zone": "GREEN_ZONE_2",
        "territories": ["BHALWAL", "SILANWALI", "BHERA", "SAHIWAL", "KOT MOMIN"]
    },
    {
        "region": "Eastern Hawks",
        "city": "MIANWALI",
        "zone": "WHITE_ZONE_1",
        "territories": ["ISA KHEL", "PIPLAN"]
    },

    # Northern Eagles Region
    {
        "region": "Northern Eagles",
        "city": "FAISALABAD",
        "zone": "GREEN_ZONE_1",
        "territories": ["SAMUNDARI", "TANDLIAN WALA", "JARANWALA", "CHAK JHUMRA"]
    },
    {
        "region": "Northern Eagles",
        "city": "KASUR",
        "zone": "GREEN_ZONE_2",
        "territories": ["PATTOKI", "CHUNIAN"]
    },
    {
        "region": "Northern Eagles",
        "city": "OKARA",
        "zone": "WHITE_ZONE_1",
        "territories": ["RENALA KHURD", "DEPALPUR"]
    },

    # Central Tigers Region
    {
        "region": "Central Tigers",
        "city": "ARIF WALA",
        "zone": "GREEN_ZONE_1",
        "territories": ["PAKPATTAN"]
    },
    {
        "region": "Central Tigers",
        "city": "BAHAWALNAGAR",
        "zone": "GREEN_ZONE_2",
        "territories": ["FORT ABBAS", "HAROONABAD", "CHISHTIAN"]
    },
    {
        "region": "Central Tigers",
        "city": "VEHARI",
        "zone": "WHITE_ZONE_1",
        "territories": ["BUREWALA", "MAILSI"]
    },

    # Add more regions, cities, zones, and territories as needed...
]


def main():
    """Main import function."""
    print("=" * 60)
    print("Territory Import Script for orange_live Companies")
    print("=" * 60)
    print()

    # Login
    print("🔐 Logging in...")
    try:
        token = login()
        print("✅ Login successful!")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # Import territories
    print()
    print(f"📥 Importing {len(TERRITORY_DATA)} territory entries...")
    print()

    try:
        result = import_territories(token, TERRITORY_DATA, clear_existing=False)

        print("✅ Import completed successfully!")
        print()
        print("📊 Import Statistics:")
        print(f"  • Regions:      {result['stats']['regions']}")
        print(f"  • Cities:       {result['stats']['cities']}")
        print(f"  • Zones:        {result['stats']['zones']}")
        print(f"  • Territories:  {result['stats']['territories']}")
        print(f"  • Skipped:      {result['stats']['skipped']}")

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return

    print()
    print("=" * 60)
    print("Import complete! You can now:")
    print("  1. View all regions:    GET /api/territories/regions")
    print("  2. View hierarchy:      GET /api/territories/hierarchy")
    print("  3. Search territories:  GET /api/territories/search?q=<query>")
    print("=" * 60)


if __name__ == "__main__":
    main()
