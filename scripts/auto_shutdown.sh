#!/bin/bash

# Only run on scheduler hostname
HOSTNAME=$(hostname)
if [ "$HOSTNAME" != "scheduler" ]; then
    exit 0
fi

# Check if machine has been on for at least 30 minutes
UPTIME_SECONDS=$(awk '{print int($1)}' /proc/uptime)
if [ $UPTIME_SECONDS -lt 1800 ]; then
    exit 0
fi

# Check last access time from access.log
LAST_ACCESS=$(stat -c %Y /opt/workflow_app/jobs_manager/logs/access.log 2>/dev/null || echo 0)
CURRENT_TIME=$(date +%s)
IDLE_TIME=$((CURRENT_TIME - LAST_ACCESS))

# If idle for more than 30 minutes (1800 seconds), schedule shutdown
if [ $IDLE_TIME -gt 1800 ]; then
    /sbin/shutdown -h 5
