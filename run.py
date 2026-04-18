"""
Smart Attendance System — Entry Point
=======================================
Run this file to start the application:

    python run.py

The Flask web dashboard will be available at:
    http://localhost:5000
"""

from app.main import create_app
import config
import logging

logging.basicConfig(format=config.LOG_FORMAT, level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = create_app()

    logger.info(f"Starting Smart Attendance System on http://{config.FLASK_HOST}:{config.FLASK_PORT}")

    try:
        app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG,
            threaded=True,
            use_reloader=False  # Avoid duplicate background threads
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        from app.main import stop_app_threads
        stop_app_threads()
