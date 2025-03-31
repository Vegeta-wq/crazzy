#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import signal
import sys
import time
import threading
from telegram.ext import Updater
from bot import setup_bot
from db import init_db
from flask import Flask

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Set to DEBUG for more detailed logs
)

logger = logging.getLogger(__name__)

# Flask server to keep Render happy
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Global variable to store the updater instance
updater = None

def signal_handler(sig, frame):
    """Handle termination signals to gracefully shut down the bot"""
    global updater
    if updater:
        logger.info(f"Received signal {sig}. Shutting down the bot gracefully...")
        updater.stop()
        time.sleep(1)
    logger.info("Bot has been shut down.")
    sys.exit(0)

def start_bot():
    """Start the bot"""
    global updater
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Initializing database...")
    init_db()
    
    try:
        from db import initialize_default_strategies
        logger.info("Initializing default team strategies...")
        initialize_default_strategies()
    except Exception as e:
        logger.error(f"Error initializing default strategies: {e}")
        
    logger.info("Database initialized successfully")
    
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        exit(1)
    
    admin_ids = os.environ.get('ADMIN_IDS')
    if not admin_ids:
        logger.warning("ADMIN_IDS environment variable not set - admin commands will not work")
    else:
        logger.info(f"Admin IDs loaded successfully")
    
    try:
        logger.info("Setting up the bot...")
        updater = setup_bot()
        
        logger.info("Starting polling...")
        updater.start_polling(
            drop_pending_updates=True, 
            allowed_updates=['message', 'callback_query', 'chosen_inline_result', 'inline_query'], 
            timeout=30,
            bootstrap_retries=5,
            poll_interval=1.0
        )
        logger.info("Bot started successfully")
        updater.idle()
    except Exception as e:
        logger.error(f"Error in bot operation: {e}")
        logger.exception("Detailed error information:")
        if updater:
            try:
                updater.stop()
            except:
                pass
        sys.exit(1)

if __name__ == '__main__':
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()
    
    # Start Flask server to satisfy Render's web service requirement
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
