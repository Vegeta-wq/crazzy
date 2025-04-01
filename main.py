#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import sys
import time
import threading
from telegram.ext import Updater
from bot import setup_bot
from db import init_db
from flask import Flask

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# Flask server for Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# Global variable for updater
updater = None

def start_bot():
    """Start the bot"""
    global updater
    logger.info("Initializing Database...")
    init_db()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        sys.exit(1)

    logger.info("Setting up bot...")
    try:
        updater = setup_bot()
        updater.start_polling()
        logger.info("Bot Started Successfully!")
        updater.idle()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Start Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
