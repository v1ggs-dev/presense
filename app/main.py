"""
Smart Attendance System — Flask Application
==============================================
Main entry point. Runs the Flask web server, autonomous
timetable scheduler, and recognition loop.
"""

import os
import cv2
import time
import random
import logging
import threading
from datetime import datetime

from flask import (
    Flask, render_template, Response, request,
    redirect, url_for, flash, jsonify, send_file
)

import config
from app.camera import CameraStream
from app.recognition import (
    load_embeddings, save_embeddings, detect_and_encode,
    recognize_faces, register_face
)
from app.attendance import mark_attendance, save_unknown_face, export_csv
from app.database import (
    init_db, add_user, get_all_users, delete_user,
    start_class, end_class, get_active_class, get_class_details,
    start_sweep, get_sweep_count, get_class_attendance_summary,
    add_schedule, get_schedule, delete_schedule
)

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(format=config.LOG_FORMAT, level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=config.TEMPLATES_DIR,
    static_folder=config.STATIC_DIR
)
app.secret_key = config.SECRET_KEY

# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------
camera = CameraStream()
known_data = {"ids": [], "names": [], "encodings": []}
latest_annotated_frame = None
frame_lock = threading.Lock()
app_running = False

current_sweep_id = None
sweep_lock = threading.Lock()
force_sweep_flag = False
demo_mode_active = False


# ---------------------------------------------------------------------------
# Scheduler & Recognition Threads
# ---------------------------------------------------------------------------

def automation_loop():
    """
    Background thread that autonomously manages class sessions based
    on the timetable and randomly triggers sweeps during active classes.
    """
    global current_sweep_id, force_sweep_flag

    logger.info("Autonomous Timetable & Sweep Scheduler started")
    
    # Track the last time we checked the timetable so we don't spam it
    last_timetable_check = 0
    
    while app_running:
        now = time.time()
        
        # 1. Timetable Check (every 10 seconds)
        if now - last_timetable_check > 10:
            last_timetable_check = now
            current_day = datetime.now().strftime("%A")     # e.g., "Monday"
            current_time = datetime.now().strftime("%H:%M") # e.g., "09:15"
            
            schedules = get_schedule(current_day)
            expected_subject = None
            
            for s in schedules:
                if s['start_time'] <= current_time < s['end_time']:
                    expected_subject = s['subject']
                    break
            
            active_class = get_active_class()
            
            if expected_subject:
                # We should be in this class!
                if not active_class:
                    logger.info(f"Timetable trigger: Starting {expected_subject}")
                    start_class(expected_subject)
                elif active_class['subject'] != expected_subject and active_class['subject'] != "Manual Session":
                    # Transitioning back-to-back classes
                    end_class()
                    logger.info(f"Timetable trigger: Transitioning to {expected_subject}")
                    start_class(expected_subject)
            else:
                # No class scheduled right now
                if active_class and active_class['subject'] != "Manual Session":
                    logger.info("Timetable trigger: Class time ended.")
                    end_class()
        
        # 2. Sweep Logic (only if a class is active)
        active_class = get_active_class()
        if not active_class:
            time.sleep(2)
            continue

        if force_sweep_flag:
            force_sweep_flag = False
            _execute_sweep(active_class['id'])
            continue

        if demo_mode_active:
            sleep_duration = random.randint(5, 12)  # Fast 5-12 seconds
            logger.info(f"DEMO MODE: Next rapid sweep scheduled in ~{sleep_duration} seconds")
        else:
            average_interval = 3600 / max(1, config.SWEEPS_PER_HOUR)
            min_sleep = max(10, int(average_interval * 0.5))
            max_sleep = int(average_interval * 1.5)
            sleep_duration = random.randint(min_sleep, max_sleep)
            logger.info(f"Next automatic sweep scheduled in ~{sleep_duration//60} minutes")
        
        slept = 0
        while slept < sleep_duration:
            if not app_running or not get_active_class():
                break
            if force_sweep_flag:
                break
            time.sleep(2)
            slept += 2
            
        if force_sweep_flag or not get_active_class():
            continue

        _execute_sweep(active_class['id'])

    logger.info("Autonomous Scheduler stopped")


