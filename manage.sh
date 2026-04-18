#!/bin/bash

# Interactive Controller Script for Smart Attendance

LOG_FILE="app.log"

# Function to check if app is running
is_running() {
    if [ -f "run.pid" ]; then
        PID=$(cat run.pid)
        if kill -0 $PID 2>/dev/null; then
            return 0 # True (running)
        fi
    fi
    return 1 # False (not running)
}

start_app() {
    if is_running; then
        echo "⚠️ Application is already running (PID: $(cat run.pid))."
        return
    fi
    
    echo "Starting application in the background..."
    if [ ! -d "venv" ]; then
        echo "❌ Error: Virtual environment 'venv' not found. Please create it first."
        return
    fi
    
    source venv/bin/activate
    # Run in background and pipe output to app.log
    nohup python -u run.py > $LOG_FILE 2>&1 &
    
    # Save the PID
    echo $! > run.pid
    echo "✅ App started (PID: $!)."
    echo "🌐 Access your dashboard at: http://localhost:5000"
}

stop_app() {
    echo "Stopping application..."
    if [ -f "run.pid" ]; then
        PID=$(cat run.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "✅ Process $PID stopped."
        else
            echo "Process was not running."
        fi
        rm run.pid
    else
        # Fallback if no PID file
        pkill -f "python.*run.py"
        echo "✅ Stopped all run.py processes."
    fi
}

update_camera() {
    echo ""
    echo "Current saved URL: "
    if [ -f "data/camera_url.txt" ]; then
        cat data/camera_url.txt
    else
        echo "(Default / Missing)"
    fi
    echo ""
    read -p "Enter new Camera URL (or '0' for local webcam): " new_url
    
    if [ ! -z "$new_url" ]; then
        mkdir -p data
        echo "$new_url" > data/camera_url.txt
        echo "✅ Camera URL safely updated."
        
        if is_running; then
            echo "⚠️ NOTE: The system is currently running."
            read -p "Would you like to restart it now to apply changes? (y/n): " do_restart
            if [ "$do_restart" = "y" ]; then
                stop_app
                sleep 2
                start_app
            fi
        fi
    else
        echo "❌ No URL provided. Cancelled."
    fi
}

view_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "No logs found yet."
        return
    fi
    echo "Showing live logs. Press [CTRL+C] to exit logs and return to the menu."
    echo "--------------------------------------------------------"
    tail -f $LOG_FILE
}

# ---------------------------------------------------------
# Interactive Menu Loop
# ---------------------------------------------------------

while true; do
    echo ""
    echo "============================================="
    echo "      Smart Attendance Control Panel"
    echo "============================================="
    
    if is_running; then
        echo -e "  Status: \033[32mRUNNING\033[0m (PID: $(cat run.pid))"
    else
        echo -e "  Status: \033[31mSTOPPED\033[0m"
    fi
    
    echo "============================================="
    echo "  1) Start Application"
    echo "  2) Stop Application"
    echo "  3) Restart Application"
    echo "  4) Update Camera Stream URL"
    echo "  5) View Live Logs"
    echo "  0) Exit"
    echo "============================================="
    read -p "Please select an option [0-5]: " choice

    case $choice in
        1)
            start_app
            ;;
        2)
            stop_app
            ;;
        3)
            stop_app
            sleep 2
            start_app
            ;;
        4)
            update_camera
            ;;
        5)
            view_logs
            # Handle Ctrl+C gracefully without killing the script
            trap '' INT
            read -t 1 -n 1
            trap - INT
            ;;
        0)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option. Please try again."
            ;;
    esac
    read -n 1 -s -r -p "Press any key to continue..."
done
