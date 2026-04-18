# Deploying to Raspberry Pi 5

Complete guide for deploying the Smart Attendance System on a Raspberry Pi 5 with an IP camera.

---

## Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS (64-bit, Bookworm recommended)
- IP camera accessible via RTSP on the local network
- SSH access or direct terminal access to the Pi

---

## 1. System Dependencies

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3-pip python3-venv python3-dev \
    cmake build-essential \
    libatlas-base-dev libopenblas-dev \
    libjpeg-dev libpng-dev libtiff-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libhdf5-dev libhdf5-serial-dev \
    libffi-dev libssl-dev
```

---

## 2. Project Setup

```bash
# Clone or copy the project
cd /home/pi
git clone <your-repo-url> smart_attendance
cd smart_attendance

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install cmake
pip install dlib        # This may take 10–15 minutes on RPi5
pip install -r requirements.txt
```

> **Note:** Building `dlib` on RPi5 takes time but works natively on the 64-bit OS. If it fails, ensure you have at least 2GB of free RAM (close other applications).

---

## 3. Configure the IP Camera

```bash
# Set RTSP URL (replace with your camera's actual URL)
export CAMERA_SOURCE="rtsp://admin:password@192.168.1.100:554/stream"

# Test the stream first (optional)
# ffplay "$CAMERA_SOURCE"
```

Common RTSP URL formats:
- **Hikvision:** `rtsp://admin:password@IP:554/Streaming/channels/101`
- **Dahua:** `rtsp://admin:password@IP:554/cam/realmonitor?channel=1&subtype=0`
- **Generic:** `rtsp://admin:password@IP:554/stream`

---

## 4. Test Run

```bash
cd /home/pi/smart_attendance
source venv/bin/activate
export CAMERA_SOURCE="rtsp://admin:password@192.168.1.100:554/stream"

python run.py
```

Open a browser on any device on the same network:  
**http://\<raspberry-pi-ip\>:5000**

---

## 5. Auto-Start with systemd

Create a service file so the app starts automatically on boot:

```bash
sudo nano /etc/systemd/system/smart-attendance.service
```

Paste:

```ini
[Unit]
Description=Smart Attendance System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smart_attendance
Environment="CAMERA_SOURCE=rtsp://admin:password@192.168.1.100:554/stream"
Environment="SECRET_KEY=your-production-secret-key-here"
ExecStart=/home/pi/smart_attendance/venv/bin/python /home/pi/smart_attendance/run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable smart-attendance.service
sudo systemctl start smart-attendance.service

# Check status
sudo systemctl status smart-attendance.service

# View logs
journalctl -u smart-attendance.service -f
```

---

## 6. Kiosk Mode (Optional)

Display the dashboard full-screen on a monitor connected to the Pi:

### Install Chromium kiosk dependencies

```bash
sudo apt install -y chromium-browser unclutter
```

### Create kiosk startup script

```bash
nano /home/pi/kiosk.sh
```

Paste:

```bash
#!/bin/bash
# Wait for the attendance server to start
sleep 10

# Hide cursor
unclutter -idle 0.5 -root &

# Launch Chromium in kiosk mode
chromium-browser \
    --noerrdialogs \
    --disable-infobars \
    --kiosk \
    --incognito \
    --disable-translate \
    --no-first-run \
    http://localhost:5000
```

```bash
chmod +x /home/pi/kiosk.sh
```

### Auto-start kiosk on boot

Add to your desktop autostart:

```bash
mkdir -p /home/pi/.config/autostart
nano /home/pi/.config/autostart/kiosk.desktop
```

Paste:

```ini
[Desktop Entry]
Type=Application
Name=Smart Attendance Kiosk
Exec=/home/pi/kiosk.sh
```

---

## 7. Performance Tuning for RPi5

Edit `config.py` for optimal RPi5 performance:

```python
# Process fewer frames to reduce CPU load
PROCESS_EVERY_N_FRAMES = 5

# Limit concurrent faces
MAX_FACES_PER_FRAME = 3

# Smaller frames = faster processing
FRAME_WIDTH = 480
FRAME_HEIGHT = 360

# Always use HOG (CNN is too heavy for RPi)
FACE_DETECTION_MODEL = "hog"
```

### Monitor system resources

```bash
# CPU temperature
vcgencmd measure_temp

# CPU/memory usage
htop
```

---

## 8. Backup & Maintenance

### Backup attendance data

```bash
# Copy data directory
cp -r /home/pi/smart_attendance/data /home/pi/backup_$(date +%Y%m%d)
```

### Clear old unknown face images

```bash
# Delete unknown faces older than 30 days
find /home/pi/smart_attendance/data/unknown_faces -name "*.jpg" -mtime +30 -delete
```

### Update the application

```bash
cd /home/pi/smart_attendance
git pull
sudo systemctl restart smart-attendance.service
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `dlib` build fails | Ensure 2GB+ free RAM; close other apps; check `cmake` is installed |
| Camera stream freezes | Check network stability; reduce frame resolution |
| High CPU (>90%) | Increase `PROCESS_EVERY_N_FRAMES` to 7+; reduce `MAX_FACES_PER_FRAME` |
| Service won't start | Check `journalctl -u smart-attendance.service` for errors |
| Cannot access from other devices | Ensure `FLASK_HOST = "0.0.0.0"` and port 5000 is not firewalled |
