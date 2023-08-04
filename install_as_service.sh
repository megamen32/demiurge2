#!/bin/bash

# Use the current directory as default if no argument is provided
DIR=${1:-.}

# Check if the directory exists
if [ ! -d "$DIR" ]; then
    echo "Directory does not exist"
    exit 1
fi

# Check if main.py file exists in the directory
if [ ! -f "$DIR/run.py" ]; then
    echo "run.py does not exist in the directory"
    exit 1
fi

# Check if the venv directory exists
if [ ! -d "$DIR/venv" ]; then
    echo "venv does not exist in the directory"
    exit 1
fi

# Full path to the directory
DIR_PATH=$(realpath $DIR)

# Get the directory name without the path for the service name
DIR_NAME=$(basename $DIR_PATH)

# Create a systemd service file
echo "[Unit]
Description=Telegram bot service for $DIR_NAME
[Service]
ExecStart=$DIR_PATH/venv/bin/python3 $DIR_PATH/run.py
WorkingDirectory=$DIR_PATH
User=$USER
Group=$USER
Restart=always
[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/$DIR_NAME.service

# Reload the systemd daemon
sudo systemctl daemon-reload

# Enable the service
sudo systemctl enable $DIR_NAME

# Start the service
sudo systemctl start $DIR_NAME

echo "Service $DIR_NAME has been created and started"