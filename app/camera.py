"""
Smart Attendance System — Camera Capture Layer
================================================
Thread-safe RTSP/webcam frame capture with auto-reconnection.
"""

import cv2
import time
import logging
import threading

import config

logger = logging.getLogger(__name__)


class CameraStream:
    """
    Thread-safe camera capture from RTSP stream or local webcam.

    Usage:
        camera = CameraStream()
        camera.start()
        frame = camera.read()
        camera.stop()
    """

    def __init__(self, source=None):
        self.source = source if source is not None else config.CAMERA_SOURCE
        self.cap = None
        self.frame = None
        self.ret = False
        self.running = False
        self.lock = threading.Lock()
        self._thread = None

    def _connect(self):
        """Establish connection to camera source."""
        if self.cap is not None:
            self.cap.release()

        logger.info(f"Connecting to camera: {self.source}")
        self.cap = cv2.VideoCapture(self.source)

        if isinstance(self.source, str) and "rtsp" in self.source.lower():
            # Optimize RTSP stream buffering
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.cap.isOpened():
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            logger.info("Camera connected successfully")
            return True
        else:
            logger.error("Failed to connect to camera")
            return False

    def _capture_loop(self):
        """Continuously capture frames in a background thread."""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                logger.warning("Camera disconnected. Reconnecting...")
                time.sleep(config.CAMERA_RECONNECT_DELAY)
                self._connect()
                continue

            ret, frame = self.cap.read()

            if not ret:
                logger.warning("Failed to read frame. Reconnecting...")
                time.sleep(config.CAMERA_RECONNECT_DELAY)
                self._connect()
                continue

            # Resize frame for performance
            frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

            with self.lock:
                self.ret = ret
                self.frame = frame

        # Cleanup on exit
        if self.cap is not None:
            self.cap.release()

    def start(self):
        """Start the camera capture thread."""
        if self.running:
            logger.warning("Camera is already running")
            return

        if not self._connect():
            logger.error("Cannot start camera — connection failed")
            return

        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera capture thread started")

    def read(self):
        """
        Read the latest frame (thread-safe).

        Returns:
            tuple: (success: bool, frame: numpy.ndarray or None)
        """
        with self.lock:
            if self.frame is None:
                return False, None
            return self.ret, self.frame.copy()

    def stop(self):
        """Stop the camera capture thread and release resources."""
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self.cap is not None:
            self.cap.release()
        logger.info("Camera stopped")

    def is_running(self):
        """Check if the camera is actively capturing."""
        return self.running and self.cap is not None and self.cap.isOpened()
