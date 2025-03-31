
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cricket Game Management Telegram Bot
Main entry point for the application
"""

import os
import logging
import signal
import sys
import time
from telegram.ext import Updater
from bot import setup_bot
from db import init_db

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set to DEBUG for more detailed logs
)

logger = logging.getLogger(__name__)

# Global variable to store the updater instance
updater = None

def signal_handler(sig, frame):
    """Handle termination signals to gracefully shut down the bot"""
    global updater
    
    if updater:
        logger.info(f"Received signal {sig}. Shutting down the bot gracefully...")
        # Stop the bot
        updater.stop()
        # Wait a moment to ensure cleanup
        time.sleep(1)
    
    logger.info("Bot has been shut down.")
    sys.exit(0)

def main():
    """Start the bot"""
    global updater
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize the database
    logger.info("Initializing database...")
    init_db()
    
    # Initialize default strategies
    try:
        from db import initialize_default_strategies
        logger.info("Initializing default team strategies...")
        initialize_default_strategies()
    except Exception as e:
        logger.error(f"Error initializing default strategies: {e}")
        
    logger.info("Database initialized successfully")
    
    # Check for environment variables
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        exit(1)
    
    admin_ids = os.environ.get('ADMIN_IDS')
    if not admin_ids:
        logger.warning("ADMIN_IDS environment variable not set - admin commands will not work")
    else:
        logger.info(f"Admin IDs loaded successfully")
    
    # Initialize and start the bot
    try:
        logger.info("Setting up the bot...")
        updater = setup_bot()
        
        # Start the bot's polling with drop_pending_updates=True to prevent conflicts
        logger.info("Starting polling...")
        updater.start_polling(
            drop_pending_updates=True, 
            allowed_updates=['message', 'callback_query', 'chosen_inline_result', 'inline_query'], 
            timeout=30,
            bootstrap_retries=5,
            poll_interval=1.0
        )
        logger.info("Bot started successfully")
        
        # Run the bot until the process receives a termination signal
        updater.idle()
    except Exception as e:
        logger.error(f"Error in bot operation: {e}")
        logger.exception("Detailed error information:")
        # Make sure to clean up when an exception happens
        if updater:
            try:
                updater.stop()
            except:
                pass
        sys.exit(1)

if __name__ == '__main__':
    main()
