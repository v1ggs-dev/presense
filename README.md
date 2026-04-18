# Smart Attendance System

AI-powered facial recognition attendance system built with Python, Flask, and OpenCV.  
Designed for **Raspberry Pi 5** deployment with **IP camera (RTSP)** input.

---

## Features

- **Real-time face recognition** using HOG detection + 128-d face encodings
- **Cosine similarity matching** with configurable confidence threshold
- **Automatic attendance marking** with 5-minute duplicate prevention
- **Web dashboard** — live stats, attendance log, CSV export
- **User registration** — step-by-step face capture with visual progress
- **Unknown face capture** — saves unrecognised faces for review
- **RTSP / IP camera support** — works with any RTSP-compatible camera
- **Performance optimised** — frame skipping, resolution capping, face count limits

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Flask Web UI                     │
│  Dashboard  │  Users  │  Register  │  API Endpoints │
└──────┬──────┴────┬────┴─────┬──────┴───────┬────────┘
       │           │          │              │
  ┌────▼────┐  ┌───▼───┐  ┌──▼──────┐  ┌────▼─────┐
  │ camera  │  │ recog │  │ attend  │  │ database │
  │  .py    │  │ .py   │  │  .py    │  │   .py    │
  └────┬────┘  └───┬───┘  └──┬──────┘  └────┬─────┘
       │           │          │              │
  IP Camera    embeddings   attendance    attendance
  (RTSP)       .pkl         .csv          .db (SQLite)
```

---

## Project Structure

```
smart_attendance/
├── run.py                     ← Entry point: python run.py
├── config.py                  ← All configuration in one place
├── requirements.txt           ← Python dependencies
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── main.py                ← Flask routes + recognition loop
│   ├── camera.py              ← Thread-safe RTSP/webcam capture
│   ├── recognition.py         ← Face detection, encoding, cosine matching
│   ├── attendance.py          ← Mark attendance, CSV export, unknown faces
│   └── database.py            ← SQLite CRUD operations
│
├── templates/
│   ├── base.html              ← Layout with nav + flash messages
│   ├── dashboard.html         ← Stats, live feed, attendance table
│   ├── register.html          ← Step-by-step face registration
│   └── users.html             ← Registered users list
│
├── static/
│   ├── style.css              ← Dark theme stylesheet
│   └── app.js                 ← Frontend AJAX + status polling
│
└── data/                      ← Auto-created at runtime
    ├── attendance.db
    ├── embeddings.pkl
    ├── attendance.csv
    └── unknown_faces/
```

---

## Prerequisites

- **Python 3.9+**
- **CMake** (required to build `dlib`)
- **C++ build tools** (Visual Studio Build Tools on Windows, `build-essential` on Linux)

---

## Setup — Windows (Development)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd smart_attendance
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install cmake
pip install dlib
pip install -r requirements.txt
```

> **Trouble with dlib?**  
> Ensure you have [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) installed with "Desktop development with C++" workload selected. Then retry `pip install dlib`.

### 4. Configure camera source

Edit `config.py` or set an environment variable:

```bash
# Use local webcam (default)
set CAMERA_SOURCE=0

# Or use an IP camera RTSP stream
set CAMERA_SOURCE=rtsp://admin:password@192.168.1.100:554/stream
```

### 5. Run the application

```bash
python run.py
```

Open your browser at **http://localhost:5000**

---

## Setup — Raspberry Pi 5 (Deployment)

See the full deployment guide: [DEPLOY_RPI.md](DEPLOY_RPI.md)

### Quick Start

```bash
# System dependencies
sudo apt update && sudo apt install -y \
    python3-pip python3-venv cmake \
    libatlas-base-dev libopenblas-dev \
    libjpeg-dev libpng-dev

# Project setup
cd smart_attendance
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure IP camera
export CAMERA_SOURCE="rtsp://admin:password@192.168.1.100:554/stream"

# Run
python run.py
```

---

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `CAMERA_SOURCE` | `0` (webcam) | Webcam index or RTSP URL |
| `FRAME_WIDTH` / `FRAME_HEIGHT` | 640 × 480 | Frame resize dimensions |
| `PROCESS_EVERY_N_FRAMES` | 3 | Skip frames for performance |
| `MAX_FACES_PER_FRAME` | 5 | Max faces processed per frame |
| `FACE_DETECTION_MODEL` | `"hog"` | `"hog"` (CPU) or `"cnn"` (GPU) |
| `COSINE_THRESHOLD` | 0.55 | Similarity threshold (higher = stricter) |
| `REGISTRATION_SAMPLES` | 5 | Face samples captured per registration |
| `DUPLICATE_WINDOW_MINUTES` | 5 | Duplicate prevention window |
| `FLASK_PORT` | 5000 | Web server port |
| `SECRET_KEY` | (default) | Override via `SECRET_KEY` env var |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Dashboard page |
| `/users` | GET | Registered users page |
| `/register` | GET | Registration page |
| `/video_feed` | GET | MJPEG live stream |
| `/download?date=YYYY-MM-DD` | GET | Download attendance CSV |
| `/api/attendance` | GET | JSON attendance data |
| `/api/status` | GET | System status (camera, recognition) |
| `/api/capture_sample` | POST | Capture one face sample |
| `/api/register_user` | POST | Register user with captured samples |

---

## Troubleshooting

### dlib won't install
- **Windows:** Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with C++ workload
- **Linux/RPi:** `sudo apt install cmake build-essential`

### Camera not connecting
- Check `CAMERA_SOURCE` is correct
- For RTSP: verify the URL works in VLC first
- Ensure the camera is on the same network

### Low recognition accuracy
- Increase `REGISTRATION_SAMPLES` (e.g., 8–10)
- Lower `COSINE_THRESHOLD` (e.g., 0.45) — trades accuracy for recall
- Ensure even lighting during registration
- Register faces at the same distance/angle the camera will see them

### High CPU usage
- Increase `PROCESS_EVERY_N_FRAMES` (e.g., 5)
- Reduce `MAX_FACES_PER_FRAME`
- Ensure `FACE_DETECTION_MODEL = "hog"` (not `"cnn"`)

---

## License

MIT
