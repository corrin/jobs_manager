#!/bin/bash

# Only run on scheduler hostname
HOSTNAME=$(hostname)
if [ "$HOSTNAME" != "scheduler" ]; then
    echo "Not shutting down because hostname is '$HOSTNAME', not 'scheduler'"
    exit 0
fi

# Check if machine has been on for at least 30 minutes
UPTIME_SECONDS=$(awk '{print int($1)}' /proc/uptime)
if [ $UPTIME_SECONDS -lt 1800 ]; then
    UPTIME_MINUTES=$((UPTIME_SECONDS / 60))
    echo "Not shutting down because machine was recently started ($UPTIME_MINUTES minutes ago, need 30+ minutes)"
    exit 0
fi

# Check last access time from access.log
LAST_ACCESS=$(stat -c %Y /opt/workflow_app/jobs_manager/logs/access.log 2>/dev/null || echo 0)
CURRENT_TIME=$(date +%s)
IDLE_TIME=$((CURRENT_TIME - LAST_ACCESS))
IDLE_MINUTES=$((IDLE_TIME / 60))

# If idle for more than 30 minutes (1800 seconds), schedule shutdown
if [ $IDLE_TIME -gt 1800 ]; then
    echo "Scheduling shutdown - website was last accessed $IDLE_MINUTES minutes ago"
    /sbin/shutdown -h 5
else
    echo "Not shutting down because website was last accessed $IDLE_MINUTES minutes ago (need 30+ minutes idle)"
fi
