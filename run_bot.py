#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cricket Game Management Telegram Bot
Script to run the bot only (without the Flask web app)
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from telegram.ext import Updater
from bot import setup_bot

# Create logs directory if it doesn't exist
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Configure enhanced logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log')
    ]
)

logger = logging.getLogger(__name__)

def ensure_telegram_token():
    """Ensure the Telegram bot token is available"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        logger.error("Please set the token and try again.")
        sys.exit(1)
    return token

def ensure_admin_ids():
    """Ensure admin IDs are available and parse them"""
    admin_ids_str = os.environ.get('ADMIN_IDS')
    if not admin_ids_str:
        logger.warning("Warning: ADMIN_IDS environment variable is not set.")
        logger.warning("No users will have admin access to the bot.")
        return []
    
    try:
        # Try to parse admin IDs as a comma-separated list of integers
        admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(',')]
        logger.info(f"Admin IDs configured: {admin_ids}")
        return admin_ids
    except ValueError:
        logger.error("Error: ADMIN_IDS must be a comma-separated list of integers.")
        logger.error("Example: 123456789,987654321")
        sys.exit(1)

def main():
    """Start the bot"""
    logger.info("Starting Cricket Game Bot...")
    
    # Ensure required environment variables are set
    ensure_telegram_token()
    ensure_admin_ids()
    
    try:
        # Initialize and start the bot
        updater = setup_bot()
        
        # Start the bot's polling in a blocking way with extended polling interval
        # to avoid hitting Telegram API limits
        updater.start_polling(
            clean=True, 
            allowed_updates=['message', 'callback_query'],
            poll_interval=1.0
        )
        logger.info("Bot started successfully!")
        logger.info("Press Ctrl+C to stop the bot.")
        
        # Run the bot until the user presses Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
        updater.idle()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()