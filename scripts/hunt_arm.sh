#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../hunt_arm.log"

echo "Starting OCI ARM Hunter in background..."
nohup python3 -u "$SCRIPT_DIR/hunt_arm.py" >> "$LOG_FILE" 2>&1 &
PID=$!
echo "Hunter started with PID: $PID"
echo "To view live logs: tail -f hunt_arm.log"
echo "To stop hunter: pkill -f hunt_arm.py"
