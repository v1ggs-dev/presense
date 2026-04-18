"""
Smart Attendance System — Attendance Logic
=============================================
Orchestration between recognition results and storage.
Handles Sweep tracking, CSV export, and unknown face management.
"""

import os
import csv
import cv2
import logging
from datetime import datetime

import config
from app import database

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mark Attendance
# ---------------------------------------------------------------------------

def mark_attendance(user_id, name, confidence, sweep_id):
    """
    Mark attendance for a recognized user during a specific sweep.
    Database UNIQUE constraint prevents double-marking per sweep.

    Args:
        user_id: Unique identifier
        name: Person's name
        confidence: Recognition confidence (0.0–1.0)
        sweep_id: The ID of the currently active sweep
    """
    if not sweep_id:
        return False

    inserted = database.add_attendance(user_id, sweep_id, confidence)
    
    if inserted:
        logger.info(f"Attendance marked for sweep {sweep_id}: {name} ({confidence:.0%})")
        return True
    return False


# ---------------------------------------------------------------------------
# CSV Operations
# ---------------------------------------------------------------------------

def export_csv(class_id):
    """
    Generate CSV content for a specific class session summary.
    """
    summary = database.get_class_attendance_summary(class_id)

    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "Name", "Sweeps Attended", "Total Sweeps", "Percentage"])

    for record in summary:
        writer.writerow([
            record["user_id"],
            record["name"],
            record["sweeps_attended"],
            record["total_sweeps"],
            f"{record['percentage']}%"
        ])

    return output.getvalue()


# ---------------------------------------------------------------------------
# Unknown Face Handling
# ---------------------------------------------------------------------------

def save_unknown_face(frame, bbox):
    """
    Save a cropped image of an unrecognized face for later review.
    """
    try:
        top, right, bottom, left = bbox

        # Add padding around the face crop
        pad = 20
        h, w = frame.shape[:2]
        top = max(0, top - pad)
        left = max(0, left - pad)
        bottom = min(h, bottom + pad)
        right = min(w, right + pad)

        face_crop = frame[top:bottom, left:right]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"unknown_{timestamp}.jpg"
        filepath = os.path.join(config.UNKNOWN_FACES_DIR, filename)

        cv2.imwrite(filepath, face_crop)
        logger.debug(f"Unknown face saved: {filename}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save unknown face: {e}")
        return None