def _execute_sweep(class_id):
    global current_sweep_id
    with sweep_lock:
        current_sweep_id = start_sweep(class_id)
        
    logger.info(f"SWEEP ACTIVE! AI waking up for {config.SWEEP_DURATION_SECONDS} seconds.")
    time.sleep(config.SWEEP_DURATION_SECONDS)
    
    with sweep_lock:
        current_sweep_id = None
    logger.info("SWEEP COMPLETE. AI sleeping.")


def recognition_loop():
    global latest_annotated_frame, known_data

    logger.info("Recognition loop started")
    frame_count = 0
    unknown_cooldown = {}

    while app_running:
        ret, frame = camera.read()

        if not ret or frame is None:
            time.sleep(0.1)
            continue

        display_frame = frame.copy()

        with sweep_lock:
            active_sweep = current_sweep_id

        if active_sweep is not None:
            frame_count += 1
            if frame_count % config.PROCESS_EVERY_N_FRAMES == 0:
                results = recognize_faces(frame, known_data)

                for result in results:
                    top, right, bottom, left = result["bbox"]
                    name = result["name"]
                    confidence = result["confidence"]
                    user_id = result["id"]

                    if name != "Unknown":
                        color = (0, 200, 0)
                        label = f"{name} ({confidence:.0%})"
                        mark_attendance(user_id, name, confidence, active_sweep)
                    else:
                        color = (0, 0, 220)
                        label = f"Unknown ({confidence:.0%})"
                        
                        now = time.time()
                        bbox_key = f"{top}_{left}"
                        if bbox_key not in unknown_cooldown or (now - unknown_cooldown[bbox_key]) > 30:
                            save_unknown_face(frame, result["bbox"])
                            unknown_cooldown[bbox_key] = now

                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                    cv2.rectangle(display_frame, (left, top - 22), (right, top), color, -1)
                    cv2.putText(display_frame, label, (left + 4, top - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        with frame_lock:
            latest_annotated_frame = display_frame
        time.sleep(0.03)

    logger.info("Recognition loop stopped")


def start_app_threads():
    global app_running, known_data
    if app_running: return
    known_data = load_embeddings()
    camera.start()
    app_running = True
    threading.Thread(target=recognition_loop, daemon=True).start()
    threading.Thread(target=automation_loop, daemon=True).start()

def stop_app_threads():
    global app_running
    app_running = False
    camera.stop()

def reload_embeddings():
    global known_data
    known_data = load_embeddings()


def generate_mjpeg():
    while True:
        with frame_lock:
            frame = latest_annotated_frame
        if frame is None:
            time.sleep(0.1)
            continue
        ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret: continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Routes — Dashboard & Classes
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    active_class = get_active_class()
    summary = []
    if active_class:
        summary = get_class_attendance_summary(active_class['id'])
        
    return render_template(
        "dashboard.html",
        active_class=active_class,
        summary=summary,
        refresh_interval=config.DASHBOARD_REFRESH_INTERVAL,
        sweep_duration=config.SWEEP_DURATION_SECONDS
    )

@app.route("/api/start_class", methods=["POST"])
def api_start_class():
    # End any active classes, log a Manual Session
    start_class("Manual Session")
    return jsonify({"success": True})

@app.route("/api/end_class", methods=["POST"])
def api_end_class():
    end_class()
    return jsonify({"success": True})

@app.route("/api/force_sweep", methods=["POST"])
def api_force_sweep():
    global force_sweep_flag
    if not get_active_class(): return jsonify({"success": False, "error": "No active class."})
    with sweep_lock:
        if current_sweep_id: return jsonify({"success": False, "error": "Sweep active."})
    force_sweep_flag = True
    return jsonify({"success": True})

@app.route("/api/toggle_demo_mode", methods=["POST"])
def api_toggle_demo_mode():
    global demo_mode_active
    demo_mode_active = not demo_mode_active
    return jsonify({"success": True, "demo_mode": demo_mode_active})

@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ---------------------------------------------------------------------------
# Routes — Timetable
# ---------------------------------------------------------------------------

@app.route("/timetable")
def timetable():
    schedules = get_schedule()
    return render_template("timetable.html", schedules=schedules)

@app.route("/timetable/add", methods=["POST"])
def timetable_add():
    day = request.form.get("day_of_week")
    subject = request.form.get("subject")
    start = request.form.get("start_time")
    end = request.form.get("end_time")
    
    if start >= end:
        flash("Start time must be before end time", "error")
        return redirect(url_for("timetable"))
        
    add_schedule(day, subject, start, end)
    flash(f"Scheduled {subject} on {day}.", "success")
    return redirect(url_for("timetable"))

@app.route("/timetable/delete/<int:id>", methods=["POST"])
def timetable_delete(id):
    delete_schedule(id)
    flash("Schedule removed.", "success")
    return redirect(url_for("timetable"))


# ---------------------------------------------------------------------------
# Routes — Users & Registration
# ---------------------------------------------------------------------------

@app.route("/users")
def users():
    return render_template("users.html", users=get_all_users())

@app.route("/users/delete/<user_id>", methods=["POST"])
def delete_user_route(user_id):
    delete_user(user_id)
    data = load_embeddings()
    if user_id in data["ids"]:
        idx = data["ids"].index(user_id)
        data["ids"].pop(idx)
        data["names"].pop(idx)
        data["encodings"].pop(idx)
        save_embeddings(data)
    reload_embeddings()
    flash(f"User {user_id} deleted successfully.", "success")
    return redirect(url_for("users"))

registration_samples = {}
registration_lock = threading.Lock()

@app.route("/register")
def register():
    return render_template("register.html", samples_needed=config.REGISTRATION_SAMPLES)

@app.route("/api/capture_sample", methods=["POST"])
def api_capture_sample():
    data = request.get_json() or {}
    session_id = data.get("session_id", "")
    if not session_id: return jsonify({"error": "session_id required"}), 400

    ret, frame = camera.read()
    if not ret or frame is None: return jsonify({"success": False, "error": "Camera not available"})

    import face_recognition
    import numpy as np
    rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
    locations = face_recognition.face_locations(rgb_frame, model=config.FACE_DETECTION_MODEL)
    if not locations: return jsonify({"success": False, "error": "No face detected"})

    with registration_lock:
        if session_id not in registration_samples:
            registration_samples[session_id] = []
        registration_samples[session_id].append(frame.copy())
        count = len(registration_samples[session_id])

    return jsonify({"success": True, "sample_number": count, "total_needed": config.REGISTRATION_SAMPLES})

@app.route("/api/register_user", methods=["POST"])
def api_register_user():
    data = request.get_json() or {}
    name, user_id, session = data.get("name", "").strip(), data.get("user_id", "").strip(), data.get("session_id", "")
    if not name or not user_id or not session: return jsonify({"success": False, "error": "Missing info"}), 400

    with registration_lock:
        samples = registration_samples.pop(session, [])
    if len(samples) < 2: return jsonify({"success": False, "error": "Not enough samples"})

    if register_face(name, user_id, samples):
        add_user(user_id, name)
        reload_embeddings()
        return jsonify({"success": True, "message": f"Registered {name}!"})
    return jsonify({"success": False, "error": "Registration failed"})


# ---------------------------------------------------------------------------
# Data Exports & Status
# ---------------------------------------------------------------------------

@app.route("/reports")
def reports():
    from app.database import get_all_classes
    classes = get_all_classes()
    return render_template("reports.html", classes=classes)

@app.route("/download/<int:class_id>")
def download_csv(class_id):
    c_data = get_class_details(class_id)
    if not c_data: return "Class not found", 404
        
    csv_content = export_csv(class_id)
    safe_subject = c_data['subject'].replace(" ", "_")
    date_str = c_data['start_time'][:10]
    filename = f"attendance_{safe_subject}_{date_str}.csv"
    
    import io
    buffer = io.BytesIO(csv_content.encode("utf-8"))
    buffer.seek(0)
    return send_file(buffer, mimetype="text/csv", as_attachment=True, download_name=filename)


@app.route("/api/status")
def api_status():
    active_class = get_active_class()
    summary = get_class_attendance_summary(active_class['id']) if active_class else []
        
    return jsonify({
        "camera_running": camera.is_running(),
        "recognition_running": True, 
        "sweep_in_progress": current_sweep_id is not None,
        "active_class": active_class is not None,
        "class_id": active_class["id"] if active_class else None,
        "subject": active_class["subject"] if active_class else None,
        "total_sweeps": get_sweep_count(active_class['id']) if active_class else 0,
        "demo_mode": demo_mode_active,
        "summary": summary
    })


def create_app():
    init_db()
    start_app_threads()
    return app

if __name__ == "__main__":
    application = create_app()
    try:
        application.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        stop_app_threads()
