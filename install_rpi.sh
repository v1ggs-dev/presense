#!/bin/bash

# ========================================================
# Smart Attendance - Raspberry Pi 5 Installer 
# ========================================================
# Run this once to install everything needed for the project.

echo "====================================="
echo "  Starting Installer Data Download "
echo "====================================="

# 1. Update system and install system dependencies for Computer Vision
echo "✅ [1/4] Installing System Dependencies (this might take a few minutes)..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    python3-pip python3-venv python3-dev \
    cmake build-essential \
    libatlas-base-dev libopenblas-dev \
    libjpeg-dev libpng-dev libtiff-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libhdf5-dev libhdf5-serial-dev \
    libffi-dev libssl-dev

# 2. Create the Python Virtual Environment
echo ""
echo "✅ [2/4] Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate the venv
source venv/bin/activate

# 3. Install core PIP packages
echo ""
echo "✅ [3/4] Installing Python Requirements..."
pip install --upgrade pip
pip install cmake

echo "⚠️ NOTE: Installing 'dlib' may take 10-15 minutes on a Raspberry Pi. Please be patient!"
pip install dlib

# Install everything else from requirements.txt
pip install -r requirements.txt

# Finish up
echo ""
echo "====================================="
echo "✅ [4/4] Installation Complete!"
echo "====================================="
echo ""
echo "You are ready to go. To start your app, just run:"
echo "  chmod +x manage.sh"
echo "  ./manage.sh start"
echo ""
