"""
Smart Attendance System — Configuration
========================================
Central configuration file for all system parameters.
Modify these values to match your deployment environment.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UNKNOWN_FACES_DIR = os.path.join(DATA_DIR, "unknown_faces")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)

# Data files
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.pkl")
ATTENDANCE_CSV = os.path.join(DATA_DIR, "attendance.csv")
CSV_HEADER = ["user_id", "name", "timestamp", "confidence"]
DATABASE_FILE = os.path.join(DATA_DIR, "attendance.db")

# ---------------------------------------------------------------------------
# Camera Settings
# ---------------------------------------------------------------------------
# The manage.sh script writes the current camera url to data/camera_url.txt
# Set to 0 for local webcam (development), or an live URL for IP camera
try:
    with open("data/camera_url.txt", "r") as f:
        stored_cam = f.read().strip()
        CAMERA_SOURCE = stored_cam if stored_cam else 0
except FileNotFoundError:
    CAMERA_SOURCE = os.environ.get("CAMERA_SOURCE", 0)

# If CAMERA_SOURCE is a digit string (e.g. from env), cast to int for webcam index
if isinstance(CAMERA_SOURCE, str) and CAMERA_SOURCE.isdigit():
    CAMERA_SOURCE = int(CAMERA_SOURCE)

# Frame processing
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
PROCESS_EVERY_N_FRAMES = 3          # Skip frames for performance
MAX_FACES_PER_FRAME = 5             # Limit concurrent face processing
CAMERA_RECONNECT_DELAY = 5          # Seconds to wait before reconnecting

# ---------------------------------------------------------------------------
# Face Recognition Settings
# ---------------------------------------------------------------------------
FACE_DETECTION_MODEL = "hog"        # "hog" (CPU-fast) or "cnn" (GPU-accurate)
REGISTRATION_SAMPLES = 5            # Number of face samples during registration

# Cosine similarity threshold (0.0 to 1.0)
# Higher = stricter matching; 0.55 ≈ good balance of accuracy vs tolerance
# face_recognition produces normalised 128-d embeddings, so cosine similarity
# is a reliable measure:  1.0 = identical, 0.0 = orthogonal
COSINE_THRESHOLD = 0.55

# ---------------------------------------------------------------------------
# Attendance & Sweep Settings
# ---------------------------------------------------------------------------
SWEEP_MODE_ENABLED = True
SWEEPS_PER_HOUR = 4                 # How many randomized sweeps to run per hour
SWEEP_DURATION_SECONDS = 30         # How long each sweep lasts


# ---------------------------------------------------------------------------
# Flask Settings
# ---------------------------------------------------------------------------
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False                  # Set True only during development
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "smart-attendance-secret-key-change-in-production"
)

# Dashboard auto-refresh interval (seconds)
DASHBOARD_REFRESH_INTERVAL = 10

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "[%(levelname)s] %(message)s"
LOG_LEVEL = "INFO"
