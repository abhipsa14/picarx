#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Uninstall script for the "Okay Robot" service
# Run with: sudo bash uninstall.sh
# ═══════════════════════════════════════════════════════════════

set -e

echo "Stopping and disabling okay-robot service..."
systemctl stop okay-robot 2>/dev/null || true
systemctl disable okay-robot 2>/dev/null || true

echo "Removing service file..."
rm -f /etc/systemd/system/okay-robot.service
systemctl daemon-reload

echo "Removing PID file..."
rm -f /var/run/okay-robot.pid

echo ""
echo "Service uninstalled."
echo "Project files at /home/pi/okay-robot/ were NOT removed."
echo "To remove them: rm -rf /home/pi/okay-robot"
