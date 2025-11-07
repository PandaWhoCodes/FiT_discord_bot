"""Database operations for storing personality test results."""

import json
import logging
import os
import sys
from datetime import datetime, timezone

import libsql

from .models import PersonalityProfile, Scores

logger = logging.getLogger(__name__)

# Global database connection
db_conn: libsql.Connection | None = None


def init_database() -> None:
    """Initialize Turso database connection and create tables."""
    global db_conn

    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")

    if not turso_url or not turso_token:
        logger.error("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are required")
        sys.exit(1)

    try:
        # Connect to Turso with embedded replica
        db_conn = libsql.connect("personality_bot.db", sync_url=turso_url, auth_token=turso_token)
        logger.info("Connected to Turso database")

        # Sync on startup to pull latest data from Turso
        db_conn.sync()
        logger.info("Synced with remote Turso database")

        # Create test_results table if not exists
        db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_user_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                personality_type TEXT NOT NULL,
                test_type TEXT NOT NULL,
                scores TEXT NOT NULL,
                biblical_characters TEXT,
                spiritual_gifts TEXT,
                ministry_suggestions TEXT,
                completed_at TEXT NOT NULL
            )
        """
        )

        # Create messages table for analytics
        db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                discord_user_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                message_text TEXT NOT NULL,
                channel_id TEXT,
                channel_name TEXT,
                server_id TEXT,
                server_name TEXT,
                is_dm INTEGER NOT NULL,
                message_length INTEGER NOT NULL,
                has_attachments INTEGER NOT NULL,
                has_embeds INTEGER NOT NULL,
                has_mentions INTEGER NOT NULL,
                reply_to_message_id TEXT,
                created_at TEXT NOT NULL,
                edited_at TEXT
            )
        """
        )

        # Create indexes for common queries
        db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_user
            ON messages(discord_user_id)
        """
        )
        db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_channel
            ON messages(channel_id)
        """
        )
        db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_created
            ON messages(created_at)
        """
        )

        # Create prayers table for prayer management
        db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prayers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                discord_user_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                raw_message TEXT NOT NULL,
                extracted_prayer TEXT NOT NULL,
                posted_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """
        )

        # Create indexes for prayers table
        db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_prayers_posted_at
            ON prayers(posted_at)
        """
        )
        db_conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_prayers_user_id
            ON prayers(discord_user_id)
        """
        )

        db_conn.commit()
        db_conn.sync()
        logger.info("Database schema initialized")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


def save_test_result(
    user_id: int,
    username: str,
    personality_type: str,
    test_type: str,
    scores: Scores,
    profile: PersonalityProfile,
) -> None:
    """Save test result to database."""
    if db_conn is None:
        logger.error("Database not initialized")
        return

    try:
        db_conn.execute(
            """
            INSERT INTO test_results (
                discord_user_id, discord_username, personality_type,
                test_type, scores, biblical_characters, spiritual_gifts,
                ministry_suggestions, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(user_id),
                username,
                personality_type,
                test_type,
                json.dumps(scores),
                json.dumps(profile.biblical_characters),
                json.dumps(profile.spiritual_gifts),
                json.dumps(profile.ministry_suggestions),
                datetime.now(timezone.utc).isoformat(),
            ],
        )
        db_conn.commit()
        db_conn.sync()
        logger.info(f"Saved test result for {username} ({user_id}): {personality_type}")
    except Exception as e:
        logger.error(f"Failed to save test result: {e}")


def save_message(message_data: dict) -> None:
    """
    Save message to database for analytics.

    Args:
        message_data: Dictionary containing message fields matching the schema
    """
    if db_conn is None:
        logger.error("Database not initialized")
        return

    try:
        db_conn.execute(
            """
            INSERT INTO messages (
                message_id, discord_user_id, discord_username,
                message_text, channel_id, channel_name,
                server_id, server_name, is_dm, message_length,
                has_attachments, has_embeds, has_mentions,
                reply_to_message_id, created_at, edited_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                message_data["message_id"],
                message_data["discord_user_id"],
                message_data["discord_username"],
                message_data["message_text"],
                message_data["channel_id"],
                message_data["channel_name"],
                message_data["server_id"],
                message_data["server_name"],
                1 if message_data["is_dm"] else 0,
                message_data["message_length"],
                1 if message_data["has_attachments"] else 0,
                1 if message_data["has_embeds"] else 0,
                1 if message_data["has_mentions"] else 0,
                message_data["reply_to_message_id"],
                message_data["created_at"],
                message_data["edited_at"],
            ],
        )
        db_conn.commit()
        db_conn.sync()
    except Exception as e:
        logger.error(f"Failed to save message: {e}")


def save_prayer(prayer_data: dict) -> None:
    """
    Save prayer to database.

    Args:
        prayer_data: Dictionary containing prayer fields matching the schema
    """
    if db_conn is None:
        logger.error("Database not initialized")
        return

    try:
        db_conn.execute(
            """
            INSERT INTO prayers (
                message_id, discord_user_id, discord_username,
                channel_id, raw_message, extracted_prayer,
                posted_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                prayer_data["message_id"],
                prayer_data["discord_user_id"],
                prayer_data["discord_username"],
                prayer_data["channel_id"],
                prayer_data["raw_message"],
                prayer_data["extracted_prayer"],
                prayer_data["posted_at"],
                prayer_data["created_at"],
            ],
        )
        db_conn.commit()
        db_conn.sync()
        logger.info(
            f"Saved prayer from {prayer_data['discord_username']}: "
            f"{prayer_data['extracted_prayer'][:50]}..."
        )
    except Exception as e:
        logger.error(f"Failed to save prayer: {e}")


def get_prayers_for_week(start_date: datetime, end_date: datetime) -> list[dict]:
    """
    Get all prayers posted within a date range.

    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of prayer dictionaries with id, username, prayer text, and timestamp
    """
    if db_conn is None:
        logger.error("Database not initialized")
        return []

    try:
        cursor = db_conn.execute(
            """
            SELECT id, discord_username, extracted_prayer, posted_at
            FROM prayers
            WHERE posted_at BETWEEN ? AND ?
            ORDER BY posted_at ASC
            """,
            [start_date.isoformat(), end_date.isoformat()],
        )

        rows = cursor.fetchall()
        prayers = []
        for row in rows:
            prayers.append(
                {
                    "id": row[0],
                    "discord_username": row[1],
                    "extracted_prayer": row[2],
                    "posted_at": row[3],
                }
            )

        logger.info(
            f"Retrieved {len(prayers)} prayers for week {start_date.date()} to {end_date.date()}"
        )
        return prayers

    except Exception as e:
        logger.error(f"Failed to get prayers for week: {e}")
        return []


def close_database() -> None:
    """Close database connection."""
    global db_conn
    if db_conn:
        db_conn.close()
        logger.info("Database connection closed")
