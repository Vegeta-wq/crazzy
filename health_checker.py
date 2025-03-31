#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Health checking functionality for the bot
"""

import os
import time
import logging
import threading
from db import health_check_db

logger = logging.getLogger(__name__)

# Dictionary to store health status
_health_status = {
    "bot": {
        "status": "ok",
        "last_check": time.time(),
        "message": "Bot is running"
    },
    "database": {
        "status": "unknown",
        "last_check": 0,
        "message": "Not checked yet"
    }
}

# Lock for thread-safe updates
_status_lock = threading.Lock()


def update_health_status(component, status, message=None):
    """Update health status for a component"""
    with _status_lock:
        _health_status[component] = {
            "status": status,
            "last_check": time.time(),
            "message": message
        }


def check_db_health():
    """Check database health"""
    try:
        db_healthy = health_check_db()
        if db_healthy:
            update_health_status("database", "ok", "Database is accessible")
        else:
            update_health_status("database", "error", "Database check failed")
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        update_health_status("database", "error", f"Exception: {str(e)}")


def check_bot_health():
    """Check bot health (uptime, etc.)"""
    try:
        # Simple uptime check
        update_health_status("bot", "ok", "Bot is running")
    except Exception as e:
        logger.error(f"Bot health check error: {e}")
        update_health_status("bot", "error", f"Exception: {str(e)}")


def check_health():
    """Run health checks and return status"""
    # Check database health
    check_db_health()
    
    # Check bot health
    check_bot_health()
    
    # Return a copy of the health status
    with _status_lock:
        return dict(_health_status)


def start_health_monitoring(interval=300):
    """Start a background thread for periodic health checks"""
    def health_check_thread():
        while True:
            check_health()
            time.sleep(interval)
    
    monitor_thread = threading.Thread(
        target=health_check_thread, 
        daemon=True,
        name="health-monitor"
    )
    monitor_thread.start()
    logger.info(f"Health monitoring started (interval: {interval}s)")
