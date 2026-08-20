#!/bin/bash
# Run OCI ARM Hunter with native macOS caffeinate to prevent Mac from sleeping

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../hunt_arm.log"

echo "Starting OCI ARM Hunter with caffeinate (No Sleep mode)..."
nohup /usr/bin/caffeinate -dimsu python3 -u "$SCRIPT_DIR/hunt_arm.py" >> "$LOG_FILE" 2>&1 &
PID=$!

echo "=================================================="
echo "☕ Hunter started with No-Sleep mode (PID: $PID)"
echo "Mac is prevented from sleeping while hunting."
echo "To view live logs: tail -f hunt_arm.log"
echo "To stop hunter: pkill -f hunt_arm.py"
echo "=================================================="
