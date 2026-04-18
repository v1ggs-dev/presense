"""
Smart Attendance System — Database Layer
==========================================
SQLite operations for user management, timetable, and attendance records.
"""

import sqlite3
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def get_connection():
    """Create and return a database connection with row factory."""
    conn = sqlite3.connect(config.DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Schema Migration for Timetable Additions
    try:
        cursor.execute("SELECT target_sweeps FROM timetable LIMIT 1")
    except sqlite3.OperationalError:
        logger.warning("Upgrading DB schema for Per-Class Sweeps...")
        cursor.execute("DROP TABLE IF EXISTS attendance")
        cursor.execute("DROP TABLE IF EXISTS sweeps")
        cursor.execute("DROP TABLE IF EXISTS classes")
        cursor.execute("DROP TABLE IF EXISTS timetable")

    # Timetable Schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week TEXT NOT NULL,
            subject     TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            end_time    TEXT NOT NULL,
            target_sweeps INTEGER NOT NULL
        )
    """)

    # Classes/Sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject     TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            end_time    TEXT,
            status      TEXT NOT NULL DEFAULT 'active',
            target_sweeps INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL
        )
    """)

    # Sweeps
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sweeps (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id    INTEGER NOT NULL,
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
        )
    """)

    # Attendance logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            sweep_id    INTEGER NOT NULL,
            confidence  REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (sweep_id) REFERENCES sweeps(id) ON DELETE CASCADE,
            UNIQUE(user_id, sweep_id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# ---------------------------------------------------------------------------
# Timetable Operations
# ---------------------------------------------------------------------------

def add_schedule(day_of_week, subject, start_time, end_time, target_sweeps):
    conn = get_connection()
    conn.execute(
        "INSERT INTO timetable (day_of_week, subject, start_time, end_time, target_sweeps) VALUES (?, ?, ?, ?, ?)",
        (day_of_week, subject, start_time, end_time, target_sweeps)
    )
    conn.commit()
    conn.close()

def get_schedule(day=None):
    conn = get_connection()
    if day:
        records = conn.execute("SELECT * FROM timetable WHERE day_of_week = ? ORDER BY start_time ASC", (day,)).fetchall()
    else:
        records = conn.execute("SELECT * FROM timetable ORDER BY day_of_week ASC, start_time ASC").fetchall()
    conn.close()
    return [dict(r) for r in records]

def delete_schedule(schedule_id):
    conn = get_connection()
    conn.execute("DELETE FROM timetable WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# User Operations
# ---------------------------------------------------------------------------

def add_user(user_id, name):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to add user: {e}")
    finally:
        conn.close()

def get_all_users():
    conn = get_connection()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(u) for u in users]

def get_user_count():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return count

def delete_user(user_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM attendance WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to delete user {user_id}: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Class Session Operations
# ---------------------------------------------------------------------------

def start_class(subject="Manual Session", target_sweeps=4, duration_seconds=3600):
    conn = get_connection()
    conn.execute("UPDATE classes SET status = 'completed', end_time = ? WHERE status = 'active'", 
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    
    cursor = conn.execute(
        "INSERT INTO classes (subject, start_time, status, target_sweeps, duration_seconds) VALUES (?, ?, 'active', ?, ?)",
        (subject, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), target_sweeps, duration_seconds)
    )
    class_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Started new class: {subject} (ID: {class_id}) | Target Sweeps: {target_sweeps}")
    return class_id

def end_class():
    conn = get_connection()
    conn.execute("UPDATE classes SET status = 'completed', end_time = ? WHERE status = 'active'", 
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()
    logger.info("Ended active class session")

def get_active_class():
    conn = get_connection()
    record = conn.execute("SELECT * FROM classes WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(record) if record else None


# ---------------------------------------------------------------------------
# Sweep & Attendance Operations
# ---------------------------------------------------------------------------

def start_sweep(class_id):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO sweeps (class_id, timestamp) VALUES (?, ?)",
        (class_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    sweep_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sweep_id

def get_sweep_count(class_id):
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM sweeps WHERE class_id = ?", (class_id,)).fetchone()[0]
    conn.close()
    return count

def add_attendance(user_id, sweep_id, confidence):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO attendance (user_id, sweep_id, confidence) VALUES (?, ?, ?)",
            (user_id, sweep_id, round(confidence, 2))
        )
        inserted = conn.execute("SELECT changes()").fetchone()[0] > 0
        conn.commit()
        return inserted
    except sqlite3.Error as e:
        logger.error(f"Failed to record attendance: {e}")
        return False
    finally:
        conn.close()

def get_class_attendance_summary(class_id):
    total_sweeps = get_sweep_count(class_id)
    if total_sweeps == 0:
        return []

    conn = get_connection()
    query = """
        SELECT 
            u.id as user_id, 
            u.name, 
            COUNT(a.id) as sweeps_attended
        FROM users u
        LEFT JOIN attendance a ON u.id = a.user_id AND a.sweep_id IN (
            SELECT id FROM sweeps WHERE class_id = ?
        )
        GROUP BY u.id
    """
    records = conn.execute(query, (class_id,)).fetchall()
    conn.close()

    summary = []
    for r in records:
        attended = r['sweeps_attended']
        pct = int((attended / total_sweeps) * 100) if total_sweeps > 0 else 0
        summary.append({
            "user_id": r['user_id'],
            "name": r['name'],
            "sweeps_attended": attended,
            "total_sweeps": total_sweeps,
            "percentage": pct
        })
    
    summary.sort(key=lambda x: x['percentage'], reverse=True)
    return summary

def get_class_details(class_id):
    conn = get_connection()
    record = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
    conn.close()
    return dict(record) if record else None

def get_all_classes():
    """Return all class sessions (newest first) with sweep counts."""
    conn = get_connection()
    records = conn.execute("""
        SELECT c.*, COUNT(s.id) as sweep_count
        FROM classes c
        LEFT JOIN sweeps s ON c.id = s.class_id
        GROUP BY c.id
        ORDER BY c.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in records]

