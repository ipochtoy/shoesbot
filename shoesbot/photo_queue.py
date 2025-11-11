"""
Photo upload queue to prevent data loss.

Saves photos to local SQLite queue before uploading to Django.
Retries failed uploads automatically.
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from shoesbot.logging_setup import logger


class PhotoUploadQueue:
    """Queue for photo uploads with retry logic."""
    
    def __init__(self, db_path: str = None):
        """Initialize queue."""
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), 
                '../data/photo_queue.db'
            )
        
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Create database and tables if not exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correlation_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                message_ids TEXT NOT NULL,
                photos_data TEXT NOT NULL,
                barcodes_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_retry_at TEXT,
                uploaded_at TEXT,
                error_message TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status 
            ON pending_uploads(status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_correlation 
            ON pending_uploads(correlation_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_upload(
        self,
        correlation_id: str,
        chat_id: int,
        message_ids: list,
        photos_data: list,
        barcodes_data: list,
    ) -> int:
        """
        Add upload to queue.
        
        Args:
            correlation_id: Unique batch ID
            chat_id: Telegram chat ID
            message_ids: List of message IDs
            photos_data: List of photo dicts
            barcodes_data: List of barcode dicts
        
        Returns:
            Queue entry ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO pending_uploads 
            (correlation_id, chat_id, message_ids, photos_data, barcodes_data, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (
            correlation_id,
            chat_id,
            json.dumps(message_ids),
            json.dumps(photos_data),
            json.dumps(barcodes_data),
            datetime.now().isoformat(),
        ))
        
        upload_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"📦 Added to queue: {correlation_id} (ID: {upload_id})")
        return upload_id
    
    def mark_uploaded(self, correlation_id: str):
        """Mark upload as successfully completed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pending_uploads 
            SET status = 'uploaded', uploaded_at = ?
            WHERE correlation_id = ? AND status != 'uploaded'
        ''', (datetime.now().isoformat(), correlation_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Marked uploaded: {correlation_id}")
    
    def mark_failed(self, correlation_id: str, error: str):
        """Mark upload as failed and increment retry counter."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pending_uploads 
            SET 
                retry_count = retry_count + 1,
                last_retry_at = ?,
                error_message = ?,
                status = CASE 
                    WHEN retry_count >= 10 THEN 'failed_permanent'
                    ELSE 'pending'
                END
            WHERE correlation_id = ?
        ''', (datetime.now().isoformat(), error, correlation_id))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"❌ Upload failed: {correlation_id} - {error}")
    
    def get_pending_uploads(self, max_retry: int = 10) -> List[Dict]:
        """
        Get uploads pending retry.
        
        Args:
            max_retry: Max retry count
        
        Returns:
            List of pending upload dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get uploads that:
        # 1. Are pending
        # 2. Haven't hit max retries
        # 3. Either never retried OR last retry was >5min ago (exponential backoff)
        
        cursor.execute('''
            SELECT 
                id, correlation_id, chat_id, message_ids, 
                photos_data, barcodes_data, retry_count,
                last_retry_at, created_at
            FROM pending_uploads
            WHERE status = 'pending'
            AND retry_count < ?
            AND (
                last_retry_at IS NULL 
                OR datetime(last_retry_at) < datetime('now', '-' || (retry_count * 5) || ' minutes')
            )
            ORDER BY created_at ASC
            LIMIT 10
        ''', (max_retry,))
        
        rows = cursor.fetchall()
        conn.close()
        
        uploads = []
        for row in rows:
            uploads.append({
                'id': row[0],
                'correlation_id': row[1],
                'chat_id': row[2],
                'message_ids': json.loads(row[3]),
                'photos_data': json.loads(row[4]),
                'barcodes_data': json.loads(row[5]),
                'retry_count': row[6],
                'last_retry_at': row[7],
                'created_at': row[8],
            })
        
        return uploads
    
    def get_stats(self) -> Dict:
        """Get queue statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                status,
                COUNT(*) as count
            FROM pending_uploads
            GROUP BY status
        ''')
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        
        conn.close()
        return stats
    
    def cleanup_old_uploads(self, days: int = 7):
        """Delete uploaded entries older than X days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            DELETE FROM pending_uploads
            WHERE status = 'uploaded'
            AND uploaded_at < ?
        ''', (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old uploads")
        
        return deleted

