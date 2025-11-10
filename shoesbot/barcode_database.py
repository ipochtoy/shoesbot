"""Intelligent barcode database for tracking scan history."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from shoesbot.logging_setup import logger


class BarcodeDatabase:
    """SQLite database for tracking barcode scan history."""

    def __init__(self, db_path: str = ".barcode_history.db"):
        """Initialize database with specified path."""
        self.db_path = Path(db_path)
        self.conn = None
        self._init_db()
        logger.info(f"BarcodeDatabase initialized: {self.db_path.absolute()}")

    def _init_db(self):
        """Create database tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Access columns by name

            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS barcodes (
                    barcode TEXT PRIMARY KEY,
                    symbology TEXT NOT NULL,
                    first_seen TIMESTAMP NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    scan_count INTEGER DEFAULT 1,
                    product_name TEXT,
                    brand TEXT,
                    category TEXT,
                    notes TEXT,
                    metadata TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    chat_id INTEGER,
                    source TEXT,
                    FOREIGN KEY (barcode) REFERENCES barcodes(barcode)
                )
            """)

            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_seen ON barcodes(last_seen DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_count ON barcodes(scan_count DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scan_history_timestamp ON scan_history(timestamp DESC)
            """)

            self.conn.commit()
            logger.info("BarcodeDatabase tables initialized")

        except Exception as e:
            logger.error(f"BarcodeDatabase init error: {e}", exc_info=True)

    def record_scan(self, barcode: str, symbology: str, chat_id: int = None, source: str = None) -> Dict:
        """Record a barcode scan. Returns info about the barcode."""
        try:
            cursor = self.conn.cursor()
            now = datetime.now()

            # Check if barcode exists
            cursor.execute("SELECT * FROM barcodes WHERE barcode = ?", (barcode,))
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE barcodes
                    SET last_seen = ?, scan_count = scan_count + 1
                    WHERE barcode = ?
                """, (now, barcode))

                result = {
                    'barcode': barcode,
                    'is_new': False,
                    'first_seen': existing['first_seen'],
                    'scan_count': existing['scan_count'] + 1,
                    'product_name': existing['product_name'],
                    'brand': existing['brand'],
                }
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO barcodes (barcode, symbology, first_seen, last_seen, scan_count)
                    VALUES (?, ?, ?, ?, 1)
                """, (barcode, symbology, now, now))

                result = {
                    'barcode': barcode,
                    'is_new': True,
                    'first_seen': now.isoformat(),
                    'scan_count': 1,
                    'product_name': None,
                    'brand': None,
                }

            # Record in scan history
            cursor.execute("""
                INSERT INTO scan_history (barcode, timestamp, chat_id, source)
                VALUES (?, ?, ?, ?)
            """, (barcode, now, chat_id, source))

            self.conn.commit()
            logger.debug(f"Recorded scan: {barcode} (new={result['is_new']}, count={result['scan_count']})")
            return result

        except Exception as e:
            logger.error(f"BarcodeDatabase record_scan error: {e}", exc_info=True)
            return {
                'barcode': barcode,
                'is_new': True,
                'error': str(e)
            }

    def update_product_info(self, barcode: str, product_name: str = None, brand: str = None,
                           category: str = None, notes: str = None):
        """Update product information for a barcode."""
        try:
            cursor = self.conn.cursor()
            updates = []
            params = []

            if product_name is not None:
                updates.append("product_name = ?")
                params.append(product_name)
            if brand is not None:
                updates.append("brand = ?")
                params.append(brand)
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)

            if updates:
                params.append(barcode)
                query = f"UPDATE barcodes SET {', '.join(updates)} WHERE barcode = ?"
                cursor.execute(query, params)
                self.conn.commit()
                logger.info(f"Updated product info for {barcode}")

        except Exception as e:
            logger.error(f"BarcodeDatabase update_product_info error: {e}", exc_info=True)

    def get_barcode_info(self, barcode: str) -> Optional[Dict]:
        """Get information about a specific barcode."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM barcodes WHERE barcode = ?", (barcode,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"BarcodeDatabase get_barcode_info error: {e}", exc_info=True)
            return None

    def get_top_barcodes(self, limit: int = 20) -> List[Dict]:
        """Get most frequently scanned barcodes."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM barcodes
                ORDER BY scan_count DESC, last_seen DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"BarcodeDatabase get_top_barcodes error: {e}", exc_info=True)
            return []

    def get_recent_scans(self, limit: int = 50) -> List[Dict]:
        """Get recent scan history."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT s.*, b.product_name, b.brand
                FROM scan_history s
                LEFT JOIN barcodes b ON s.barcode = b.barcode
                ORDER BY s.timestamp DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"BarcodeDatabase get_recent_scans error: {e}", exc_info=True)
            return []

    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            cursor = self.conn.cursor()

            # Total unique barcodes
            cursor.execute("SELECT COUNT(*) as count FROM barcodes")
            total_barcodes = cursor.fetchone()['count']

            # Total scans
            cursor.execute("SELECT SUM(scan_count) as total FROM barcodes")
            total_scans = cursor.fetchone()['total'] or 0

            # Barcodes scanned today
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT barcode) as count
                FROM scan_history
                WHERE DATE(timestamp) = ?
            """, (today,))
            scanned_today = cursor.fetchone()['count']

            # Most scanned barcode
            cursor.execute("""
                SELECT barcode, scan_count, product_name
                FROM barcodes
                ORDER BY scan_count DESC
                LIMIT 1
            """)
            most_scanned = cursor.fetchone()

            return {
                'total_unique_barcodes': total_barcodes,
                'total_scans': total_scans,
                'scanned_today': scanned_today,
                'most_scanned': dict(most_scanned) if most_scanned else None,
            }

        except Exception as e:
            logger.error(f"BarcodeDatabase get_stats error: {e}", exc_info=True)
            return {}

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("BarcodeDatabase connection closed")


# Global database instance
_db_instance: Optional[BarcodeDatabase] = None


def get_barcode_db() -> BarcodeDatabase:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        db_path = os.getenv("BARCODE_DB_PATH", ".barcode_history.db")
        _db_instance = BarcodeDatabase(db_path)
    return _db_instance
