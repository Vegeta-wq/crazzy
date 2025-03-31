"""
Utility functions for handling Telegram API rate limits and exceptions
"""
import logging
import time
import random
from typing import Callable, Any, Dict, Optional, Union
from functools import wraps
from telegram.error import RetryAfter, TelegramError, TimedOut, NetworkError

logger = logging.getLogger(__name__)

def handle_telegram_errors(max_retries: int = 5, initial_wait: int = 1, exponential_base: float = 2.0):
    """
    Decorator to handle Telegram errors, especially RetryAfter.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        initial_wait: Initial wait time in seconds (default: 1)
        exponential_base: Base for exponential backoff (default: 2.0)
    
    Returns:
        Decorator function that handles retries with exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            wait_time = initial_wait
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except RetryAfter as e:
                    # Get wait time from the exception and add some randomness
                    wait_seconds = e.retry_after + random.uniform(0.5, 2.0)
                    
                    logger.warning(
                        f"RetryAfter error in {func.__name__}. Waiting {wait_seconds:.2f} seconds. "
                        f"Retry {retries + 1}/{max_retries}"
                    )
                    
                    time.sleep(wait_seconds)
                    retries += 1
                    
                except TimedOut as e:
                    wait_time = initial_wait * (exponential_base ** retries)
                    wait_time += random.uniform(0, 1)  # Add jitter
                    
                    logger.warning(
                        f"TimedOut error in {func.__name__}. Waiting {wait_time:.2f} seconds. "
                        f"Retry {retries + 1}/{max_retries}. Error: {str(e)}"
                    )
                    
                    time.sleep(wait_time)
                    retries += 1
                    
                except NetworkError as e:
                    wait_time = initial_wait * (exponential_base ** retries)
                    wait_time += random.uniform(0, 1)  # Add jitter
                    
                    logger.warning(
                        f"NetworkError in {func.__name__}. Waiting {wait_time:.2f} seconds. "
                        f"Retry {retries + 1}/{max_retries}. Error: {str(e)}"
                    )
                    
                    time.sleep(wait_time)
                    retries += 1
                    
                except TelegramError as e:
                    # For other Telegram errors, log and re-raise
                    logger.error(f"TelegramError in {func.__name__}: {str(e)}")
                    raise
            
            # If we've exhausted all retries
            logger.error(f"Max retries ({max_retries}) reached in {func.__name__}")
            raise Exception(f"Failed after {max_retries} retries due to Telegram API rate limits")
            
        return wrapper
    return decorator

def send_message_safely(bot, chat_id: int, text: str, **kwargs):
    """
    Safely send a message with the bot while handling RetryAfter errors.
    
    Args:
        bot: The Telegram bot instance
        chat_id: Chat ID to send the message to
        text: Text of the message
        **kwargs: Additional arguments to pass to bot.send_message()
    
    Returns:
        The Message object returned by bot.send_message() or None if failed
    """
    @handle_telegram_errors(max_retries=5, initial_wait=1)
    def _send_message():
        return bot.send_message(chat_id=chat_id, text=text, **kwargs)
    
    try:
        return _send_message()
    except Exception as e:
        logger.error(f"Failed to send message after multiple retries: {str(e)}")
        return None

def edit_message_safely(bot, chat_id: int, message_id: int, text: str, **kwargs):
    """
    Safely edit a message with the bot while handling RetryAfter errors.
    
    Args:
        bot: The Telegram bot instance
        chat_id: Chat ID of the message
        message_id: Message ID to edit
        text: New text of the message
        **kwargs: Additional arguments to pass to bot.edit_message_text()
    
    Returns:
        The Message object returned by bot.edit_message_text() or None if failed
    """
    @handle_telegram_errors(max_retries=5, initial_wait=1)
    def _edit_message():
        return bot.edit_message_text(
            chat_id=chat_id, 
            message_id=message_id, 
            text=text, 
            **kwargs
        )
    
    try:
        return _edit_message()
    except Exception as e:
        logger.error(f"Failed to edit message after multiple retries: {str(e)}")
        return None

def answer_callback_safely(bot, callback_query_id: str, **kwargs):
    """
    Safely answer a callback query while handling RetryAfter errors.
    
    Args:
        bot: The Telegram bot instance
        callback_query_id: Callback query ID to answer
        **kwargs: Additional arguments to pass to bot.answer_callback_query()
    
    Returns:
        Boolean success status
    """
    @handle_telegram_errors(max_retries=5, initial_wait=1)
    def _answer_callback():
        return bot.answer_callback_query(callback_query_id=callback_query_id, **kwargs)
    
    try:
        return _answer_callback()
    except Exception as e:
        logger.error(f"Failed to answer callback query after multiple retries: {str(e)}")
        return False