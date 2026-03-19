"""
Territory service for managing regions, zones, and territories.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TerritoryService:
    """Service for managing company territories, zones, and regions."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "territories.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create regions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create cities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                region_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (region_id) REFERENCES regions(id)
            )
        """)

        # Create zones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT,
                city_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (city_id) REFERENCES cities(id),
                UNIQUE(name, city_id)
            )
        """)

        # Create territories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS territories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                zone_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (zone_id) REFERENCES zones(id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Territory database initialized at {self.db_path}")

    def import_bulk_data(self, data: List[Dict]) -> Dict[str, int]:
        """
        Import bulk territory data.

        Expected data format:
        [
            {
                "region": "Eastern Hawks",
                "city": "GUJRANWALA",
                "zone": "GREEN_ZONE_1",
                "territories": ["TERRITORY_1", "TERRITORY_2", ...]
            },
            ...
        ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {
            "regions": 0,
            "cities": 0,
            "zones": 0,
            "territories": 0,
            "skipped": 0
        }

        try:
            for item in data:
                region_name = item.get("region")
                city_name = item.get("city")
                zone_name = item.get("zone")
                territories = item.get("territories", [])

                if not all([region_name, city_name, zone_name]):
                    stats["skipped"] += 1
                    continue

                # Insert or get region
                cursor.execute(
                    "INSERT OR IGNORE INTO regions (name) VALUES (?)",
                    (region_name,)
                )
                if cursor.rowcount > 0:
                    stats["regions"] += 1

                cursor.execute("SELECT id FROM regions WHERE name = ?", (region_name,))
                region_id = cursor.fetchone()[0]

                # Insert or get city
                cursor.execute(
                    "INSERT OR IGNORE INTO cities (name, region_id) VALUES (?, ?)",
                    (city_name, region_id)
                )
                if cursor.rowcount > 0:
                    stats["cities"] += 1

                cursor.execute("SELECT id FROM cities WHERE name = ?", (city_name,))
                city_id = cursor.fetchone()[0]

                # Extract zone color if present
                zone_color = None
                if "GREEN" in zone_name.upper():
                    zone_color = "GREEN"
                elif "WHITE" in zone_name.upper():
                    zone_color = "WHITE"
                elif "BLUE" in zone_name.upper():
                    zone_color = "BLUE"
                elif "RED" in zone_name.upper():
                    zone_color = "RED"

                # Insert or get zone
                cursor.execute(
                    "INSERT OR IGNORE INTO zones (name, color, city_id) VALUES (?, ?, ?)",
                    (zone_name, zone_color, city_id)
                )
                if cursor.rowcount > 0:
                    stats["zones"] += 1

                cursor.execute(
                    "SELECT id FROM zones WHERE name = ? AND city_id = ?",
                    (zone_name, city_id)
                )
                zone_id = cursor.fetchone()[0]

                # Insert territories
                for territory_name in territories:
                    if territory_name:
                        cursor.execute(
                            "INSERT OR IGNORE INTO territories (name, zone_id) VALUES (?, ?)",
                            (territory_name, zone_id)
                        )
                        if cursor.rowcount > 0:
                            stats["territories"] += 1

            conn.commit()
            logger.info(f"Import completed: {stats}")
            return stats

        except Exception as e:
            conn.rollback()
            logger.error(f"Error importing data: {e}")
            raise
        finally:
            conn.close()

    def get_all_regions(self) -> List[Dict]:
        """Get all regions with their cities."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.id, r.name, r.created_at,
                   COUNT(DISTINCT c.id) as city_count
            FROM regions r
            LEFT JOIN cities c ON c.region_id = r.id
            GROUP BY r.id
            ORDER BY r.name
        """)

        regions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return regions

    def get_cities_by_region(self, region_id: int) -> List[Dict]:
        """Get all cities in a region."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.id, c.name, c.created_at,
                   COUNT(DISTINCT z.id) as zone_count
            FROM cities c
            LEFT JOIN zones z ON z.city_id = c.id
            WHERE c.region_id = ?
            GROUP BY c.id
            ORDER BY c.name
        """, (region_id,))

        cities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cities

    def get_zones_by_city(self, city_id: int) -> List[Dict]:
        """Get all zones in a city."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT z.id, z.name, z.color, z.created_at,
                   COUNT(t.id) as territory_count
            FROM zones z
            LEFT JOIN territories t ON t.zone_id = z.id
            WHERE z.city_id = ?
            GROUP BY z.id
            ORDER BY z.name
        """, (city_id,))

        zones = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return zones

    def get_territories_by_zone(self, zone_id: int) -> List[Dict]:
        """Get all territories in a zone."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, created_at
            FROM territories
            WHERE zone_id = ?
            ORDER BY name
        """, (zone_id,))

        territories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return territories

    def get_full_hierarchy(self) -> List[Dict]:
        """Get complete hierarchy: regions -> cities -> zones -> territories."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        regions = []
        cursor.execute("SELECT id, name FROM regions ORDER BY name")

        for region_row in cursor.fetchall():
            region = dict(region_row)
            region["cities"] = []

            cursor.execute(
                "SELECT id, name FROM cities WHERE region_id = ? ORDER BY name",
                (region["id"],)
            )

            for city_row in cursor.fetchall():
                city = dict(city_row)
                city["zones"] = []

                cursor.execute(
                    "SELECT id, name, color FROM zones WHERE city_id = ? ORDER BY name",
                    (city["id"],)
                )

                for zone_row in cursor.fetchall():
                    zone = dict(zone_row)

                    cursor.execute(
                        "SELECT name FROM territories WHERE zone_id = ? ORDER BY name",
                        (zone["id"],)
                    )
                    zone["territories"] = [row["name"] for row in cursor.fetchall()]

                    city["zones"].append(zone)

                region["cities"].append(city)

            regions.append(region)

        conn.close()
        return regions

    def search_territories(self, query: str) -> List[Dict]:
        """Search for territories, zones, cities, or regions by name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        search_term = f"%{query}%"

        cursor.execute("""
            SELECT
                t.name as territory_name,
                z.name as zone_name,
                z.color as zone_color,
                c.name as city_name,
                r.name as region_name
            FROM territories t
            JOIN zones z ON t.zone_id = z.id
            JOIN cities c ON z.city_id = c.id
            JOIN regions r ON c.region_id = r.id
            WHERE t.name LIKE ? OR z.name LIKE ? OR c.name LIKE ? OR r.name LIKE ?
            ORDER BY r.name, c.name, z.name, t.name
        """, (search_term, search_term, search_term, search_term))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def clear_all_data(self):
        """Clear all territory data (use with caution)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM territories")
        cursor.execute("DELETE FROM zones")
        cursor.execute("DELETE FROM cities")
        cursor.execute("DELETE FROM regions")

        conn.commit()
        conn.close()
        logger.info("All territory data cleared")
