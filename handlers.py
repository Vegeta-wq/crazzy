#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command and conversation handlers for the telegram bot
"""

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, ConversationHandler, CallbackQueryHandler
import db
import utils

# Set up logger
logger = logging.getLogger(__name__)

from db import (
    is_admin, add_player, get_player, search_players, list_all_players, 
    get_player_count, delete_player, health_check_db, get_or_create_user,
    get_user_coins, update_user_coins, add_pack, get_pack, list_packs,
    get_pack_players, open_pack, get_user_players, get_marketplace_listings,
    list_player_for_sale, buy_player, get_base_price_by_tier, calculate_player_value,
    get_market_insights, get_player_price_history,
    # Player stats functions
    get_player_stats, get_user_player_stats, get_leaderboard
)
from utils import format_player_info, format_pack_info, format_user_info, get_tier_emoji
from health_checker import check_health

# Define conversation states - only include states that are actually used
(
    NAME, ROLE, TEAM, BATTING_TYPE, BOWLING_TYPE, 
    BATTING_TIMING, BATTING_TECHNIQUE, BATTING_POWER,
    BOWLING_PACE, BOWLING_VARIATION, BOWLING_ACCURACY,
    MANUAL_OVR_CHOICE, BATTING_OVR, BOWLING_OVR, TOTAL_OVR, 
    PLAYER_IMAGE, TIER, EDITION
) = range(18)

# Define pack conversation states
(
    PACK_NAME, PACK_DESCRIPTION, PACK_PRICE, PACK_MIN_PLAYERS, PACK_MAX_PLAYERS,
    PACK_MIN_OVR, PACK_MAX_OVR, PACK_TIERS, PACK_IMAGE, PACK_ACTIVE
) = range(17, 27)


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    is_user_admin = is_admin(user.id)
    
    welcome_text = (
        f"🏏 *Welcome to Cricket Game Management Bot* 🏏\n\n"
        f"Hello, {user.first_name}! This bot helps manage cricket players for your game.\n\n"
        f"👤 *Your Status:* {'👑 Admin' if is_user_admin else '🧑‍💻 Regular User'}\n\n"
        f"🔍 *What you can do:*\n"
        f"• View player details\n"
        f"• Search for players by name or team\n"
        f"• Browse the player database\n"
        f"• Manage your cricket teams with /teams\n"
        f"• Open player packs to collect players\n"
    )
    
    if is_user_admin:
        welcome_text += (
            f"\n👑 *Admin Features:*\n"
            f"• Add new players\n"
            f"• Manage player attributes\n"
            f"• Check bot health status\n"
        )
    
    welcome_text += (
        f"\nType /help to see all available commands.\n"
        f"Need assistance? Use /help for command details."
    )
    
    update.message.reply_text(welcome_text, parse_mode='Markdown')


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    # Base help text for all users
    help_text = (
        "🏏 <b>Cricket Game Bot Commands</b> 🏏\n\n"
        "📌 <b>General Commands:</b>\n"
        "• /start - Start the bot\n"
        "• /help - Show this help message\n"
        "• /health - Check bot health status\n"
        "• /view &lt;id&gt; - View player details by ID\n"
        "• /search &lt;term&gt; - Search for players by name or team\n"
        "• /list - List all players\n\n"
        "🎮 <b>Game Commands:</b>\n"
        "• /profile - View your profile and stats\n"
        "• /myplayers - View your player collection\n"
        "• /packs - View available player packs\n"
        "• /viewpack &lt;id&gt; - View pack details\n"
        "• /openpack &lt;id&gt; - Open a player pack\n\n"
        "📊 <b>Player Statistics:</b>\n"
        "• /playerstats &lt;id&gt; - View detailed statistics for a specific player\n"
        "• /mystats - View statistics for all your players\n"
        "• /battingleaderboard - View top batsmen by batting average\n"
        "• /bowlingleaderboard - View top bowlers by bowling average\n\n"
        "🏆 <b>Team Management:</b>\n"
        "• /teams - Interactive team management menu\n"
        "• /create_team - Create a new cricket team\n"
        "• /deleteteam &lt;id&gt; - Directly delete a team by ID\n\n"
    )
    
    # Add admin commands if the user is an admin
    if is_admin(update.effective_user.id):
        admin_text = (
            "👑 <b>Admin Commands:</b>\n"
            "• /admin - Check admin status\n"
            "• /adminpanel - Access the comprehensive admin panel\n"
            "• /add - Add a new player to the database\n"
            "• /delete &lt;id&gt; - Delete a player\n"
            "• /addpack - Create a new player pack\n"
            "• /managepacks - Manage all packs\n"
        )
        help_text += admin_text
    
    update.message.reply_text(help_text, parse_mode='HTML')


def admin_command(update: Update, context: CallbackContext) -> None:
    """Check if the user is an admin"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if is_admin(user_id):
        update.message.reply_text(
            f"👑 Hello {user_name}! You have admin privileges.\n\n"
            "You can use the following admin commands:\n"
            "• /add - Add a new player\n"
            "• /delete <id> - Delete a player\n"
            "• /deleteuser <user_id> <type> - Delete user data (type: players/coins/teams/market/all)\n"
            "• /deleteteam <id> - Delete a team directly by ID\n"
            "• /addpack - Create a new player pack\n"
            "• /managepacks - Manage all packs\n"
            "• /adminpanel - Open the comprehensive admin panel\n\n"
            "Type /help for a full list of all available commands."
        )
    else:
        update.message.reply_text(
            f"❌ Sorry {user_name}, you don't have admin privileges.\n"
            "Only authorized admins can add or modify players."
        )


def add_player_start(update: Update, context: CallbackContext) -> int:
    """Start the player addition conversation."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if not is_admin(user_id):
        update.message.reply_text(
            f"❌ Sorry {user_name}, only admins can add players."
        )
        return ConversationHandler.END
    
    # Initialize an empty player in context
    context.user_data['player'] = {}
    
    # Show welcome message with field information
    message = (
        f"🏏 *Adding New Player* 🏏\n\n"
        f"Welcome, {user_name}! Let's add a new player to the database.\n"
        f"You'll need to provide the following information:\n\n"
        f"• Name\n"
        f"• Role (Batsman/Bowler/All-rounder/Wicket-keeper)\n"
        f"• Team\n"
        f"• Batting type (LHB/RHB)\n"
        f"• Bowling type (FAST/SPIN)\n"
        f"• Batting attributes (Timing, Technique, Power)\n"
        f"• Bowling attributes (Pace, Variation, Accuracy)\n"
        f"• Player image (optional)\n"
        f"• Tier (Bronze/Silver/Gold/Platinum/Heroic/Icons)\n\n"
        f"Send /cancel at any time to cancel the operation.\n\n"
        f"Let's begin! *What is the player's name?*"
    )
    
    update.message.reply_text(message, parse_mode='Markdown')
    return NAME


def process_name(update: Update, context: CallbackContext) -> int:
    """Process the player's name."""
    name = update.message.text.strip()
    if not name:
        update.message.reply_text("Name cannot be empty. Please enter a valid name:")
        return NAME
    
    context.user_data['player']['name'] = name
    
    update.message.reply_text(
        f"Name: {name}\n\n"
        "What is the player's role?\n\n"
        "Valid roles:\n"
        "• Batsman\n"
        "• Bowler\n" 
        "• All-rounder\n"
        "• Wicket-keeper"
    )
    return ROLE


def process_role(update: Update, context: CallbackContext) -> int:
    """Process the player's role."""
    role = update.message.text.strip()
    valid_roles = ["Batsman", "Bowler", "All-rounder", "Wicket-keeper"]
    
    if role not in valid_roles:
        update.message.reply_text(
            "Please enter a valid role:\n"
            "• Batsman\n"
            "• Bowler\n"
            "• All-rounder\n"
            "• Wicket-keeper"
        )
        return ROLE
    
    context.user_data['player']['role'] = role
    update.message.reply_text(
        f"Role: {role}\n\n"
        "What team does the player belong to?"
    )
    return TEAM


def process_team(update: Update, context: CallbackContext) -> int:
    """Process the player's team."""
    team = update.message.text.strip()
    if not team:
        update.message.reply_text("Team cannot be empty. Please enter a valid team:")
        return TEAM
    
    context.user_data['player']['team'] = team
    
    # Create inline keyboard for batting type
    keyboard = [
        [
            InlineKeyboardButton("LHB (Left-handed)", callback_data='batting_LHB'),
            InlineKeyboardButton("RHB (Right-handed)", callback_data='batting_RHB')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"Team: {team}\n\n"
        "What is the player's batting type?",
        reply_markup=reply_markup
    )
    return BATTING_TYPE


def process_batting_type(update: Update, context: CallbackContext) -> int:
    """Process the player's batting type."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract batting type from callback data
        if query.data.startswith('batting_'):
            batting_type = query.data.split('_')[1]
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BATTING_TYPE
    else:
        # Handle text input (for backward compatibility)
        batting_type = update.message.text.strip().upper()
        message = update.message
        if batting_type not in ["LHB", "RHB"]:
            update.message.reply_text(
                "Invalid batting type. Please select LHB or RHB:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("LHB (Left-handed)", callback_data='batting_LHB'),
                        InlineKeyboardButton("RHB (Right-handed)", callback_data='batting_RHB')
                    ]
                ])
            )
            return BATTING_TYPE
    
    context.user_data['player']['batting_type'] = batting_type
    
    # Create inline keyboard for bowling type
    keyboard = [
        [
            InlineKeyboardButton("FAST Bowler", callback_data='bowling_FAST'),
            InlineKeyboardButton("SPIN Bowler", callback_data='bowling_SPIN')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Batting Type: {batting_type}\n\n"
            "What is the player's bowling type?",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Batting Type: {batting_type}\n\n"
            "What is the player's bowling type?",
            reply_markup=reply_markup
        )
    
    return BOWLING_TYPE


def process_bowling_type(update: Update, context: CallbackContext) -> int:
    """Process the player's bowling type."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract bowling type from callback data
        if query.data.startswith('bowling_'):
            bowling_type = query.data.split('_')[1]
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BOWLING_TYPE
    else:
        # Handle text input (for backward compatibility)
        bowling_type = update.message.text.strip().upper()
        message = update.message
        if bowling_type not in ["FAST", "SPIN"]:
            update.message.reply_text(
                "Invalid bowling type. Please select FAST or SPIN:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("FAST Bowler", callback_data='bowling_FAST'),
                        InlineKeyboardButton("SPIN Bowler", callback_data='bowling_SPIN')
                    ]
                ])
            )
            return BOWLING_TYPE
    
    context.user_data['player']['bowling_type'] = bowling_type
    
    # Create inline keyboard for ratings
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='timing_50'),
            InlineKeyboardButton("Good (75)", callback_data='timing_75'),
            InlineKeyboardButton("Excellent (90)", callback_data='timing_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Bowling Type: {bowling_type}\n\n"
            "Now let's add batting attributes.\n"
            "Please enter the player's TIMING rating (1-100):",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Bowling Type: {bowling_type}\n\n"
            "Now let's add batting attributes.\n"
            "Please enter the player's TIMING rating (1-100):",
            reply_markup=reply_markup
        )
    
    return BATTING_TIMING


def process_batting_timing(update: Update, context: CallbackContext) -> int:
    """Process the player's batting timing attribute."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract timing from callback data
        if query.data.startswith('timing_'):
            timing = int(query.data.split('_')[1])
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BATTING_TIMING
    else:
        # Handle text input (for backward compatibility)
        try:
            timing = int(update.message.text.strip())
            message = update.message
            if not 1 <= timing <= 100:
                raise ValueError("Rating must be between 1 and 100")
        except ValueError:
            # Create quick selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='timing_50'),
                    InlineKeyboardButton("Good (75)", callback_data='timing_75'),
                    InlineKeyboardButton("Excellent (90)", callback_data='timing_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Please enter a valid number between 1 and 100, or select from options below:",
                reply_markup=reply_markup
            )
            return BATTING_TIMING
    
    context.user_data['player']['batting_timing'] = timing
    
    # Create keyboard for technique rating
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='technique_50'),
            InlineKeyboardButton("Good (75)", callback_data='technique_75'),
            InlineKeyboardButton("Excellent (90)", callback_data='technique_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Batting Timing: {timing}\n\n"
            "Please enter the player's TECHNIQUE rating (1-100):",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Batting Timing: {timing}\n\n"
            "Please enter the player's TECHNIQUE rating (1-100):",
            reply_markup=reply_markup
        )
    
    return BATTING_TECHNIQUE


def process_batting_technique(update: Update, context: CallbackContext) -> int:
    """Process the player's batting technique attribute."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract technique from callback data
        if query.data.startswith('technique_'):
            technique = int(query.data.split('_')[1])
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BATTING_TECHNIQUE
    else:
        # Handle text input (for backward compatibility)
        try:
            technique = int(update.message.text.strip())
            message = update.message
            if not 1 <= technique <= 100:
                raise ValueError("Rating must be between 1 and 100")
        except ValueError:
            # Create quick selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='technique_50'),
                    InlineKeyboardButton("Good (75)", callback_data='technique_75'),
                    InlineKeyboardButton("Excellent (90)", callback_data='technique_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Please enter a valid number between 1 and 100, or select from options below:",
                reply_markup=reply_markup
            )
            return BATTING_TECHNIQUE
    
    context.user_data['player']['batting_technique'] = technique
    
    # Create keyboard for power rating
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='power_50'),
            InlineKeyboardButton("Good (75)", callback_data='power_75'),
            InlineKeyboardButton("Excellent (90)", callback_data='power_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Batting Technique: {technique}\n\n"
            "Please enter the player's POWER rating (1-100):",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Batting Technique: {technique}\n\n"
            "Please enter the player's POWER rating (1-100):",
            reply_markup=reply_markup
        )
    
    return BATTING_POWER


def process_batting_power(update: Update, context: CallbackContext) -> int:
    """Process the player's batting power attribute."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract power from callback data
        if query.data.startswith('power_'):
            power = int(query.data.split('_')[1])
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BATTING_POWER
    else:
        # Handle text input (for backward compatibility)
        try:
            power = int(update.message.text.strip())
            message = update.message
            if not 1 <= power <= 100:
                raise ValueError("Rating must be between 1 and 100")
        except ValueError:
            # Create quick selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='power_50'),
                    InlineKeyboardButton("Good (75)", callback_data='power_75'),
                    InlineKeyboardButton("Excellent (90)", callback_data='power_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Please enter a valid number between 1 and 100, or select from options below:",
                reply_markup=reply_markup
            )
            return BATTING_POWER
    
    context.user_data['player']['batting_power'] = power
    
    # Create keyboard for pace rating
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='pace_50'),
            InlineKeyboardButton("Good (75)", callback_data='pace_75'),
            InlineKeyboardButton("Excellent (90)", callback_data='pace_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Batting Power: {power}\n\n"
            "Now let's add bowling attributes.\n"
            "Please enter the player's PACE rating (1-100):",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Batting Power: {power}\n\n"
            "Now let's add bowling attributes.\n"
            "Please enter the player's PACE rating (1-100):",
            reply_markup=reply_markup
        )
    
    return BOWLING_PACE


def process_bowling_pace(update: Update, context: CallbackContext) -> int:
    """Process the player's bowling pace attribute."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract pace from callback data
        if query.data.startswith('pace_'):
            pace = int(query.data.split('_')[1])
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BOWLING_PACE
    else:
        # Handle text input (for backward compatibility)
        try:
            pace = int(update.message.text.strip())
            message = update.message
            if not 1 <= pace <= 100:
                raise ValueError("Rating must be between 1 and 100")
        except ValueError:
            # Create quick selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='pace_50'),
                    InlineKeyboardButton("Good (75)", callback_data='pace_75'),
                    InlineKeyboardButton("Excellent (90)", callback_data='pace_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Please enter a valid number between 1 and 100, or select from options below:",
                reply_markup=reply_markup
            )
            return BOWLING_PACE
    
    context.user_data['player']['bowling_pace'] = pace
    
    # Create keyboard for variation rating
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='variation_50'),
            InlineKeyboardButton("Good (75)", callback_data='variation_75'),
            InlineKeyboardButton("Excellent (90)", callback_data='variation_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Bowling Pace: {pace}\n\n"
            "Please enter the player's VARIATION rating (1-100):",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Bowling Pace: {pace}\n\n"
            "Please enter the player's VARIATION rating (1-100):",
            reply_markup=reply_markup
        )
    
    return BOWLING_VARIATION


def process_bowling_variation(update: Update, context: CallbackContext) -> int:
    """Process the player's bowling variation attribute."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract variation from callback data
        if query.data.startswith('variation_'):
            variation = int(query.data.split('_')[1])
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BOWLING_VARIATION
    else:
        # Handle text input (for backward compatibility)
        try:
            variation = int(update.message.text.strip())
            message = update.message
            if not 1 <= variation <= 100:
                raise ValueError("Rating must be between 1 and 100")
        except ValueError:
            # Create quick selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='variation_50'),
                    InlineKeyboardButton("Good (75)", callback_data='variation_75'),
                    InlineKeyboardButton("Excellent (90)", callback_data='variation_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Please enter a valid number between 1 and 100, or select from options below:",
                reply_markup=reply_markup
            )
            return BOWLING_VARIATION
    
    context.user_data['player']['bowling_variation'] = variation
    
    # Create keyboard for accuracy rating
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='accuracy_50'),
            InlineKeyboardButton("Good (75)", callback_data='accuracy_75'),
            InlineKeyboardButton("Excellent (90)", callback_data='accuracy_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Bowling Variation: {variation}\n\n"
            "Please enter the player's ACCURACY rating (1-100):",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Bowling Variation: {variation}\n\n"
            "Please enter the player's ACCURACY rating (1-100):",
            reply_markup=reply_markup
        )
    
    return BOWLING_ACCURACY


def process_bowling_accuracy(update: Update, context: CallbackContext) -> int:
    """Process the player's bowling accuracy attribute."""
    # Handle callback query if it's from an inline button
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract accuracy from callback data
        if query.data.startswith('accuracy_'):
            accuracy = int(query.data.split('_')[1])
            message = query.message
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BOWLING_ACCURACY
    else:
        # Handle text input (for backward compatibility)
        try:
            accuracy = int(update.message.text.strip())
            message = update.message
            if not 1 <= accuracy <= 100:
                raise ValueError("Rating must be between 1 and 100")
        except ValueError:
            # Create quick selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='accuracy_50'),
                    InlineKeyboardButton("Good (75)", callback_data='accuracy_75'),
                    InlineKeyboardButton("Excellent (90)", callback_data='accuracy_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "Please enter a valid number between 1 and 100, or select from options below:",
                reply_markup=reply_markup
            )
            return BOWLING_ACCURACY
    
    context.user_data['player']['bowling_accuracy'] = accuracy
    
    # Ask if user wants to input manual OVR values 
    keyboard = [
        [
            InlineKeyboardButton("Calculate automatically", callback_data='auto_ovr'),
            InlineKeyboardButton("Enter manually", callback_data='manual_ovr')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If it's a callback, edit the message, otherwise send a new one
    if update.callback_query:
        query.edit_message_text(
            f"Bowling Accuracy: {accuracy}\n\n"
            f"Would you like to enter OVR (overall rating) values manually or let the system calculate them?",
            reply_markup=reply_markup
        )
    else:
        message.reply_text(
            f"Bowling Accuracy: {accuracy}\n\n"
            f"Would you like to enter OVR (overall rating) values manually or let the system calculate them?",
            reply_markup=reply_markup
        )
    
    return MANUAL_OVR_CHOICE


def process_manual_ovr_choice(update: Update, context: CallbackContext) -> int:
    """Process whether to use manual or automatic OVR values."""
    query = update.callback_query
    query.answer()
    
    choice = query.data
    
    if choice == 'auto_ovr':
        # Calculate OVR values automatically
        from utils import calculate_overall_ratings
        
        batting_attrs = [
            context.user_data['player']['batting_timing'],
            context.user_data['player']['batting_technique'],
            context.user_data['player']['batting_power']
        ]
        
        bowling_attrs = [
            context.user_data['player']['bowling_pace'],
            context.user_data['player']['bowling_variation'],
            context.user_data['player']['bowling_accuracy']
        ]
        
        batting_ovr, bowling_ovr, total_ovr = calculate_overall_ratings(batting_attrs, bowling_attrs)
        
        # Store calculated values
        context.user_data['player']['batting_ovr'] = batting_ovr
        context.user_data['player']['bowling_ovr'] = bowling_ovr
        context.user_data['player']['total_ovr'] = total_ovr
        
        # Show calculated values
        query.edit_message_text(
            f"OVR values calculated automatically:\n\n"
            f"• Batting OVR: {batting_ovr}\n"
            f"• Bowling OVR: {bowling_ovr}\n"
            f"• TOTAL OVR: {total_ovr}\n\n"
            f"Please send the player's image URL or upload an image:"
        )
        return PLAYER_IMAGE
    else:
        # Let user enter manual values
        query.edit_message_text(
            "You've chosen to enter OVR values manually.\n\n"
            "Please enter the player's batting overall rating (1-100):"
        )
        return BATTING_OVR


def process_batting_ovr(update: Update, context: CallbackContext) -> int:
    """Process the player's manual batting OVR value."""
    # Create quick selection buttons for common OVR values
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='batting_ovr_50'),
            InlineKeyboardButton("Good (70)", callback_data='batting_ovr_70')
        ],
        [
            InlineKeyboardButton("Very Good (80)", callback_data='batting_ovr_80'),
            InlineKeyboardButton("Excellent (90)", callback_data='batting_ovr_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        batting_ovr = int(update.message.text.strip())
        if not 1 <= batting_ovr <= 100:
            raise ValueError("Rating must be between 1 and 100")
        
        context.user_data['player']['batting_ovr'] = batting_ovr
        
        update.message.reply_text(
            f"Batting OVR: {batting_ovr}\n\n"
            f"Please enter the player's bowling overall rating (1-100):",
            reply_markup=reply_markup
        )
        return BOWLING_OVR
    except ValueError:
        # If not a callback and not a valid number text
        if not update.callback_query:
            update.message.reply_text(
                "Please enter a valid number between 1 and 100 or select from options below:",
                reply_markup=reply_markup
            )
            return BATTING_OVR
    
    # Handle callback query if it exists
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract OVR from callback data
        if query.data.startswith('batting_ovr_'):
            batting_ovr = int(query.data.split('_')[-1])
            context.user_data['player']['batting_ovr'] = batting_ovr
            
            # Create quick selection buttons for bowling OVR
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='bowling_ovr_50'),
                    InlineKeyboardButton("Good (70)", callback_data='bowling_ovr_70')
                ],
                [
                    InlineKeyboardButton("Very Good (80)", callback_data='bowling_ovr_80'),
                    InlineKeyboardButton("Excellent (90)", callback_data='bowling_ovr_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"Batting OVR: {batting_ovr}\n\n"
                f"Please enter the player's bowling overall rating (1-100):",
                reply_markup=reply_markup
            )
            return BOWLING_OVR
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BATTING_OVR
    
    return BATTING_OVR


def process_bowling_ovr(update: Update, context: CallbackContext) -> int:
    """Process the player's manual bowling OVR value."""
    # Create quick selection buttons for common OVR values
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='bowling_ovr_50'),
            InlineKeyboardButton("Good (70)", callback_data='bowling_ovr_70')
        ],
        [
            InlineKeyboardButton("Very Good (80)", callback_data='bowling_ovr_80'),
            InlineKeyboardButton("Excellent (90)", callback_data='bowling_ovr_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        bowling_ovr = int(update.message.text.strip())
        if not 1 <= bowling_ovr <= 100:
            raise ValueError("Rating must be between 1 and 100")
        
        context.user_data['player']['bowling_ovr'] = bowling_ovr
        
        # Create quick selection buttons for total OVR
        keyboard = [
            [
                InlineKeyboardButton("Average (50)", callback_data='total_ovr_50'),
                InlineKeyboardButton("Good (70)", callback_data='total_ovr_70')
            ],
            [
                InlineKeyboardButton("Very Good (80)", callback_data='total_ovr_80'),
                InlineKeyboardButton("Excellent (90)", callback_data='total_ovr_90')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"Bowling OVR: {bowling_ovr}\n\n"
            f"Finally, please enter the player's total overall rating (1-100):",
            reply_markup=reply_markup
        )
        return TOTAL_OVR
    except ValueError:
        # If not a callback and not a valid number text
        if not update.callback_query:
            update.message.reply_text(
                "Please enter a valid number between 1 and 100 or select from options below:",
                reply_markup=reply_markup
            )
            return BOWLING_OVR
    
    # Handle callback query if it exists
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract OVR from callback data
        if query.data.startswith('bowling_ovr_'):
            bowling_ovr = int(query.data.split('_')[-1])
            context.user_data['player']['bowling_ovr'] = bowling_ovr
            
            # Create quick selection buttons for total OVR
            keyboard = [
                [
                    InlineKeyboardButton("Average (50)", callback_data='total_ovr_50'),
                    InlineKeyboardButton("Good (70)", callback_data='total_ovr_70')
                ],
                [
                    InlineKeyboardButton("Very Good (80)", callback_data='total_ovr_80'),
                    InlineKeyboardButton("Excellent (90)", callback_data='total_ovr_90')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"Bowling OVR: {bowling_ovr}\n\n"
                f"Finally, please enter the player's total overall rating (1-100):",
                reply_markup=reply_markup
            )
            return TOTAL_OVR
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return BOWLING_OVR
    
    return BOWLING_OVR


def process_total_ovr(update: Update, context: CallbackContext) -> int:
    """Process the player's manual total OVR value."""
    # Create quick selection buttons for common OVR values
    keyboard = [
        [
            InlineKeyboardButton("Average (50)", callback_data='total_ovr_50'),
            InlineKeyboardButton("Good (70)", callback_data='total_ovr_70')
        ],
        [
            InlineKeyboardButton("Very Good (80)", callback_data='total_ovr_80'),
            InlineKeyboardButton("Excellent (90)", callback_data='total_ovr_90')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        total_ovr = int(update.message.text.strip())
        if not 1 <= total_ovr <= 100:
            raise ValueError("Rating must be between 1 and 100")
        
        context.user_data['player']['total_ovr'] = total_ovr
        
        update.message.reply_text(
            f"Total OVR: {total_ovr}\n\n"
            f"Please send the player's image URL or upload an image:"
        )
        return PLAYER_IMAGE
    except ValueError:
        # If not a callback and not a valid number text
        if not update.callback_query:
            update.message.reply_text(
                "Please enter a valid number between 1 and 100 or select from options below:",
                reply_markup=reply_markup
            )
            return TOTAL_OVR
    
    # Handle callback query if it exists
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract OVR from callback data
        if query.data.startswith('total_ovr_'):
            total_ovr = int(query.data.split('_')[-1])
            context.user_data['player']['total_ovr'] = total_ovr
            
            query.edit_message_text(
                f"Total OVR: {total_ovr}\n\n"
                f"Please send the player's image URL or upload an image:"
            )
            return PLAYER_IMAGE
        else:
            query.edit_message_text("Invalid selection. Please try again.")
            return TOTAL_OVR
    
    return TOTAL_OVR


def process_player_image(update: Update, context: CallbackContext) -> int:
    """Process the player's image."""
    if update.message.photo:
        # Get the largest photo (last in the list)
        photo = update.message.photo[-1]
        file_id = photo.file_id
        image_url = f"telegram:{file_id}"
        context.user_data['player']['image_url'] = image_url
        update.message.reply_text("✅ Image uploaded successfully!")
    else:
        image_url = update.message.text.strip()
        # Basic URL validation
        if not image_url or not re.match(r'^https?://', image_url):
            context.user_data['player']['image_url'] = ""
            update.message.reply_text("No image URL provided, continuing without an image.")
        else:
            context.user_data['player']['image_url'] = image_url
            update.message.reply_text("✅ Image URL saved!")
    
    # Show a tier selection message with emojis using inline buttons
    keyboard = [
        [
            InlineKeyboardButton("🥉 Bronze", callback_data='tier_Bronze'),
            InlineKeyboardButton("🥈 Silver", callback_data='tier_Silver')
        ],
        [
            InlineKeyboardButton("🥇 Gold", callback_data='tier_Gold'),
            InlineKeyboardButton("💎 Platinum", callback_data='tier_Platinum')
        ],
        [
            InlineKeyboardButton("🏆 Heroic", callback_data='tier_Heroic'),
            InlineKeyboardButton("👑 Icons", callback_data='tier_Icons')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get OVR values to display
    batting_ovr = context.user_data['player'].get('batting_ovr', 0)
    bowling_ovr = context.user_data['player'].get('bowling_ovr', 0)
    total_ovr = context.user_data['player'].get('total_ovr', 0)
    
    # Show stats and tier selection
    message = (
        f"🏏 *Player Stats Summary* 🏏\n\n"
        f"• Batting OVR: {batting_ovr}\n"
        f"• Bowling OVR: {bowling_ovr}\n"
        f"• TOTAL OVR: {total_ovr}\n\n"
        f"Now, please choose the player's tier:"
    )
    
    update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return TIER


def process_tier(update: Update, context: CallbackContext) -> int:
    """Process the player's tier and finalize player creation."""
    from utils import get_tier_emoji
    
    # Check if this is a callback from inline buttons
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract tier from callback data (format: 'tier_Bronze')
        if query.data.startswith('tier_'):
            tier = query.data.split('_')[1]
        else:
            # If somehow we got here with an invalid callback, show error
            query.edit_message_text(
                "❌ Invalid tier selection. Please use the /add command to start over."
            )
            return ConversationHandler.END
    else:
        # Handle input with or without emoji for backward compatibility
        input_text = update.message.text.strip()
        tier_input = input_text.split()[-1] if len(input_text.split()) > 0 else ""
        tier = tier_input.capitalize()
    
    valid_tiers = ["Bronze", "Silver", "Gold", "Platinum", "Heroic", "Icons"]
    
    if tier not in valid_tiers:
        # Create keyboard for tier selection
        keyboard = [
            [
                InlineKeyboardButton("🥉 Bronze", callback_data='tier_Bronze'),
                InlineKeyboardButton("🥈 Silver", callback_data='tier_Silver')
            ],
            [
                InlineKeyboardButton("🥇 Gold", callback_data='tier_Gold'),
                InlineKeyboardButton("💎 Platinum", callback_data='tier_Platinum')
            ],
            [
                InlineKeyboardButton("🏆 Heroic", callback_data='tier_Heroic'),
                InlineKeyboardButton("👑 Icons", callback_data='tier_Icons')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # If this is from a callback, edit the message
        if update.callback_query:
            update.callback_query.edit_message_text(
                "⚠️ Invalid tier selected.\n\nPlease choose a tier:",
                reply_markup=reply_markup
            )
        else:
            update.message.reply_text(
                "⚠️ Invalid tier selected.\n\nPlease choose a tier:",
                reply_markup=reply_markup
            )
        return TIER
    
    # Save the tier and finalize player creation
    context.user_data['player']['tier'] = tier
    
    # Prepare keyboard for edition selection
    keyboard = [
        [
            InlineKeyboardButton("Standard", callback_data='edition_Standard'),
            InlineKeyboardButton("Limited", callback_data='edition_Limited')
        ],
        [
            InlineKeyboardButton("Special", callback_data='edition_Special'),
            InlineKeyboardButton("Seasonal", callback_data='edition_Seasonal')
        ],
        [
            InlineKeyboardButton("Event", callback_data='edition_Event'),
            InlineKeyboardButton("Legend", callback_data='edition_Legend')
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Set up the next prompt for edition
    if update.callback_query:
        update.callback_query.edit_message_text(
            f"Tier selected: {get_tier_emoji(tier)} {tier}\n\n"
            f"Now, select the player's *Edition*:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            f"Tier selected: {get_tier_emoji(tier)} {tier}\n\n"
            f"Now, select the player's *Edition*:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    return EDITION


def process_edition(update: Update, context: CallbackContext) -> int:
    """Process the player's edition and finalize player creation."""
    
    # Check if this is a callback from inline buttons
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Extract edition from callback data (format: 'edition_Standard')
        if query.data.startswith('edition_'):
            edition = query.data.split('_')[1]
        else:
            # If somehow we got here with an invalid callback, show error
            query.edit_message_text(
                "❌ Invalid edition selection. Please use the /add command to start over."
            )
            return ConversationHandler.END
    else:
        # Handle direct text input (fallback)
        input_text = update.message.text.strip()
        edition = input_text.capitalize()
        
        valid_editions = ["Standard", "Limited", "Special", "Seasonal", "Event", "Legend"]
        if edition not in valid_editions:
            # Create keyboard for edition selection
            keyboard = [
                [
                    InlineKeyboardButton("Standard", callback_data='edition_Standard'),
                    InlineKeyboardButton("Limited", callback_data='edition_Limited')
                ],
                [
                    InlineKeyboardButton("Special", callback_data='edition_Special'),
                    InlineKeyboardButton("Seasonal", callback_data='edition_Seasonal')
                ],
                [
                    InlineKeyboardButton("Event", callback_data='edition_Event'),
                    InlineKeyboardButton("Legend", callback_data='edition_Legend')
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                "❌ Invalid edition. Please select from the options below:",
                reply_markup=reply_markup
            )
            return EDITION
    
    # Save the edition to player data
    context.user_data['player']['edition'] = edition
    
    # Send a processing message - handle both normal updates and callback queries
    if update.callback_query:
        update.callback_query.edit_message_text(f"⏳ Processing player data for {edition} edition...")
        # Store the message object locally for later use
        message = update.callback_query.message
    else:
        message = update.message.reply_text(f"⏳ Processing player data for {edition} edition...")
    
    try:
        # Add player to database
        player_id = add_player(context.user_data['player'])
        
        # Get the complete player data
        player_data = get_player(player_id)
        
        # Format the player information
        player_info = format_player_info(player_data)
        
        # Get tier emoji for confirmation message
        tier_emoji = get_tier_emoji(context.user_data['player']['tier'])
        
        # Send confirmation message, using the appropriate message object
        if update.callback_query:
            update.callback_query.message.reply_text(
                f"{tier_emoji} Player added successfully! {tier_emoji}\n\n"
                f"*Player ID: {player_id}*\n"
                f"*Edition: {edition}*\n\n"
                f"{player_info}",
                parse_mode='Markdown'
            )
        else:
            update.message.reply_text(
                f"{tier_emoji} Player added successfully! {tier_emoji}\n\n"
                f"*Player ID: {player_id}*\n"
                f"*Edition: {edition}*\n\n"
                f"{player_info}",
                parse_mode='Markdown'
            )
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error adding player: {e}")
        
        # Send error message, using the appropriate message object
        if update.callback_query:
            update.callback_query.message.reply_text(
                "❌ An error occurred while adding the player.\n"
                "Please check your input and try again with the /add command."
            )
        else:
            update.message.reply_text(
                "❌ An error occurred while adding the player.\n"
                "Please check your input and try again with the /add command."
            )
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel and end the conversation."""
    user_name = update.effective_user.first_name
    
    update.message.reply_text(
        f"❌ *Operation Cancelled* ❌\n\n"
        f"{user_name}, you've cancelled the player addition process.\n"
        f"All data has been cleared.\n\n"
        f"Use /add to start adding a player again, or /help to see other commands.",
        parse_mode='Markdown'
    )
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END


def deleteuser_command(update: Update, context: CallbackContext) -> None:
    """Quick admin command to delete user data without using the admin panel"""
    # Check if user is admin
    admin_id = update.effective_user.id
    if not is_admin(admin_id):
        update.message.reply_text("You are not authorized to use admin commands.")
        return

    # Check if we have the required arguments
    if len(context.args) < 2:
        update.message.reply_text(
            "❌ Usage: /deleteuser [user_id] [players|coins|teams|market|all]"
        )
        return

    try:
        # Parse arguments
        user_id = int(context.args[0])
        data_type = context.args[1].lower()
        
        # Set up delete options
        delete_options = {
            'players': False,
            'coins': False,
            'teams': False,
            'marketplace': False
        }
        
        if data_type == 'all':
            delete_options = {k: True for k in delete_options}
        elif data_type == 'players':
            delete_options['players'] = True
        elif data_type == 'coins':
            delete_options['coins'] = True
        elif data_type == 'teams':
            delete_options['teams'] = True
        elif data_type == 'market':
            delete_options['marketplace'] = True
        else:
            update.message.reply_text(
                "❌ Invalid data type. Use: players, coins, teams, market, or all"
            )
            return
        
        # Execute deletion
        from db import delete_user_data
        success, message = delete_user_data(user_id, delete_options)
        
        if success:
            update.message.reply_text(f"✅ SUCCESS: {message}")
        else:
            update.message.reply_text(f"❌ ERROR: {message}")
            
    except ValueError:
        update.message.reply_text("❌ Invalid user ID. Please provide a valid numeric ID.")
    except Exception as e:
        update.message.reply_text(f"❌ An error occurred: {str(e)}")

def deleteteam_command(update: Update, context: CallbackContext) -> None:
    """Direct command to delete a team by ID"""
    user_id = update.effective_user.id
    
    # Check if a team ID was provided
    if not context.args:
        update.message.reply_text(
            "Usage: /deleteteam [team_id]\n"
            "You can find your team ID by viewing your team details."
        )
        return
    
    try:
        team_id = int(context.args[0])
    except ValueError:
        update.message.reply_text("Invalid team ID. Please provide a valid number.")
        return
    
    # Get team to confirm it exists and belongs to user
    from db import get_team, delete_team

    team = get_team(team_id, user_id)
    
    if not team:
        update.message.reply_text(
            "Team not found or you don't have access to it."
        )
        return
    
    # Delete the team
    success, message = delete_team(team_id, user_id)
    
    if success:
        update.message.reply_text(f"✅ {message}")
    else:
        update.message.reply_text(f"❌ Error deleting team: {message}")


def health_check(update: Update, context: CallbackContext) -> None:
    """Check the health status of the bot and its components."""
    # Show loading message
    loading_msg = update.message.reply_text("🔍 Checking bot health status...")
    
    # Get health status
    health_status = check_health()
    player_count = get_player_count()
    
    # Format health status report with markdown
    status_text = "🏏 *CRICKET BOT HEALTH STATUS* 🏏\n\n"
    status_text += "*System Components:*\n"
    
    all_ok = True
    for component, status in health_status.items():
        is_ok = status["status"] == "ok"
        icon = "✅" if is_ok else "❌"
        component_name = component.replace("_", " ").title()
        
        status_text += f"{icon} *{component_name}*: `{status['status']}`\n"
        
        if status.get("message"):
            status_text += f"   ↳ _{status['message']}_\n"
        
        if not is_ok:
            all_ok = False
    
    # Add database statistics
    status_text += f"\n*Database Statistics:*\n"
    status_text += f"📊 Total Players: `{player_count}`\n"
    
    # Add overall status
    status_text += f"\n*Overall Status:* "
    if all_ok:
        status_text += "✅ All systems operational"
    else:
        status_text += "⚠️ Issues detected"
    
    # Add timestamp
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_text += f"\n\n_Report generated at: {now}_"
    
    # Send the formatted health status
    loading_msg.edit_text(status_text, parse_mode='Markdown')


def test_role_filter(update: Update, context: CallbackContext) -> None:
    """Test command to verify role filtering implementation"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not db.is_admin(user_id):
        update.message.reply_text("This command is only available for admins.")
        return
    
    # Get all players
    all_players = db.list_all_players(limit=1000)
    
    # Count roles
    roles = {}
    for player in all_players:
        role = player['role']
        if role in roles:
            roles[role] += 1
        else:
            roles[role] = 1
    
    # Format message
    message = "🏏 *ROLE DISTRIBUTION* 🏏\n\n"
    for role, count in sorted(roles.items()):
        message += f"*{role}*: {count} players\n"
    
    message += "\n*Filter Testing*\n"
    # Test different role filter matches
    for test_role in ["batsman", "bowler", "all-rounder", "wicket-keeper"]:
        # Count matching players
        matching = [p for p in all_players if p['role'].lower() == test_role.lower()]
        message += f"Filter '{test_role}' matches {len(matching)} players\n"
    
    update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


def view_player(update: Update, context: CallbackContext) -> None:
    """View a player by ID or name."""
    args = context.args
    player = None
    search_term = None
    owner_id = update.effective_user.id
    
    # Check if this is a callback query
    if update.callback_query:
        query = update.callback_query
        
        # Check if the user is trying to access someone else's callback
        if 'user_id' in query.data and str(owner_id) not in query.data:
            query.answer("⛔ Access Denied: You can only interact with your own selections.", show_alert=True)
            return
            
        query.answer()
        
        # Extract player ID from callback data
        try:
            # Format should be "view_player_ID"
            player_id = int(query.data.split('_')[-1])
            player = get_player(player_id)
            # Show loading message
            loading_msg = query.message.reply_text("🔍 Searching for player...")
        except (IndexError, ValueError):
            query.edit_message_text(
                "❌ Invalid player data. Please try again."
            )
            return
    else:
        # No args provided
        if not args:
            update.message.reply_text(
                "❌ Please provide a player ID or name.\n"
                "Usage: `/view <player_id>` or `/view <player_name>`\n\n"
                "Examples:\n"
                "• `/view 1`\n"
                "• `/view Kohli`",
                parse_mode='Markdown'
            )
            return
        
        # Show loading message
        loading_msg = update.message.reply_text("🔍 Searching for player...")
        
        # Check if first arg is a digit (ID search)
        if args[0].isdigit():
            player_id = int(args[0])
            player = get_player(player_id)
            if not player:
                loading_msg.edit_text(f"❌ Player with ID {player_id} not found.")
                return
        else:
            # Search by name
            search_term = " ".join(args)
            players = search_players(search_term)
            
            if not players:
                loading_msg.edit_text(f"❌ No players found matching '{search_term}'.")
                return
                
            if len(players) == 1:
                # Only one player found, use that one
                player = players[0]
            else:
                # Multiple players found, create a selection menu
                keyboard = []
                
                for p in players[:10]:  # Limit to 10 players to avoid huge menus
                    tier_emoji = get_tier_emoji(p['tier'])
                    button_text = f"{tier_emoji} {p['name']} ({p['team']}) - OVR: {p['total_ovr']}"
                    # Add user_id to callback data for ownership control
                    keyboard.append([InlineKeyboardButton(
                        button_text, 
                        callback_data=f"view_player_{owner_id}_{p['id']}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                loading_msg.edit_text(
                    f"📋 *Found {len(players)} players matching '{search_term}'*\n"
                    f"Please select one to view details:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
    
    # At this point, we have a single player to display
    # Format the player information
    player_info = format_player_info(player)
    
    # Get tier emoji for enhanced display
    tier_emoji = get_tier_emoji(player['tier'])
    
    # Create enhanced detailed caption with colored indicators and visual bars
    from utils import get_attribute_color
    
    # Get attribute color indicators
    batting_color = get_attribute_color(player['batting_ovr'])
    bowling_color = get_attribute_color(player['bowling_ovr'])
    total_color = get_attribute_color(player['total_ovr'])
    
    # Create visual rating bars for the most important attributes
    def rating_bar(value, max_length=5):
        if value is None:
            return "░" * max_length
        filled = int((value / 100) * max_length)
        return "▓" * filled + "░" * (max_length - filled)
    
    # Create enhanced detailed caption
    detailed_caption = (
        f"{tier_emoji} *{player['name']}* {tier_emoji}\n"
        f"{'━' * 20}\n\n"
        
        f"📋 *PLAYER INFO:*\n"
        f"🆔 ID: `{player['id']}`\n"
        f"🏏 Role: `{player['role']}`\n"
        f"👥 Team: `{player['team']}`\n"
        f"🏆 Tier: `{player['tier']}`\n\n"
        
        f"📊 *OVERALL RATINGS:*\n"
        f"{batting_color} Batting: `{player['batting_ovr']}` {rating_bar(player['batting_ovr'])}\n"
        f"{bowling_color} Bowling: `{player['bowling_ovr']}` {rating_bar(player['bowling_ovr'])}\n"
        f"{total_color} Total OVR: `{player['total_ovr']}` {rating_bar(player['total_ovr'])}\n\n"
        
        f"⚾ *BATTING STATS:* `{player['batting_type']}`\n"
        f"⏱️ Timing: `{player['batting_timing']}` {rating_bar(player['batting_timing'])}\n"
        f"🎯 Technique: `{player['batting_technique']}` {rating_bar(player['batting_technique'])}\n"
        f"💪 Power: `{player['batting_power']}` {rating_bar(player['batting_power'])}\n\n"
        
        f"🏀 *BOWLING STATS:* `{player['bowling_type']}`\n"
        f"⚡ Pace: `{player['bowling_pace']}` {rating_bar(player['bowling_pace'])}\n"
        f"🎭 Variation: `{player['bowling_variation']}` {rating_bar(player['bowling_variation'])}\n"
        f"🎯 Accuracy: `{player['bowling_accuracy']}` {rating_bar(player['bowling_accuracy'])}"
    )
    
    # No buttons in view player function as requested
    reply_markup = None
    
    # Check if player has an image
    if player.get('image_url'):
        # Send the player image with caption
        try:
            # If it's a Telegram image (starts with "telegram:")
            if player['image_url'].startswith('telegram:'):
                file_id = player['image_url'].replace('telegram:', '')
                loading_msg.delete()
                update.message.reply_photo(
                    photo=file_id,
                    caption=detailed_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            # If it's an external URL
            else:
                loading_msg.delete()
                update.message.reply_photo(
                    photo=player['image_url'],
                    caption=detailed_caption,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        except Exception as e:
            # If there's an error sending the image, fall back to text-only
            logger.error(f"Error sending player image: {e}")
            loading_msg.edit_text(
                f"{tier_emoji} *PLAYER DETAILS* {tier_emoji}\n\n"
                f"{player_info}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    else:
        # No image available, send text-only message
        loading_msg.edit_text(
            f"{tier_emoji} *PLAYER DETAILS* {tier_emoji}\n\n"
            f"{player_info}",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


def search_player(update: Update, context: CallbackContext) -> None:
    """Search for players by name or team."""
    args = context.args
    
    if not args:
        update.message.reply_text(
            "❌ Please provide a search term.\n"
            "Usage: `/search <term>`\n\n"
            "You can search by player name or team name.\n"
            "Examples:\n"
            "• `/search Kohli`\n"
            "• `/search India`",
            parse_mode='Markdown'
        )
        return
    
    search_term = " ".join(args)
    
    # Show searching message
    loading_msg = update.message.reply_text(f"🔍 Searching for players matching '{search_term}'...")
    
    players = search_players(search_term)
    
    if not players:
        loading_msg.edit_text(f"❌ No players found matching '{search_term}'.")
        return
    
    from utils import get_tier_emoji
    
    # No buttons in search player function as requested
    response = f"🏏 *SEARCH RESULTS* 🏏\n\n"
    response += f"Found {len(players)} players matching '{search_term}':\n\n"
    
    # Limit to 10 players for display
    display_players = players[:10]
    
    for i, player in enumerate(display_players, 1):
        tier_emoji = get_tier_emoji(player['tier'])
        response += f"{tier_emoji} *ID: {player['id']}* - {player['name']}\n"
        response += f"   Role: {player['role']}, Team: {player['team']}\n\n"
    
    # Add hint on how to view players
    response += f"To view a player, use the command:\n`/view <player_id>`\n\n"
    
    # If there are more than 10 players, add a note
    if len(players) > 10:
        response += f"*Note:* Showing first 10 of {len(players)} results.\n"
        response += "Try a more specific search term for better results."
    
    loading_msg.edit_text(
        response, 
        parse_mode='Markdown'
    )


def list_players(update: Update, context: CallbackContext) -> None:
    """List all players with pagination."""
    page = 1
    items_per_page = 10
    
    # Check if page argument is provided
    if context.args and context.args[0].isdigit():
        page = int(context.args[0])
    
    # Show loading message
    loading_msg = update.message.reply_text("📋 Loading player list...")
    
    offset = (page - 1) * items_per_page
    players = list_all_players(items_per_page, offset)
    
    if not players:
        if page == 1:
            loading_msg.edit_text("❌ No players found in the database.")
        else:
            loading_msg.edit_text(f"❌ No players found on page {page}.")
        return
    
    total_players = get_player_count()
    total_pages = (total_players + items_per_page - 1) // items_per_page
    
    from utils import get_tier_emoji
    
    response = f"🏏 *PLAYER LIST* 🏏\n"
    response += f"*Page {page} of {total_pages}*\n\n"
    
    for i, player in enumerate(players, 1):
        tier_emoji = get_tier_emoji(player['tier'])
        response += f"{tier_emoji} *ID: {player['id']}* - {player['name']}\n"
        response += f"   Role: {player['role']}, Team: {player['team']}\n"
        
        # Add a separator between players except after the last one
        if i < len(players):
            response += f"\n"
    
    # Add hint on how to view players and navigate pages
    response += f"\n📊 Showing {len(players)} of {total_players} players\n\n"
    response += f"To view a player, use the command:\n`/view <player_id>`\n\n"
    
    if total_pages > 1:
        response += f"To go to another page, use the command:\n`/list <page_number>`"
    
    # Edit message without buttons
    loading_msg.edit_text(
        response, 
        parse_mode='Markdown'
    )


def delete_player_command(update: Update, context: CallbackContext) -> None:
    """Delete a player from the database (admin only)."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        update.message.reply_text(
            "❌ Only admins can delete players."
        )
        return
    
    # Check if an ID was provided
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "❌ Please provide a valid player ID to delete.\nUsage: /delete <player_id>"
        )
        return
    
    player_id = int(context.args[0])
    
    # Get player info before deletion for confirmation
    player = get_player(player_id)
    if not player:
        update.message.reply_text(
            f"❌ Player with ID {player_id} not found."
        )
        return
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, delete", callback_data=f"delete_confirm_{player_id}"),
            InlineKeyboardButton("❌ No, cancel", callback_data="delete_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send confirmation message
    update.message.reply_text(
        f"⚠️ *Confirm Delete* ⚠️\n\n"
        f"You are about to delete player:\n"
        f"*ID:* {player_id}\n"
        f"*Name:* {player['name']}\n"
        f"*Team:* {player['team']}\n\n"
        f"This action cannot be undone. Are you sure?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def delete_player_callback(update: Update, context: CallbackContext) -> None:
    """Handle callbacks for player deletion confirmation."""
    user_id = update.effective_user.id
    query = update.callback_query
    
    # Confirm the callback was processed
    query.answer()
    
    if not is_admin(user_id):
        query.edit_message_text(
            "❌ Only admins can delete players."
        )
        return
    
    # Check if it's a deletion confirmation
    if query.data.startswith("delete_confirm_"):
        try:
            player_id = int(query.data.split("_")[-1])
            
            # Delete the player
            success, message = delete_player(player_id)
            
            if success:
                query.edit_message_text(
                    f"✅ {message}",
                    parse_mode='Markdown'
                )
            else:
                query.edit_message_text(
                    f"❌ Failed to delete player: {message}",
                    parse_mode='Markdown'
                )
                
        except ValueError:
            query.edit_message_text(
                "❌ Invalid player ID format."
            )
    # Deletion canceled
    elif query.data == "delete_cancel":
        query.edit_message_text(
            "🛑 Player deletion canceled."
        )


def user_profile(update: Update, context: CallbackContext) -> None:
    """Show user profile and stats."""
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    # Get or create user
    user = get_or_create_user(user_id, name)
    
    if not user:
        update.message.reply_text(
            "❌ Failed to retrieve user profile."
        )
        return
    
    # Get user's players for stats
    user_players = get_user_players(user_id)
    
    # Enhance user dict with player statistics
    if user_players:
        user['player_count'] = len(user_players)
        
        # Calculate tier distribution
        tier_distribution = {}
        for player in user_players:
            tier = player['tier']
            if tier in tier_distribution:
                tier_distribution[tier] += 1
            else:
                tier_distribution[tier] = 1
                
        user['tier_distribution'] = tier_distribution
    
    # Check if user is admin
    if is_admin(user_id):
        user['is_admin'] = True
    
    # Format user info with enhanced details
    user_info = format_user_info(user, include_players=True)
    
    # Create keyboard for user options with improved styling and additional options
    keyboard = [
        [InlineKeyboardButton("👥 My Players", callback_data=f"myplayers_view_user_id_{user_id}")],
        [InlineKeyboardButton("🎁 Browse Packs", callback_data="packs_view")]
    ]
    
    # Add admin panel button if user is admin
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        user_info,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def add_pack_start(update: Update, context: CallbackContext) -> int:
    """Start the pack creation conversation (admin only)."""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        update.message.reply_text(
            "❌ Only admins can create packs."
        )
        return ConversationHandler.END
    
    # Show welcome message with field information
    message = (
        "📦 *Create New Player Pack* 📦\n\n"
        "Please provide the following information:\n\n"
        "• Name\n"
        "• Description\n"
        "• Price (coins)\n"
        "• Players per pack (min-max)\n"
        "• Player OVR range (min-max)\n"
        "• Available tiers\n"
        "• Pack image (optional)\n\n"
        "Let's begin! *What is the pack name?*"
    )
    
    update.message.reply_text(message, parse_mode='Markdown')
    
    # Initialize context data
    context.user_data['pack'] = {}
    
    return PACK_NAME


def process_pack_name(update: Update, context: CallbackContext) -> int:
    """Process the pack name."""
    name = update.message.text.strip()
    if not name:
        update.message.reply_text("Name cannot be empty. Please enter a valid name:")
        return PACK_NAME
    
    context.user_data['pack']['name'] = name
    
    update.message.reply_text(
        f"Pack Name: {name}\n\n"
        f"Now, please provide a description of this pack (what kind of players it contains):"
    )
    return PACK_DESCRIPTION


def process_pack_description(update: Update, context: CallbackContext) -> int:
    """Process the pack description."""
    description = update.message.text.strip()
    context.user_data['pack']['description'] = description
    
    update.message.reply_text(
        f"Description: {description}\n\n"
        f"How much will this pack cost in coins?"
    )
    return PACK_PRICE


def process_pack_price(update: Update, context: CallbackContext) -> int:
    """Process the pack price."""
    try:
        price = int(update.message.text.strip())
        if price < 0:
            raise ValueError("Price must be a positive number")
        
        context.user_data['pack']['price'] = price
        
        update.message.reply_text(
            f"Price: {price} coins\n\n"
            f"What is the minimum number of players in this pack?"
        )
        return PACK_MIN_PLAYERS
    except ValueError:
        update.message.reply_text(
            "Please enter a valid positive number for the price:"
        )
        return PACK_PRICE


def process_pack_min_players(update: Update, context: CallbackContext) -> int:
    """Process the minimum number of players."""
    try:
        min_players = int(update.message.text.strip())
        if min_players < 1:
            raise ValueError("Minimum players must be at least 1")
        
        context.user_data['pack']['min_players'] = min_players
        
        update.message.reply_text(
            f"Minimum Players: {min_players}\n\n"
            f"What is the maximum number of players in this pack? (must be greater than or equal to {min_players})"
        )
        return PACK_MAX_PLAYERS
    except ValueError:
        update.message.reply_text(
            "Please enter a valid positive number for minimum players:"
        )
        return PACK_MIN_PLAYERS


def process_pack_max_players(update: Update, context: CallbackContext) -> int:
    """Process the maximum number of players."""
    try:
        max_players = int(update.message.text.strip())
        min_players = context.user_data['pack']['min_players']
        
        if max_players < min_players:
            update.message.reply_text(
                f"Maximum players must be at least {min_players}. Please enter a valid number:"
            )
            return PACK_MAX_PLAYERS
        
        context.user_data['pack']['max_players'] = max_players
        
        update.message.reply_text(
            f"Maximum Players: {max_players}\n\n"
            f"What is the minimum OVR (overall rating) for players in this pack? (1-100)"
        )
        return PACK_MIN_OVR
    except ValueError:
        update.message.reply_text(
            "Please enter a valid number for maximum players:"
        )
        return PACK_MAX_PLAYERS


def process_pack_min_ovr(update: Update, context: CallbackContext) -> int:
    """Process the minimum OVR."""
    try:
        min_ovr = int(update.message.text.strip())
        if not 1 <= min_ovr <= 100:
            raise ValueError("OVR must be between 1 and 100")
        
        context.user_data['pack']['min_ovr'] = min_ovr
        
        update.message.reply_text(
            f"Minimum OVR: {min_ovr}\n\n"
            f"What is the maximum OVR for players in this pack? (must be between {min_ovr} and 100)"
        )
        return PACK_MAX_OVR
    except ValueError:
        update.message.reply_text(
            "Please enter a valid number between 1 and 100 for minimum OVR:"
        )
        return PACK_MIN_OVR


def process_pack_max_ovr(update: Update, context: CallbackContext) -> int:
    """Process the maximum OVR."""
    try:
        max_ovr = int(update.message.text.strip())
        min_ovr = context.user_data['pack']['min_ovr']
        
        if not min_ovr <= max_ovr <= 100:
            update.message.reply_text(
                f"Maximum OVR must be between {min_ovr} and 100. Please enter a valid number:"
            )
            return PACK_MAX_OVR
        
        context.user_data['pack']['max_ovr'] = max_ovr
        
        # Show tier options with emojis
        from utils import get_tier_emoji
        
        tiers_message = "Available tiers:\n"
        for tier in ["Bronze", "Silver", "Gold", "Platinum", "Heroic", "Icons"]:
            emoji = get_tier_emoji(tier)
            tiers_message += f"{emoji} {tier}\n"
        
        update.message.reply_text(
            f"Maximum OVR: {max_ovr}\n\n"
            f"Which tiers of players will be available in this pack?\n\n"
            f"{tiers_message}\n"
            f"You can specify multiple tiers separated by commas (e.g., 'Bronze, Silver, Gold')"
        )
        return PACK_TIERS
    except ValueError:
        update.message.reply_text(
            "Please enter a valid number between 1 and 100 for maximum OVR:"
        )
        return PACK_MAX_OVR


def process_pack_tiers(update: Update, context: CallbackContext) -> int:
    """Process the available tiers."""
    from utils import get_tier_emoji
    
    tiers_input = update.message.text.strip()
    tiers = [t.strip().capitalize() for t in tiers_input.split(',')]
    
    valid_tiers = ["Bronze", "Silver", "Gold", "Platinum", "Heroic", "Icons"]
    invalid_tiers = [t for t in tiers if t not in valid_tiers]
    
    if invalid_tiers:
        update.message.reply_text(
            f"Invalid tier(s): {', '.join(invalid_tiers)}\n"
            f"Please enter valid tiers separated by commas:"
        )
        return PACK_TIERS
    
    context.user_data['pack']['tiers'] = tiers
    
    # Format tiers with emojis
    formatted_tiers = [f"{get_tier_emoji(t)} {t}" for t in tiers]
    
    update.message.reply_text(
        f"Tiers: {', '.join(formatted_tiers)}\n\n"
        f"Please send an image URL for the pack, upload an image, or send 'skip' to continue without an image:"
    )
    return PACK_IMAGE


def process_pack_image(update: Update, context: CallbackContext) -> int:
    """Process the pack image."""
    if update.message.photo:
        # Get the largest photo (last in the list)
        photo = update.message.photo[-1]
        file_id = photo.file_id
        image_url = f"telegram:{file_id}"
        context.user_data['pack']['image_url'] = image_url
        update.message.reply_text("✅ Image uploaded successfully!")
    else:
        image_url = update.message.text.strip()
        # Check if user wants to skip
        if image_url.lower() == 'skip':
            context.user_data['pack']['image_url'] = ""
            update.message.reply_text("Skipping image upload.")
        # Basic URL validation
        elif not image_url or not re.match(r'^https?://', image_url):
            context.user_data['pack']['image_url'] = ""
            update.message.reply_text("No valid image URL provided, continuing without an image.")
        else:
            context.user_data['pack']['image_url'] = image_url
            update.message.reply_text("✅ Image URL saved!")
    
    # Add buttons for yes/no selection
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data="pack_active_yes"),
            InlineKeyboardButton("❌ No", callback_data="pack_active_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Ask if the pack should be active
    update.message.reply_text(
        "Should this pack be active immediately?",
        reply_markup=reply_markup
    )
    return PACK_ACTIVE


def process_pack_active(update: Update, context: CallbackContext) -> int:
    """Process whether the pack should be active."""
    # Handle both text input and button callbacks
    if update.callback_query:
        query = update.callback_query
        query.answer()
        response = query.data.split('_')[-1]
        message = query.message
    else:
        response = update.message.text.strip().lower()
        message = update.message
    
    is_active = response in ['yes', 'y', 'true', '1', 'active']
    
    context.user_data['pack']['is_active'] = is_active
    
    # Summarize pack information
    pack_data = context.user_data['pack']
    from utils import format_pack_info
    
    # Set default values for any missing fields
    if 'image_url' not in pack_data:
        pack_data['image_url'] = ""
    
    # Add inline buttons to indicate processing is happening
    if update.callback_query:
        query.edit_message_text(f"⏳ Processing pack data...")
    else:
        message.reply_text(f"⏳ Processing pack data...")
    
    try:
        # Add pack to database
        pack_id = add_pack(pack_data)
        
        # Get the complete pack data
        pack = get_pack(pack_id)
        
        # Format the pack information
        pack_info = format_pack_info(pack)
        
        success_message = (
            f"📦 Pack created successfully! 📦\n\n"
            f"*Pack ID: {pack_id}*\n\n"
            f"{pack_info}\n\n"
            f"Status: {'🟢 Active' if is_active else '🔴 Inactive'}"
        )
        
        # Send the success message as a new message
        if update.callback_query:
            message.reply_text(success_message, parse_mode='Markdown')
        else:
            message.reply_text(success_message, parse_mode='Markdown')
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error adding pack: {e}")
        error_message = (
            "❌ An error occurred while adding the pack.\n"
            "Please check your input and try again with the /addpack command."
        )
        
        if update.callback_query:
            message.reply_text(error_message)
        else:
            message.reply_text(error_message)
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END


def manage_packs(update: Update, context: CallbackContext) -> None:
    """List and manage packs for admins and users."""
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    
    # Handle callback query if it exists
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Check if this is a callback from a different function
        if query.data not in ["packs_view", "packs_list_user", "packs_list_admin"]:
            return
            
        # If admin is requesting admin view
        if query.data == "packs_list_admin" and is_user_admin:
            show_admin_view = True
        else:
            # For regular user view or when non-admin tries admin view
            show_admin_view = False
            
        message = query.message
    else:
        # Regular command
        show_admin_view = is_user_admin
        message = update.message
    
    # Show loading message
    if not update.callback_query:
        loading_msg = message.reply_text("📦 Loading available packs...")
    
    # Get list of packs
    if show_admin_view:
        packs = list_packs(active_only=False)
    else:
        packs = list_packs(active_only=True)
    
    if not packs:
        if update.callback_query:
            message.edit_text(
                "No packs found." + (" Create one with /addpack" if is_user_admin else "")
            )
        else:
            loading_msg.edit_text(
                "No packs found." + (" Create one with /addpack" if is_user_admin else "")
            )
        return
    
    # Format response
    if show_admin_view:
        response = "📦 *Admin: Pack Management* 📦\n\n"
    else:
        response = "📦 *Available Packs* 📦\n\n"
    
    # Create keyboards for each pack
    keyboard = []
    
    for pack in packs:
        status = "✅ Active" if pack['is_active'] else "❌ Inactive"
        
        # Add pack info to response
        if show_admin_view:
            response += f"*ID:* {pack['id']} - {pack['name']} ({status})\n"
        else:
            response += f"*{pack['name']}*\n"
        
        response += f"*Price:* 💰 {pack['price']} coins\n"
        response += f"*Players:* {pack['min_players']}"
        if pack['min_players'] != pack['max_players']:
            response += f"-{pack['max_players']}"
        response += "\n\n"
        
        # Add buttons for this pack
        pack_buttons = []
        user_id = update.effective_user.id
        
        # View button for all users (with user_id for access control)
        pack_buttons.append(
            InlineKeyboardButton(f"🔍 View {pack['name']}", callback_data=f"viewpack_user_id_{user_id}_{pack['id']}")
        )
        
        # Add second row with Open Pack button for active packs
        if pack['is_active']:
            keyboard.append([pack_buttons[0]])  # First row with View button
            keyboard.append([
                InlineKeyboardButton(f"🎁 Open Pack ({pack['price']} 💰)", callback_data=f"openpack_user_id_{user_id}_{pack['id']}")
            ])  # Second row with Open Pack button
        else:
            # Just one row for inactive packs (only viewable)
            keyboard.append([pack_buttons[0]])
    
    # Add admin actions if admin view
    if is_user_admin:
        keyboard.append([
            InlineKeyboardButton("➕ Add New Pack", callback_data="admin_addpack")
        ])
        
        # Add view toggle buttons
        if show_admin_view:
            keyboard.append([
                InlineKeyboardButton("👥 User View", callback_data="packs_list_user")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🔧 Admin View", callback_data="packs_list_admin")
            ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit message based on context
    if update.callback_query:
        try:
            message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
    else:
        loading_msg.edit_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


def view_pack(update: Update, context: CallbackContext) -> None:
    """View pack details."""
    user_id = update.effective_user.id
    
    # Check if this is a callback query
    if update.callback_query:
        query = update.callback_query
        callback_data = query.data
        
        # Check if the user is trying to access someone else's callback
        if 'user_id' in callback_data and str(user_id) not in callback_data:
            query.answer("⛔ Access Denied: You can only interact with your own selections.", show_alert=True)
            return
            
        query.answer()
        
        # Extract pack_id from callback data
        try:
            # Format could be "viewpack_ID" or "viewpack_user_id_USERID_ID"
            data_parts = callback_data.split('_')
            if 'user_id' in callback_data:
                pack_id = int(data_parts[-1])  # Last part is pack ID
            else:
                pack_id = int(data_parts[1])  # Old format without access control
        except (IndexError, ValueError):
            query.edit_message_text(
                "❌ Invalid pack data. Please try again."
            )
            return
        
        message = query.message
    else:
        # Check if pack ID was provided as command argument
        if not context.args or not context.args[0].isdigit():
            update.message.reply_text(
                "❌ Please provide a valid pack ID.\nUsage: /viewpack <pack_id>"
            )
            return
        
        pack_id = int(context.args[0])
        message = update.message
    
    pack = get_pack(pack_id)
    
    if not pack:
        response_text = f"❌ Pack with ID {pack_id} not found."
        
        if update.callback_query:
            query.edit_message_text(response_text)
        else:
            message.reply_text(response_text)
        return
    
    # Format pack info
    pack_info = format_pack_info(pack)
    
    # Add buttons for actions
    keyboard = []
    
    # Check if user is admin
    if is_admin(update.effective_user.id):
        toggle_text = "❌ Deactivate" if pack['is_active'] else "✅ Activate"
        keyboard.append([
            InlineKeyboardButton(toggle_text, callback_data=f"pack_toggle_{pack_id}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"pack_delete_{pack_id}")
        ])
    
    # Add open pack button for all users with price information
    if pack['is_active']:
        keyboard.append([
            InlineKeyboardButton(f"🎁 Open Pack ({pack['price']} coins)", callback_data=f"pack_open_{pack_id}")
        ])
    
    # Add back button to return to packs list
    keyboard.append([
        InlineKeyboardButton("⬅️ Back to Packs", callback_data="packs_view")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # If there is an image, try to send it
    has_sent_image = False
    
    try:
        if pack.get('image_url'):
            if pack['image_url'].startswith('telegram:'):
                file_id = pack['image_url'].replace('telegram:', '')
                if update.callback_query:
                    query.message.reply_photo(
                        photo=file_id,
                        caption=f"📦 *{pack['name']}* 📦\n\n"
                              f"*Price:* 💰 {pack['price']} coins\n"
                              f"*Contains:* {pack['min_players']}-{pack['max_players']} players",
                        parse_mode='Markdown'
                    )
                else:
                    message.reply_photo(
                        photo=file_id,
                        caption=f"📦 *{pack['name']}* 📦\n\n"
                              f"*Price:* 💰 {pack['price']} coins\n"
                              f"*Contains:* {pack['min_players']}-{pack['max_players']} players",
                        parse_mode='Markdown'
                    )
                has_sent_image = True
            elif pack['image_url'].startswith('http'):
                if update.callback_query:
                    query.message.reply_photo(
                        photo=pack['image_url'],
                        caption=f"📦 *{pack['name']}* 📦\n\n"
                              f"*Price:* 💰 {pack['price']} coins\n"
                              f"*Contains:* {pack['min_players']}-{pack['max_players']} players",
                        parse_mode='Markdown'
                    )
                else:
                    message.reply_photo(
                        photo=pack['image_url'],
                        caption=f"📦 *{pack['name']}* 📦\n\n"
                              f"*Price:* 💰 {pack['price']} coins\n"
                              f"*Contains:* {pack['min_players']}-{pack['max_players']} players",
                        parse_mode='Markdown'
                    )
                has_sent_image = True
    except Exception as e:
        logger.error(f"Error sending pack image: {e}")
        # Continue without the image
    
    # Send or edit the text message with pack details
    if update.callback_query:
        query.edit_message_text(
            pack_info,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        message.reply_text(
            pack_info,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


def open_pack_command(update: Update, context: CallbackContext) -> None:
    """Open a pack by ID."""
    user_id = update.effective_user.id
    
    # Handle callback query if it exists
    if update.callback_query:
        query = update.callback_query
        callback_data = query.data
        
        # Check if the user is trying to access someone else's callback
        if 'user_id' in callback_data and str(user_id) not in callback_data:
            query.answer("⛔ Access Denied: You can only interact with your own selections.", show_alert=True)
            return
            
        query.answer()
        
        # Extract pack ID from callback data
        pack_id = int(callback_data.split('_')[-1])
        
        # Create loading message
        loading_msg = query.message.reply_text(
            "🎁 Opening pack... 🎁"
        )
    else:
        # Check if pack ID was provided in command arguments
        if not context.args or not context.args[0].isdigit():
            update.message.reply_text(
                "❌ Please provide a valid pack ID.\nUsage: /openpack <pack_id>"
            )
            return
        
        pack_id = int(context.args[0])
        
        # Create loading message
        loading_msg = update.message.reply_text(
            "🎁 Opening pack... 🎁"
        )
    
    # Get pack details
    pack = get_pack(pack_id)
    
    if not pack:
        loading_msg.edit_text(f"❌ Pack with ID {pack_id} not found.")
        return
    
    if not pack['is_active']:
        loading_msg.edit_text(f"❌ This pack is currently not available.")
        return
    
    # Get user's coins
    user = get_or_create_user(user_id, update.effective_user.first_name)
    
    if user['coins'] < pack['price']:
        loading_msg.edit_text(
            f"❌ You don't have enough coins to open this pack.\n"
            f"Pack price: 💰 {pack['price']} coins\n"
            f"Your balance: 💰 {user['coins']} coins"
        )
        return
    
    # Open the pack
    success, result = open_pack(user_id, pack_id)
    
    if not success:
        loading_msg.edit_text(f"❌ Failed to open pack: {result}")
        return
    
    # Format the result
    pack_name = result['pack_name']
    price = result['price']
    players = result['players']
    
    response = f"🎉 *Pack Opened!* 🎉\n\n"
    response += f"You spent 💰 {price} coins on a {pack_name} pack\n"
    response += f"and received {len(players)} players:\n\n"
    
    for player in players:
        tier_emoji = get_tier_emoji(player['tier'])
        response += f"{tier_emoji} *{player['name']}* ({player['total_ovr']} OVR)\n"
        response += f"   {player['role']} • {player['team']}\n\n"
    
    # Get updated coin balance
    new_balance = get_user_coins(user_id)
    response += f"Your new balance: 💰 {new_balance} coins"
    
    # Add buttons to view your players
    keyboard = [[InlineKeyboardButton("👥 View My Players", callback_data=f"myplayers_view_user_id_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    loading_msg.edit_text(
        response, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


def my_players(update: Update, context: CallbackContext) -> None:
    """Show players owned by the user."""
    user_id = update.effective_user.id
    players = get_user_players(user_id)
    
    # Handle callback query if it exists
    if update.callback_query:
        query = update.callback_query
        callback_data = query.data
        
        # Check if the user is trying to access someone else's callback
        if 'user_id' in callback_data and str(user_id) not in callback_data:
            query.answer("⛔ Access Denied: You can only interact with your own selections.", show_alert=True)
            return
            
        query.answer()
        
        # Check if this is a page navigation request
        if "myplayers_page_" in callback_data:
            # Extract page number from callback data (now with user_id in the format)
            # Format: myplayers_page_user_id_USERID_PAGENUMBER
            page_parts = callback_data.split("_")
            page = int(page_parts[-1])  # Last part should be the page number
        else:
            page = 1
        
        # Set message to edit
        message = query.message
    else:
        # Check if page argument was provided in command
        if context.args and context.args[0].isdigit():
            page = int(context.args[0])
        else:
            page = 1
        
        # Set message to reply to
        message = update.message
    
    # Check if user has any players
    if not players:
        # Need different handling based on callback vs message
        if update.callback_query:
            message.reply_text(
                "You don't have any players in your collection yet.\n"
                "Use /packs to browse available player packs."
            )
        else:
            message.reply_text(
                "You don't have any players in your collection yet.\n"
                "Use /packs to browse available player packs."
            )
        return
    
    items_per_page = 5
    total_players = len(players)
    total_pages = (total_players + items_per_page - 1) // items_per_page
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    
    # Calculate slice for current page
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_players)
    current_page_players = players[start_idx:end_idx]
    
    # Format response
    response = f"👥 *MY PLAYERS* (Page {page}/{total_pages})\n\n"
    
    for player in current_page_players:
        tier_emoji = get_tier_emoji(player['tier'])
        # Add edition info if available
        edition_text = f" | {player['edition']}" if 'edition' in player and player['edition'] else ""
        response += f"{tier_emoji} *{player['name']}* ({player['total_ovr']} OVR){edition_text}\n"
        response += f"   {player['role']} • {player['team']}\n"
        
        # Add stats summary
        response += f"   BAT:{player['batting_ovr']} • BOWL:{player['bowling_ovr']}"
        
        if 'fielding_ovr' in player and player['fielding_ovr']:
            response += f" • FIELD:{player['fielding_ovr']}"
            
        response += "\n\n"
    
    # Add navigation buttons
    keyboard = []
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"myplayers_page_user_id_{user_id}_{page-1}"))
    
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"myplayers_page_user_id_{user_id}_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    # Add back to profile button
    keyboard.append([InlineKeyboardButton("🏠 Back to Profile", callback_data=f"profile_view_user_id_{user_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Different handling for callback vs direct command
    if update.callback_query:
        # Edit the existing message
        try:
            message.edit_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            # If message content hasn't changed, this can cause an error
            logger.error(f"Error editing message: {e}")
            pass
    else:
        # Send a new message
        message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


# Team Management Functions

# States for create_team conversation
CREATE_TEAM_NAME, CREATE_TEAM_DESCRIPTION = range(100, 102)

# Special state for team management
TEAM_MANAGEMENT = 200
TEAM_VIEW = 201
TEAM_EDIT = 202
TEAM_ADD_PLAYER = 203
PLAYER_POSITION = 204

def teams_menu(update: Update, context: CallbackContext) -> None:
    """Show the main teams menu with options."""
    user_id = update.effective_user.id
    
    # Get user's teams
    teams = db.get_user_teams(user_id)
    
    # Create keyboard for teams menu
    keyboard = [
        [InlineKeyboardButton("➕ Create New Team", callback_data="team_create")]
    ]
    
    # If user has teams, add option to view them
    if teams:
        keyboard.append([InlineKeyboardButton("🏏 View My Teams", callback_data="team_list")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "🏏 *TEAM MANAGEMENT* 🏏\n\n"
        "Manage your cricket teams and players here.\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def teams_callback_handler(update: Update, context: CallbackContext) -> int:
    """Handle all team-related callbacks."""
    query = update.callback_query
    # In python-telegram-bot v13.15, query.answer() is not awaitable
    query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # Handle different callback actions
    if data == "team_create":
        # Instead of trying to go into a conversation within the callback,
        # we'll instruct the user to use the /create_team command
        query.edit_message_text(
            "To create a new team, please use the /create_team command.\n\n"
            "I'll now exit this menu. Please send /create_team to start creating your team."
        )
        return ConversationHandler.END
        
    elif data == "team_list":
        # Show user's teams with buttons for each
        teams = db.get_user_teams(user_id)
        keyboard = []
        
        for team in teams:
            team_button = [InlineKeyboardButton(
                f"{team['name']} ({team['player_count']} players)",
                callback_data=f"view_team_{team['id']}"
            )]
            keyboard.append(team_button)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« Back to Teams Menu", callback_data="back_to_team_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🏏 *YOUR CRICKET TEAMS* 🏏\n\n"
            "Select a team to view or manage:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return TEAM_MANAGEMENT
        
    elif data.startswith("view_team_"):
        # View specific team details
        team_id = int(data.split("_")[-1])
        team = db.get_team(team_id, user_id)
        
        if not team:
            query.edit_message_text(
                "Team not found or you don't have access to it.\n\n"
                "Press /teams to return to the teams menu."
            )
            return ConversationHandler.END
        
        # Get role counts
        role_counts = team.get('role_counts', {})
        
        # Calculate team average OVR
        total_ovr = 0
        player_count = len(team['players'])
        if player_count > 0:
            for player in team['players']:
                total_ovr += player['total_ovr']
            avg_ovr = round(total_ovr / player_count, 1)
        else:
            avg_ovr = 0
            
        # Create team details message
        message = f"🏏 *TEAM: {team['name']}* 🏏\n\n"
        message += f"Description: {team['description']}\n"
        message += f"Total Players: {len(team['players'])}/11\n"
        message += f"Average OVR: {avg_ovr}\n\n"
        
        # Add team composition breakdown
        message += "*Team Composition:*\n"
        message += f"🧤 *Wicket Keepers*: {role_counts.get('wicket-keeper', 0)}/1-2\n"
        message += f"🏏 *Batsmen*: {role_counts.get('batsman', 0)}/4-6\n"
        message += f"🎯 *Bowlers*: {role_counts.get('bowler', 0)}/4-6\n"
        message += f"⚡ *All-rounders*: {role_counts.get('all-rounder', 0)}/1-2\n\n"
        
        if team['players']:
            message += "*Players in this team:*\n"
            for i, player in enumerate(team['players'], start=1):
                position = f"Position {player['position']}" if player['position'] is not None else "No position"
                emoji = utils.get_tier_emoji(player['tier'])
                # Add edition info if available
                edition_text = f" | {player['edition']}" if 'edition' in player and player['edition'] else ""
                message += f"{i}. {emoji} *{player['name']}* ({player['total_ovr']} OVR){edition_text}\n"
                message += f"   Role: {player['role']} - {position}\n"
        else:
            message += "No players in this team yet.\n"
            message += "*Add players by role using the buttons below.*\n"
        
        # Create action buttons for the team
        keyboard = []
        
        # Add role-specific player buttons
        add_batsman = [InlineKeyboardButton("➕ Add Batsman", callback_data=f"filter_batsman_{team_id}")]
        add_bowler = [InlineKeyboardButton("➕ Add Bowler", callback_data=f"filter_bowler_{team_id}")]
        add_keeper = [InlineKeyboardButton("➕ Add Wicket-keeper", callback_data=f"filter_wicket-keeper_{team_id}")]
        add_allrounder = [InlineKeyboardButton("➕ Add All-rounder", callback_data=f"filter_all-rounder_{team_id}")]
        
        # Add role-specific player buttons based on team needs
        role_buttons = []
        
        # First priority: wicket-keeper
        if role_counts.get('wicket-keeper', 0) < 1:
            role_buttons.append(add_keeper)
        # Second priority: all-rounders
        if role_counts.get('all-rounder', 0) < 1:
            role_buttons.append(add_allrounder)
        # Third priority: missing core roles (batsmen and bowlers)
        if role_counts.get('batsman', 0) < 4:
            role_buttons.append(add_batsman)
        if role_counts.get('bowler', 0) < 4:
            role_buttons.append(add_bowler)
        
        # If we have all core roles but can still add players
        if len(team['players']) < 11 and not role_buttons:
            # Add any roles that are below max
            if role_counts.get('wicket-keeper', 0) < 2:
                role_buttons.append(add_keeper)
            if role_counts.get('all-rounder', 0) < 2:
                role_buttons.append(add_allrounder)
            if role_counts.get('batsman', 0) < 6:
                role_buttons.append(add_batsman)
            if role_counts.get('bowler', 0) < 6:
                role_buttons.append(add_bowler)
        
        # If no specific roles needed, show generic add player button
        if len(team['players']) < 11 and not role_buttons:
            keyboard.append([InlineKeyboardButton("➕ Add Player", callback_data=f"add_player_{team_id}")])
        else:
            # Add recommended roles if team is not full
            if len(team['players']) < 11:
                keyboard.extend(role_buttons)
                keyboard.append([InlineKeyboardButton("➕ Add Any Player", callback_data=f"add_player_{team_id}")])
            
        # Team management buttons
        management_buttons = []
        if team['players']:
            management_buttons.append(InlineKeyboardButton("➖ Remove Player", callback_data=f"remove_player_{team_id}"))
        management_buttons.append(InlineKeyboardButton("✏️ Edit Team", callback_data=f"edit_team_{team_id}"))
        management_buttons.append(InlineKeyboardButton("❌ Delete Team", callback_data=f"delete_team_{team_id}"))
        
        # Split management buttons into two rows
        if len(management_buttons) > 2:
            keyboard.append(management_buttons[:2])
            keyboard.append(management_buttons[2:])
        else:
            keyboard.append(management_buttons)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« Back to Teams List", callback_data="team_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return TEAM_VIEW
        
    elif data.startswith("add_player_"):
        # Parse team_id and page number if present
        parts = data.split("_")
        team_id = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        
        # Store team_id in context for later use
        context.user_data['current_team_id'] = team_id
        
        # Get user's players
        user_players = db.get_user_players(user_id)
        
        if not user_players:
            # No players available
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "You don't have any players to add to your team.\n\n"
                "Open some packs to get players first!",
                reply_markup=reply_markup
            )
            return TEAM_VIEW
        
        # Get current team to check which players are already in it
        team = db.get_team(team_id, user_id)
        
        # First check if the team exists and belongs to the user
        if not team:
            keyboard = [[InlineKeyboardButton("« Back to Teams Menu", callback_data="team_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "Team not found or you don't have access to it.\n\n"
                "Please select another team.",
                reply_markup=reply_markup
            )
            return TEAM_MANAGEMENT
        
        current_player_ids = [p['id'] for p in team['players']] if team['players'] else []
        
        # Filter out players already in the team
        available_players = [p for p in user_players if p['id'] not in current_player_ids]
        
        if not available_players:
            # All players are already in the team
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "All your players are already in this team!",
                reply_markup=reply_markup
            )
            return TEAM_VIEW
        
        # Check if there's an active role filter
        role_filter = context.user_data.get('player_filter')
        if role_filter:
            # Apply role filter
            available_players = [p for p in available_players if p['role'].lower() == role_filter.lower()]
            # Clear filter after applying
            context.user_data.pop('player_filter', None)
            
            # If no players match the filter
            if not available_players:
                keyboard = [[InlineKeyboardButton("« Back to Player Selection", callback_data=f"add_player_{team_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    f"No {role_filter.title()} players available to add to this team.\n\n"
                    f"Try another filter or go back to view all players.",
                    reply_markup=reply_markup
                )
                return TEAM_ADD_PLAYER
        
        # Sort players by tier and OVR
        available_players.sort(key=lambda p: (-["bronze", "silver", "gold", "platinum", "heroic", "icons"].index(p['tier'].lower()), -p['total_ovr']))
        
        # Implement pagination - 5 players per page
        items_per_page = 5
        total_pages = (len(available_players) + items_per_page - 1) // items_per_page
        
        # Validate page number
        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1
        
        # Get players for current page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(available_players))
        current_page_players = available_players[start_idx:end_idx]
        
        # Create keyboard with available players for current page
        keyboard = []
        
        for player in current_page_players:
            emoji = utils.get_tier_emoji(player['tier'])
            # Add edition info if available
            edition_text = f" | {player['edition']}" if 'edition' in player and player['edition'] else ""
            player_button = [InlineKeyboardButton(
                f"{emoji} {player['name']} ({player['total_ovr']} OVR){edition_text}",
                callback_data=f"select_player_{player['id']}"
            )]
            keyboard.append(player_button)
        
        # Add pagination navigation if needed
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("« Previous", callback_data=f"add_player_{team_id}_{page-1}"))
        
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("Next »", callback_data=f"add_player_{team_id}_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Add filter options by player role
        filter_buttons = []
        
        # First row of filters - Batsmen and Bowlers
        filter_row1 = [
            InlineKeyboardButton("🏏 Batsmen", callback_data=f"filter_batsman_{team_id}"),
            InlineKeyboardButton("🎯 Bowlers", callback_data=f"filter_bowler_{team_id}")
        ]
        
        # Second row of filters - All-rounders and Wicket Keepers
        filter_row2 = [
            InlineKeyboardButton("⚡ All-rounders", callback_data=f"filter_all-rounder_{team_id}"),
            InlineKeyboardButton("🧤 Wicket Keepers", callback_data=f"filter_wicket-keeper_{team_id}")
        ]
        
        # Third row with reset filter
        filter_row3 = [
            InlineKeyboardButton("👥 All Roles", callback_data=f"add_player_{team_id}")
        ]
        
        keyboard.append(filter_row1)
        keyboard.append(filter_row2)
        keyboard.append(filter_row3)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")])
        
        # Prepare message with filter info if applicable
        filter_info = f"Showing only {role_filter.upper()} players\n" if role_filter else ""
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"Select a player to add to your team (Page {page+1}/{total_pages}):\n\n"
            f"{filter_info}Showing players {start_idx+1}-{end_idx} of {len(available_players)}",
            reply_markup=reply_markup
        )
        return TEAM_ADD_PLAYER
        
    elif data.startswith("select_player_"):
        # User selected a player to add to the team
        player_id = int(data.split("_")[-1])
        
        # Get the team_id from context or from previous callback data in TEAM_ADD_PLAYER state
        team_id = context.user_data.get('current_team_id')
        
        # If team_id not found in context, try to retrieve from recent history
        if not team_id and 'add_player_team_id' in context.user_data:
            team_id = context.user_data.get('add_player_team_id')
            
        # If still not found, check if team exists
        if not team_id:
            # Inform user and return to teams list
            keyboard = [[InlineKeyboardButton("« Back to Teams List", callback_data="team_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "Error: Could not determine which team to add the player to.\n\n"
                "Please try selecting a team again.",
                reply_markup=reply_markup
            )
            return TEAM_MANAGEMENT
        
        # Store player_id in context for later use
        context.user_data['current_player_id'] = player_id
        
        # Ask for position (optional)
        keyboard = [
            [
                InlineKeyboardButton("1", callback_data="position_1"),
                InlineKeyboardButton("2", callback_data="position_2"),
                InlineKeyboardButton("3", callback_data="position_3"),
                InlineKeyboardButton("4", callback_data="position_4")
            ],
            [
                InlineKeyboardButton("5", callback_data="position_5"),
                InlineKeyboardButton("6", callback_data="position_6"),
                InlineKeyboardButton("7", callback_data="position_7"),
                InlineKeyboardButton("8", callback_data="position_8")
            ],
            [
                InlineKeyboardButton("9", callback_data="position_9"),
                InlineKeyboardButton("10", callback_data="position_10"),
                InlineKeyboardButton("11", callback_data="position_11"),
                InlineKeyboardButton("No Position", callback_data="position_none")
            ],
            [InlineKeyboardButton("« Cancel", callback_data=f"view_team_{team_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get player name
        player = db.get_player(player_id)
        player_name = player['name'] if player else "Selected player"
        
        query.edit_message_text(
            f"Please select a position for *{player_name}* in your team:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return PLAYER_POSITION
        
    elif data.startswith("filter_"):
        # Handle filtering of players by role
        parts = data.split("_")
        role = parts[1]
        team_id = int(parts[2])
        
        # Store filter in context
        context.user_data['player_filter'] = role
        context.user_data['current_team_id'] = team_id
        
        # Get user's players
        user_players = db.get_user_players(user_id)
        
        if not user_players:
            # No players available
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "You don't have any players to add to your team.\n\n"
                "Open some packs to get players first!",
                reply_markup=reply_markup
            )
            return TEAM_VIEW
        
        # Get current team to check which players are already in it
        team = db.get_team(team_id, user_id)
        
        # First check if the team exists and belongs to the user
        if not team:
            keyboard = [[InlineKeyboardButton("« Back to Teams Menu", callback_data="team_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "Team not found or you don't have access to it.\n\n"
                "Please select another team.",
                reply_markup=reply_markup
            )
            return TEAM_MANAGEMENT
        
        current_player_ids = [p['id'] for p in team['players']] if team['players'] else []
        
        # Filter out players already in the team
        available_players = [p for p in user_players if p['id'] not in current_player_ids]
        
        if not available_players:
            # All players are already in the team
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "All your players are already in this team!",
                reply_markup=reply_markup
            )
            return TEAM_VIEW
        
        # Apply role filter
        available_players = [p for p in available_players if p['role'].lower() == role.lower()]
        
        # If no players match the filter
        if not available_players:
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"No {role.title()} players available to add to this team.\n\n"
                f"Try another filter or go back to view all players.",
                reply_markup=reply_markup
            )
            return TEAM_VIEW
        
        # Sort players by tier and OVR
        available_players.sort(key=lambda p: (-["bronze", "silver", "gold", "platinum", "heroic", "icons"].index(p['tier'].lower() if p['tier'].lower() in ["bronze", "silver", "gold", "platinum", "heroic", "icons"] else "bronze"), -p['total_ovr']))
        
        # Implement pagination - 5 players per page
        page = 0
        items_per_page = 5
        total_pages = (len(available_players) + items_per_page - 1) // items_per_page
        
        # Get players for current page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(available_players))
        current_page_players = available_players[start_idx:end_idx]
        
        # Create keyboard with available players for current page
        keyboard = []
        
        for player in current_page_players:
            # Add edition info if available
            edition_text = f" | {player['edition']}" if 'edition' in player and player['edition'] else ""
            emoji = utils.get_tier_emoji(player['tier'])
            player_button = [InlineKeyboardButton(
                f"{emoji} {player['name']} ({player['total_ovr']} OVR){edition_text}",
                callback_data=f"select_player_{player['id']}"
            )]
            keyboard.append(player_button)
        
        # Add pagination navigation if needed
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("« Previous", callback_data=f"add_player_{team_id}_{page-1}"))
        
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("Next »", callback_data=f"add_player_{team_id}_{page+1}"))
        
        if pagination_buttons:
            keyboard.append(pagination_buttons)
        
        # Add filter options by player role
        filter_buttons = []
        
        # First row of filters - Batsmen and Bowlers
        filter_row1 = [
            InlineKeyboardButton("🏏 Batsmen", callback_data=f"filter_batsman_{team_id}"),
            InlineKeyboardButton("🎯 Bowlers", callback_data=f"filter_bowler_{team_id}")
        ]
        
        # Second row of filters - All-rounders and Wicket Keepers
        filter_row2 = [
            InlineKeyboardButton("⚡ All-rounders", callback_data=f"filter_all-rounder_{team_id}"),
            InlineKeyboardButton("🧤 Wicket Keepers", callback_data=f"filter_wicket-keeper_{team_id}")
        ]
        
        # Third row with reset filter
        filter_row3 = [
            InlineKeyboardButton("👥 All Roles", callback_data=f"add_player_{team_id}")
        ]
        
        keyboard.append(filter_row1)
        keyboard.append(filter_row2)
        keyboard.append(filter_row3)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"Select a {role.title()} to add to your team (Page 1/{total_pages}):\n\n"
            f"Showing players {start_idx+1}-{end_idx} of {len(available_players)}",
            reply_markup=reply_markup
        )
        return TEAM_ADD_PLAYER
    
    elif data.startswith("position_"):
        # User selected a position for the player
        position_str = data.split("_")[-1]
        position = None if position_str == "none" else int(position_str)
        
        # Get team_id from context or from previous entries
        team_id = context.user_data.get('current_team_id')
        if not team_id and 'add_player_team_id' in context.user_data:
            team_id = context.user_data.get('add_player_team_id')
            
        player_id = context.user_data.get('current_player_id')
        
        if not team_id or not player_id:
            # Check if we can reconstruct data from the conversation history
            keyboard = [[InlineKeyboardButton("« Back to Teams List", callback_data="team_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "Error: Could not determine which team or player to update.\n\n"
                "Please try selecting a team and player again.",
                reply_markup=reply_markup
            )
            return TEAM_MANAGEMENT
        
        # Add player to team
        success, message = db.add_player_to_team(team_id, player_id, position, user_id)
        
        if success:
            # Get player name
            player = db.get_player(player_id)
            player_name = player['name'] if player else "Selected player"
            
            # Show success message and return to team view
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"✅ *{player_name}* has been added to your team!\n\n"
                f"Position: {position if position else 'Not assigned'}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            # Check if error is about not owning the player
            if "don't own" in message.lower() or "not found" in message.lower():
                # Get available players for this user
                user_players = db.get_user_players(user_id)
                player_ids = [p['id'] for p in user_players] if user_players else []
                
                if player_id not in player_ids:
                    # Player is not owned by user
                    keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    query.edit_message_text(
                        "❌ You don't own this player. Please select a player you own.\n\n"
                        "Try opening some packs to get more players!",
                        reply_markup=reply_markup
                    )
                    return TEAM_VIEW
            
            # For other errors, show general error message
            keyboard = [[InlineKeyboardButton("« Try Again", callback_data=f"add_player_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"❌ Error adding player to team: {message}",
                reply_markup=reply_markup
            )
        
        return TEAM_VIEW
        
    elif data.startswith("remove_player_"):
        # Show list of players that can be removed from the team
        team_id = int(data.split("_")[-1])
        
        # Get team players
        team = db.get_team(team_id, user_id)
        
        if not team or not team['players']:
            # No players in the team
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "There are no players in this team to remove.",
                reply_markup=reply_markup
            )
            return TEAM_VIEW
        
        # Create keyboard with team players
        keyboard = []
        
        for player in team['players']:
            emoji = utils.get_tier_emoji(player['tier'])
            position = f" (Pos {player['position']})" if player['position'] is not None else ""
            player_button = [InlineKeyboardButton(
                f"{emoji} {player['name']}{position}",
                callback_data=f"remove_pl_{team_id}_{player['id']}"
            )]
            keyboard.append(player_button)
        
        # Add back button
        keyboard.append([InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "Select a player to remove from your team:",
            reply_markup=reply_markup
        )
        return TEAM_VIEW
        
    elif data.startswith("remove_pl_"):
        # User selected a player to remove from the team
        parts = data.split("_")
        team_id = int(parts[2])
        player_id = int(parts[3])
        
        # Remove player from team
        success, message = db.remove_player_from_team(team_id, player_id, user_id)
        
        if success:
            # Show success message and return to team view
            keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"✅ {message}",
                reply_markup=reply_markup
            )
        else:
            # Show error message
            keyboard = [[InlineKeyboardButton("« Try Again", callback_data=f"remove_player_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"❌ Error removing player: {message}",
                reply_markup=reply_markup
            )
        
        return TEAM_VIEW
        
    elif data.startswith("edit_team_"):
        # Not implementing inline edit functionality in this iteration
        team_id = int(data.split("_")[-1])
        
        # Show message about using /create_team instead
        keyboard = [[InlineKeyboardButton("« Back to Team", callback_data=f"view_team_{team_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "To edit your team, please create a new team with the desired changes.\n\n"
            "You can use /create_team to start the creation process.",
            reply_markup=reply_markup
        )
        return TEAM_VIEW
        
    elif data.startswith("delete_team_"):
        # Confirm team deletion
        team_id = int(data.split("_")[-1])
        
        # Debug logging
        logger.info(f"Delete team button clicked for team_id: {team_id}, user_id: {user_id}")
        
        # Get team to confirm it exists and belongs to user
        team = db.get_team(team_id, user_id)
        
        logger.info(f"Team data retrieved: {team}")
        
        if not team:
            query.edit_message_text(
                "Team not found or you don't have access to it.\n\n"
                "Press /teams to return to the teams menu."
            )
            return ConversationHandler.END
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, delete", callback_data=f"confirm_delete_team_{team_id}"),
                InlineKeyboardButton("❌ No, cancel", callback_data=f"view_team_{team_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.info(f"Showing delete confirmation for team: {team['name']}")
        
        query.edit_message_text(
            f"❗ Are you sure you want to delete the team *{team['name']}*?\n\n"
            f"This action cannot be undone and all players will be removed from the team.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return TEAM_VIEW
        
    elif data.startswith("confirm_delete_team_"):
        # User confirmed team deletion
        team_id = int(data.split("_")[-1])
        
        # Enhanced debugging
        logger.info(f"Confirm delete team button clicked for team_id: {team_id}, user_id: {user_id}")
        
        # Delete the team
        success, message = db.delete_team(team_id, user_id)
        
        logger.info(f"Delete result: success={success}, message={message}")
        
        if success:
            # Show success message and return to teams list
            keyboard = [[InlineKeyboardButton("« Back to Teams List", callback_data="team_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.info("Preparing success message")
            
            try:
                query.edit_message_text(
                    f"✅ {message}",
                    reply_markup=reply_markup
                )
                logger.info("Successfully edited message with success notification")
            except Exception as e:
                logger.error(f"Error while showing success message: {str(e)}")
                
            # Return to TEAM_MANAGEMENT to handle the team_list callback
            logger.info("Team deletion successful, returning to TEAM_MANAGEMENT")
            return TEAM_MANAGEMENT
        else:
            # Show error message
            keyboard = [[InlineKeyboardButton("« Try Again", callback_data=f"delete_team_{team_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                query.edit_message_text(
                    f"❌ Error deleting team: {message}",
                    reply_markup=reply_markup
                )
                logger.info("Successfully edited message with error notification")
            except Exception as e:
                logger.error(f"Error while showing error message: {str(e)}")
            
            # On error, stay in TEAM_VIEW so user can try again
            logger.info("Team deletion failed, returning to TEAM_VIEW")
            return TEAM_VIEW
        
    elif data == "back_to_team_menu":
        # Return to main teams menu
        keyboard = [
            [InlineKeyboardButton("➕ Create New Team", callback_data="team_create")],
            [InlineKeyboardButton("🏏 View My Teams", callback_data="team_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🏏 *TEAM MANAGEMENT* 🏏\n\n"
            "Manage your cricket teams and players here.\n\n"
            "What would you like to do?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return TEAM_MANAGEMENT
    
    return ConversationHandler.END


def create_team_start(update: Update, context: CallbackContext) -> int:
    """Start the team creation conversation."""
    update.message.reply_text(
        "Let's create a new cricket team! 🏏\n\n"
        "First, what would you like to name your team?"
    )
    return CREATE_TEAM_NAME


def process_team_name(update: Update, context: CallbackContext) -> int:
    """Process the team name."""
    name = update.message.text
    if not name or len(name) > 50:
        update.message.reply_text(
            "Please provide a valid team name (max 50 characters)."
        )
        return CREATE_TEAM_NAME
    
    context.user_data['team_name'] = name
    
    update.message.reply_text(
        f"Great! Your team will be called *{name}*.\n\n"
        "Now, please provide a short description for your team, "
        "or send /skip to use a default description.",
        parse_mode="Markdown"
    )
    return CREATE_TEAM_DESCRIPTION


def skip_description(update: Update, context: CallbackContext) -> int:
    """Skip the description."""
    user = update.effective_user
    context.user_data['team_description'] = f"{user.name}'s Cricket Team"
    
    # Call create_team_finish directly
    create_team_finish(update, context)
    return TEAM_VIEW


def process_team_description(update: Update, context: CallbackContext) -> int:
    """Process the team description."""
    description = update.message.text
    if len(description) > 200:
        update.message.reply_text(
            "Description is too long. Please keep it under 200 characters."
        )
        return CREATE_TEAM_DESCRIPTION
    
    context.user_data['team_description'] = description
    
    # Call create_team_finish directly
    create_team_finish(update, context)
    return TEAM_VIEW


def create_team_finish(update: Update, context: CallbackContext) -> int:
    """Finish creating the team."""
    user_id = update.effective_user.id
    
    team_data = {
        'name': context.user_data['team_name'],
        'description': context.user_data['team_description']
    }
    
    success, result = db.create_team(user_id, team_data)
    
    if success:
        team_id = result
        
        # Create a keyboard to manage the newly created team
        keyboard = [
            [InlineKeyboardButton("➕ Add Players", callback_data=f"add_player_{team_id}")],
            [InlineKeyboardButton("🔍 View Team", callback_data=f"view_team_{team_id}")],
            [InlineKeyboardButton("« Back to Teams Menu", callback_data="back_to_team_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"✅ Team *{team_data['name']}* created successfully!\n\n"
            f"Description: {team_data['description']}\n\n"
            f"What would you like to do next?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        update.message.reply_text(
            f"❌ Failed to create team: {result}"
        )
    
    # Clear user data
    context.user_data.clear()
    
    return TEAM_VIEW
def marketplace(update: Update, context: CallbackContext) -> None:
    """Show marketplace with buy/sell options"""
    keyboard = [
        [
            InlineKeyboardButton("🛍️ Buy Players", callback_data="market_buy_0"),
            InlineKeyboardButton("💰 Sell Players", callback_data="market_sell_0")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🏪 *CRICKET MARKETPLACE* 🏪\n\n"
        "Choose an option:\n"
        "• Buy players from other users\n"
        "• Sell your own players\n\n"
        "Note: A 5% transaction fee applies to all sales"
    )
    
    # Handle both message and callback query
    if update.callback_query:
        # This is a callback from "Back to Market" button
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # This is from /market command
        update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def market_buy_handler(update: Update, context: CallbackContext) -> None:
    """Handle marketplace buy view"""
    query = update.callback_query
    query.answer()
    
    # Get page number from callback data
    page = int(query.data.split('_')[-1])
    items_per_page = 5
    offset = page * items_per_page
    
    # Get listings
    listings = get_marketplace_listings(items_per_page, offset)
    
    if not listings:
        keyboard = [[InlineKeyboardButton("« Back to Market", callback_data="market_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "No players currently listed in the marketplace.",
            reply_markup=reply_markup
        )
        return
    
    # Format listings
    response = "🛍️ *AVAILABLE PLAYERS* 🛍️\n\n"
    keyboard = []
    
    for listing in listings:
        tier_emoji = get_tier_emoji(listing['tier'])
        # Add edition info if available
        edition_text = f" | {listing['edition']}" if 'edition' in listing and listing['edition'] else ""
        response += f"{tier_emoji} *{listing['name']}* ({listing['total_ovr']} OVR){edition_text}\n"
        response += f"• Role: {listing['role']}\n"
        response += f"• Price: 💰 {listing['price']} coins\n"
        response += f"• ID: `{listing['listing_id']}`\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"Buy {listing['name']} ({listing['price']} 💰)", 
                callback_data=f"buy_confirm_{listing['listing_id']}"
            )
        ])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("« Previous", callback_data=f"market_buy_{page-1}"))
    if len(listings) == items_per_page:
        nav_buttons.append(InlineKeyboardButton("Next »", callback_data=f"market_buy_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton("« Back to Market", callback_data="market_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def market_sell_handler(update: Update, context: CallbackContext) -> None:
    """Handle marketplace sell view"""
    query = update.callback_query
    query.answer()
    
    # Get page number from callback data
    page = int(query.data.split('_')[-1])
    items_per_page = 5
    offset = page * items_per_page
    
    # Get user's players
    user_players = get_user_players(query.from_user.id)
    
    if not user_players:
        keyboard = [[InlineKeyboardButton("« Back to Market", callback_data="market_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "You don't have any players to sell.\n"
            "Open some packs to get players!",
            reply_markup=reply_markup
        )
        return
    
    # Get paginated players
    start_idx = offset
    end_idx = min(start_idx + items_per_page, len(user_players))
    current_players = user_players[start_idx:end_idx]
    
    # Format response
    response = "💰 *SELECT PLAYER TO SELL* 💰\n\n"
    keyboard = []
    
    for player in current_players:
        tier_emoji = get_tier_emoji(player['tier'])
        min_price = get_base_price_by_tier(player['tier'])
        
        keyboard.append([
            InlineKeyboardButton(
                f"{tier_emoji} {player['name']} ({player['total_ovr']} OVR)", 
                callback_data=f"sell_player_{player['id']}"
            )
        ])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("« Previous", callback_data=f"market_sell_{page-1}"))
    if end_idx < len(user_players):
        nav_buttons.append(InlineKeyboardButton("Next »", callback_data=f"market_sell_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton("« Back to Market", callback_data="market_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def sell_player_handler(update: Update, context: CallbackContext) -> None:
    """Handle player sale setup"""
    query = update.callback_query
    query.answer()
    
    player_id = int(query.data.split('_')[-1])
    player = get_player(player_id)
    
    if not player:
        query.edit_message_text("Error: Player not found")
        return
        
    min_price = get_base_price_by_tier(player['tier'])
    tier_emoji = get_tier_emoji(player['tier'])
    
    response = f"{tier_emoji} *SELL PLAYER* {tier_emoji}\n\n"
    response += f"Player: {player['name']}\n"
    response += f"Role: {player['role']}\n"
    response += f"OVR: {player['total_ovr']}\n\n"
    response += f"Minimum price: 💰 {min_price} coins\n"
    response += "Enter price with /setprice &lt;amount&gt;"
    
    # Store player_id in context for price setting
    context.user_data['selling_player_id'] = player_id
    
    keyboard = [[InlineKeyboardButton("« Cancel", callback_data="market_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def buy_confirm_handler(update: Update, context: CallbackContext) -> None:
    """Handle buy confirmation"""
    query = update.callback_query
    query.answer()
    
    listing_id = int(query.data.split('_')[-1])
    success, message = buy_player(query.from_user.id, listing_id)
    
    if success:
        keyboard = [
            [InlineKeyboardButton("👥 My Players", callback_data=f"myplayers_view_user_id_{query.from_user.id}")],
            [InlineKeyboardButton("🏪 Back to Market", callback_data="market_main")]
        ]
    else:
        keyboard = [[InlineKeyboardButton("« Back to Market", callback_data="market_main")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        "✅ " + message if success else "❌ " + message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def set_price_command(update: Update, context: CallbackContext) -> None:
    """Handle setting price for player sale"""
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "❌ Please provide a valid price.\n"
            "Usage: /setprice <amount>"
        )
        return
        
    price = int(context.args[0])
    player_id = context.user_data.get('selling_player_id')
    
    if not player_id:
        update.message.reply_text("❌ No player selected for sale")
        return
        
    player = get_player(player_id)
    if not player:
        update.message.reply_text("❌ Player not found")
        return
        
    min_price = get_base_price_by_tier(player['tier'])
    if price < min_price:
        update.message.reply_text(
            f"❌ Minimum price for {player['tier']} tier is {min_price} coins"
        )
        return
        
    success, message = list_player_for_sale(update.effective_user.id, player_id, price)
    
    if success:
        # Clear selling context
        context.user_data.pop('selling_player_id', None)
        
        keyboard = [[InlineKeyboardButton("« Back to Market", callback_data="market_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"✅ Listed {player['name']} for 💰 {price} coins!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(f"❌ {message}")

def market_insights_command(update: Update, context: CallbackContext) -> None:
    """Show market insights and trends"""
    insights = get_market_insights()
    
    if "error" in insights:
        update.message.reply_text(f"⚠️ Error retrieving market insights: {insights['error']}")
        return
        
    # Format response
    response = "📊 *CRICKET MARKET INSIGHTS* 📊\n\n"
    
    # Most traded roles
    response += "🔄 *Most Traded Roles:*\n"
    if insights.get("most_traded_roles"):
        for role_data in insights["most_traded_roles"]:
            response += f"• {role_data['role']}: {role_data['trade_count']} trades\n"
    else:
        response += "• No trading activity in the past week\n"
    
    response += "\n💰 *Average Prices by Tier:*\n"
    if insights.get("avg_prices_by_tier"):
        for tier_data in insights["avg_prices_by_tier"]:
            tier_emoji = get_tier_emoji(tier_data['tier'])
            avg_price = int(tier_data['avg_price']) if tier_data['avg_price'] else 0
            response += f"• {tier_emoji} {tier_data['tier']}: {avg_price} coins\n"
    else:
        response += "• No pricing data available yet\n"
    
    response += "\n🔝 *Top Recent Sales:*\n"
    if insights.get("top_sales"):
        for i, sale in enumerate(insights["top_sales"], 1):
            tier_emoji = get_tier_emoji(sale['tier'])
            response += f"{i}. {tier_emoji} *{sale['name']}*: 💰 {sale['price']} coins\n"
    else:
        response += "• No sales recorded yet\n"
    
    response += "\n📈 *Price Trends (Last 7 Days):*\n"
    if insights.get("price_trends"):
        for trend in insights["price_trends"]:
            tier_emoji = get_tier_emoji(trend['tier'])
            price_change = trend.get('price_change_percent', 0)
            if price_change > 0:
                direction = "↗️ +" + str(round(price_change, 1)) + "%"
            elif price_change < 0:
                direction = "↘️ " + str(round(price_change, 1)) + "%"
            else:
                direction = "➡️ 0%"
                
            response += f"• {tier_emoji} {trend['tier']}: {direction}\n"
    else:
        response += "• Not enough data for price trend analysis\n"
    
    response += "\n💡 *Market Tips:*\n"
    response += "• Use `/price <player_id>` to get a fair value estimate\n"
    response += "• Higher OVR and rare players command higher prices\n"
    response += "• Check price trends before listing or buying\n"
    
    # Send the insights message
    update.message.reply_text(response, parse_mode='Markdown')

def market_listings_command(update: Update, context: CallbackContext) -> None:
    """Show current marketplace listings"""
    # Get listings
    listings = get_marketplace_listings()
    
    if not listings:
        keyboard = [
            [InlineKeyboardButton("Sell a Player", callback_data="market_sell")],
            [InlineKeyboardButton("Market Insights", callback_data="market_insights")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "No players currently listed in the marketplace.",
            reply_markup=reply_markup
        )
        return
        
    # Format response
    response = "🏪 *PLAYER MARKETPLACE* 🏪\n\n"
    
    for listing in listings:
        tier_emoji = get_tier_emoji(listing['tier'])
        # Add edition info if available
        edition_text = f" | {listing['edition']}" if 'edition' in listing and listing['edition'] else ""
        response += f"{tier_emoji} *{listing['name']}* ({listing['total_ovr']} OVR){edition_text}\n"
        response += f"• Role: {listing['role']}\n"
        response += f"• Team: {listing['team']}\n"
        response += f"• Price: 💰 {listing['price']} coins\n"
        response += f"• Seller: {listing['seller_name']}\n"
        response += f"• ID: `{listing['listing_id']}`\n\n"

    response += "To buy a player, use:\n`/buy <listing_id>`\n\n"
    response += "To list a player, use:\n`/sell <player_id> <price>`\n\n"
    response += "For market analysis, use:\n`/market_insights`"
    
    keyboard = [
        [InlineKeyboardButton("Buy Players", callback_data="market_buy")],
        [InlineKeyboardButton("Sell a Player", callback_data="market_sell")],
        [InlineKeyboardButton("Market Insights", callback_data="market_insights")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)

def sell_player(update: Update, context: CallbackContext) -> None:
    """List a player for sale"""
    if not context.args or len(context.args) != 2:
        update.message.reply_text(
            "❌ Please provide player ID and price.\n"
            "Usage: `/sell <player_id> <price>`",
            parse_mode='Markdown'
        )
        return

    try:
        player_id = int(context.args[0])
        price = int(context.args[1])
    except ValueError:
        update.message.reply_text("❌ Invalid player ID or price format.")
        return

    if price <= 0:
        update.message.reply_text("❌ Price must be positive.")
        return

    # Get player info to check tier price
    player = get_player(player_id)
    if not player:
        update.message.reply_text("❌ Player not found.")
        return

    # Calculate minimum price based on tier
    min_price = get_base_price_by_tier(player['tier'])
    if price < min_price:
        update.message.reply_text(
            f"❌ Minimum price for {player['tier']} tier is {min_price} coins."
        )
        return

    success, message = list_player_for_sale(update.effective_user.id, player_id, price)
    
    if success:
        tier_emoji = get_tier_emoji(player['tier'])
        update.message.reply_text(
            f"✅ {tier_emoji} *{player['name']}* listed for 💰 {price} coins!",
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(f"❌ {message}")

def buy_player_command(update: Update, context: CallbackContext) -> None:
    """Buy a player from marketplace"""
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "❌ Please provide listing ID.\n"
            "Usage: `/buy <listing_id>`",
            parse_mode='Markdown'
        )
        return

    listing_id = int(context.args[0])
    success, message = buy_player(update.effective_user.id, listing_id)
    
    if success:
        update.message.reply_text(
            f"✅ {message}\n\n"
            f"Check your players with /myplayers",
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(f"❌ {message}")
# Player Statistics Handlers
def format_player_statistics(stats):
    """
    Format player statistics for display in Telegram
    
    Args:
        stats: Dictionary containing player statistics
    
    Returns:
        Formatted text for Telegram message
    """
    if not stats:
        return "❌ No statistics found for this player."
    
    player_name = stats.get('name', 'Unknown Player')
    role = stats.get('role', 'Unknown')
    team = stats.get('team', 'Unknown')
    tier = stats.get('tier', 'Bronze')
    tier_emoji = get_tier_emoji(tier)
    
    # Basic info
    formatted_text = (
        f"📊 *PLAYER STATISTICS*\n\n"
        f"{tier_emoji} *{player_name}* ({role})\n"
        f"🏏 *Team:* {team}\n"
        f"🎮 *Matches Played:* {stats.get('matches_played', 0)} "
        f"(Won: {stats.get('matches_won', 0)})\n"
        f"🏆 *Player of the Match:* {stats.get('player_of_match', 0)} times\n\n"
    )
    
    # Batting stats (only show if player has batted)
    if stats.get('innings_batted', 0) > 0:
        formatted_text += (
            f"🏏 *BATTING STATS*\n"
            f"Innings: {stats.get('innings_batted', 0)}\n"
            f"Runs: {stats.get('runs_scored', 0)}\n"
            f"Not Outs: {stats.get('not_outs', 0)}\n"
            f"Highest Score: {stats.get('highest_score', 0)}\n"
            f"Average: {stats.get('batting_average', 0.0):.2f}\n"
            f"Strike Rate: {stats.get('batting_strike_rate', 0.0):.2f}\n"
            f"50s/100s: {stats.get('fifties', 0)}/{stats.get('hundreds', 0)}\n"
            f"4s/6s: {stats.get('fours', 0)}/{stats.get('sixes', 0)}\n\n"
        )
    
    # Bowling stats (only show if player has bowled)
    if stats.get('innings_bowled', 0) > 0:
        formatted_text += (
            f"⚾ *BOWLING STATS*\n"
            f"Innings: {stats.get('innings_bowled', 0)}\n"
            f"Overs: {stats.get('overs_bowled', 0.0):.1f}\n"
            f"Wickets: {stats.get('wickets_taken', 0)}\n"
            f"Best Bowling: {stats.get('best_bowling', '0/0')}\n"
            f"Average: {stats.get('bowling_average', 0.0):.2f}\n"
            f"Strike Rate: {stats.get('bowling_strike_rate', 0.0):.2f}\n"
            f"Economy: {stats.get('bowling_economy', 0.0):.2f}\n"
            f"Maidens: {stats.get('maidens', 0)}\n"
            f"3w/5w: {stats.get('three_wicket_hauls', 0)}/{stats.get('five_wicket_hauls', 0)}\n"
        )
    
    return formatted_text


def player_stats_command(update: Update, context: CallbackContext) -> None:
    """Display statistics for a specific player"""
    
    # Get the user's ID
    user = get_or_create_user(update.effective_user.id, name=update.effective_user.first_name)
    
    # Check if a player ID was provided
    if not context.args:
        update.message.reply_text(
            "❌ Please provide a player ID.\n\n"
            "Usage: /playerstats <player_id>\n\n"
            "You can find player IDs with /myplayers command."
        )
        return
    
    try:
        player_id = int(context.args[0])
        
        # Get player statistics
        stats = get_player_stats(user['id'], player_id)
        
        if not stats:
            update.message.reply_text(
                "❌ No statistics found for this player. Either:\n"
                "• The player doesn't exist\n"
                "• You don't own this player\n"
                "• The player hasn't played any matches yet\n\n"
                "Check your player collection with /myplayers"
            )
            return
        
        # Format and send the statistics
        formatted_stats = format_player_statistics(stats)
        update.message.reply_text(formatted_stats, parse_mode='Markdown')
    
    except ValueError:
        update.message.reply_text("❌ Invalid player ID. Please provide a valid number.")


def my_stats_command(update: Update, context: CallbackContext) -> None:
    """Display statistics for all players owned by the user"""
    
    # Get the user's ID
    user = get_or_create_user(update.effective_user.id, name=update.effective_user.first_name)
    
    # Parse arguments for sorting and filtering
    sort_by = 'batting_average'
    sort_order = 'desc'
    role_filter = None
    limit = 10
    offset = 0
    
    if context.args:
        for arg in context.args:
            if arg.startswith('sort:'):
                sort_field = arg.split(':')[1].strip().lower()
                valid_fields = [
                    'batting_average', 'batting_strike_rate', 'runs_scored',
                    'bowling_average', 'bowling_strike_rate', 'bowling_economy',
                    'wickets_taken', 'matches_played', 'matches_won'
                ]
                if sort_field in valid_fields:
                    sort_by = sort_field
            
            elif arg.startswith('order:'):
                order = arg.split(':')[1].strip().lower()
                if order in ['asc', 'desc']:
                    sort_order = order
            
            elif arg.startswith('role:'):
                role = arg.split(':')[1].strip().lower()
                if role in ['batsman', 'bowler', 'all-rounder', 'wicket-keeper']:
                    role_filter = role
            
            elif arg.startswith('limit:'):
                try:
                    limit_val = int(arg.split(':')[1].strip())
                    if 1 <= limit_val <= 50:
                        limit = limit_val
                except ValueError:
                    pass
            
            elif arg.startswith('offset:'):
                try:
                    offset_val = int(arg.split(':')[1].strip())
                    if offset_val >= 0:
                        offset = offset_val
                except ValueError:
                    pass
    
    # Get player statistics
    player_stats = get_user_player_stats(
        user['id'], sort_by=sort_by, sort_order=sort_order,
        role_filter=role_filter, limit=limit, offset=offset
    )
    
    if not player_stats:
        update.message.reply_text(
            "❌ No player statistics found. Possible reasons:\n"
            "• You don't own any players\n"
            "• Your players haven't played any matches yet\n\n"
            "Check your player collection with /myplayers"
        )
        return
    
    # Create a message for the player stats overview
    sorting_description = (
        f"Sorting by: {sort_by.replace('_', ' ').title()} "
        f"({'Ascending' if sort_order == 'asc' else 'Descending'})"
    )
    
    role_description = f"Role filter: {role_filter.title()}" if role_filter else "All roles"
    
    pagination_info = f"Showing {min(limit, len(player_stats))} players, starting at {offset}"
    
    header = (
        f"📊 *YOUR PLAYER STATISTICS* 📊\n\n"
        f"🔍 *{sorting_description}*\n"
        f"👤 *{role_description}*\n"
        f"📋 *{pagination_info}*\n\n"
    )
    
    message_parts = [header]
    
    # Add each player's basic stats
    for i, stats in enumerate(player_stats, 1):
        player_name = stats.get('name', 'Unknown Player')
        tier = stats.get('tier', 'Bronze')
        tier_emoji = get_tier_emoji(tier)
        role = stats.get('role', 'Unknown')
        
        # Create a brief player summary
        if sort_by.startswith('batting'):
            # For batting stats
            player_part = (
                f"{i}. {tier_emoji} *{player_name}* ({role})\n"
                f"   🏏 AVG: {stats.get('batting_average', 0.0):.2f} • "
                f"SR: {stats.get('batting_strike_rate', 0.0):.2f} • "
                f"Runs: {stats.get('runs_scored', 0)}\n"
            )
        elif sort_by.startswith('bowling'):
            # For bowling stats
            player_part = (
                f"{i}. {tier_emoji} *{player_name}* ({role})\n"
                f"   ⚾ AVG: {stats.get('bowling_average', 0.0):.2f} • "
                f"SR: {stats.get('bowling_strike_rate', 0.0):.2f} • "
                f"Wickets: {stats.get('wickets_taken', 0)}\n"
            )
        else:
            # For general stats
            player_part = (
                f"{i}. {tier_emoji} *{player_name}* ({role})\n"
                f"   🎮 MP: {stats.get('matches_played', 0)} • "
                f"Wins: {stats.get('matches_won', 0)} • "
                f"POTM: {stats.get('player_of_match', 0)}\n"
            )
        
        message_parts.append(player_part)
    
    # Add footer with command help
    footer = (
        f"\n*Other sorting options:*\n"
        f"• /mystats sort:batting_average\n"
        f"• /mystats sort:bowling_average\n"
        f"• /mystats sort:wickets_taken\n"
        f"• /mystats sort:runs_scored\n"
        f"• /mystats role:batsman\n"
        f"• /mystats limit:20 offset:10\n\n"
        f"For detailed player stats, use /playerstats <player_id>"
    )
    
    message_parts.append(footer)
    
    # Send the message
    update.message.reply_text("".join(message_parts), parse_mode='Markdown')


def batting_leaderboard_command(update: Update, context: CallbackContext) -> None:
    """Display a leaderboard of the top batsmen"""
    
    # Default to batting average, but allow override
    stat_field = 'batting_average'
    limit = 10
    
    if context.args:
        for arg in context.args:
            if arg.startswith('stat:'):
                field = arg.split(':')[1].strip().lower()
                valid_fields = ['batting_average', 'batting_strike_rate', 'runs_scored', 'highest_score']
                if field in valid_fields:
                    stat_field = field
            
            elif arg.startswith('limit:'):
                try:
                    limit_val = int(arg.split(':')[1].strip())
                    if 1 <= limit_val <= 50:
                        limit = limit_val
                except ValueError:
                    pass
    
    # Get the leaderboard data
    leaderboard_data = get_leaderboard(stat_type='batting', stat_field=stat_field, limit=limit)
    
    if not leaderboard_data:
        update.message.reply_text(
            "❌ No batting statistics available yet.\n\n"
            "Players need to participate in matches to appear on the leaderboard."
        )
        return
    
    # Format the title based on the stat type
    if stat_field == 'batting_average':
        title = "BATTING AVERAGE LEADERBOARD"
        stat_name = "Average"
    elif stat_field == 'batting_strike_rate':
        title = "BATTING STRIKE RATE LEADERBOARD"
        stat_name = "Strike Rate"
    elif stat_field == 'runs_scored':
        title = "MOST RUNS LEADERBOARD"
        stat_name = "Runs"
    elif stat_field == 'highest_score':
        title = "HIGHEST SCORE LEADERBOARD"
        stat_name = "Highest Score"
    else:
        title = "BATTING LEADERBOARD"
        stat_name = "Stat"
    
    # Create the header
    header = (
        f"🏆 *{title}* 🏆\n\n"
        f"The top {len(leaderboard_data)} batsmen ranked by {stat_name.lower()}\n\n"
    )
    
    # Format the leaderboard entries
    leaderboard_entries = []
    
    for i, player in enumerate(leaderboard_data, 1):
        player_name = player.get('name', 'Unknown Player')
        owner_name = player.get('owner_name', 'Unknown Owner')
        tier = player.get('tier', 'Bronze')
        tier_emoji = get_tier_emoji(tier)
        
        # Get the relevant statistic
        if stat_field == 'batting_average':
            stat_value = f"{player.get('batting_average', 0.0):.2f}"
        elif stat_field == 'batting_strike_rate':
            stat_value = f"{player.get('batting_strike_rate', 0.0):.2f}"
        elif stat_field == 'runs_scored':
            stat_value = f"{player.get('runs_scored', 0)}"
        elif stat_field == 'highest_score':
            stat_value = f"{player.get('highest_score', 0)}"
        else:
            stat_value = "N/A"
        
        # Format as medal for top 3, number for the rest
        if i == 1:
            rank = "🥇"
        elif i == 2:
            rank = "🥈"
        elif i == 3:
            rank = "🥉"
        else:
            rank = f"{i}."
        
        # Add additional batting stats
        innings = player.get('innings_batted', 0)
        runs = player.get('runs_scored', 0)
        avg = player.get('batting_average', 0.0)
        sr = player.get('batting_strike_rate', 0.0)
        
        entry = (
            f"{rank} {tier_emoji} *{player_name}*\n"
            f"   *{stat_name}:* {stat_value}\n"
            f"   Innings: {innings} • Runs: {runs}\n"
            f"   Avg: {avg:.2f} • SR: {sr:.2f}\n"
            f"   Owner: {owner_name}\n"
        )
        
        leaderboard_entries.append(entry)
    
    # Add footer with command help
    footer = (
        f"\n*Other leaderboard options:*\n"
        f"• /battingleaderboard stat:batting_average\n"
        f"• /battingleaderboard stat:batting_strike_rate\n"
        f"• /battingleaderboard stat:runs_scored\n"
        f"• /battingleaderboard stat:highest_score\n"
        f"• /battingleaderboard limit:5\n\n"
        f"Check bowling stats with /bowlingleaderboard"
    )
    
    # Combine all parts and send
    message = header + "\n".join(leaderboard_entries) + footer
    update.message.reply_text(message, parse_mode='Markdown')


def bowling_leaderboard_command(update: Update, context: CallbackContext) -> None:
    """Display a leaderboard of the top bowlers"""
    
    # Default to bowling average, but allow override
    stat_field = 'bowling_average'
    limit = 10
    
    if context.args:
        for arg in context.args:
            if arg.startswith('stat:'):
                field = arg.split(':')[1].strip().lower()
                valid_fields = ['bowling_average', 'bowling_strike_rate', 'bowling_economy', 'wickets_taken']
                if field in valid_fields:
                    stat_field = field
            
            elif arg.startswith('limit:'):
                try:
                    limit_val = int(arg.split(':')[1].strip())
                    if 1 <= limit_val <= 50:
                        limit = limit_val
                except ValueError:
                    pass
    
    # Get the leaderboard data
    leaderboard_data = get_leaderboard(stat_type='bowling', stat_field=stat_field, limit=limit)
    
    if not leaderboard_data:
        update.message.reply_text(
            "❌ No bowling statistics available yet.\n\n"
            "Players need to participate in matches to appear on the leaderboard."
        )
        return
    
    # Format the title based on the stat type
    if stat_field == 'bowling_average':
        title = "BOWLING AVERAGE LEADERBOARD"
        stat_name = "Average"
    elif stat_field == 'bowling_strike_rate':
        title = "BOWLING STRIKE RATE LEADERBOARD"
        stat_name = "Strike Rate"
    elif stat_field == 'bowling_economy':
        title = "BOWLING ECONOMY LEADERBOARD"
        stat_name = "Economy"
    elif stat_field == 'wickets_taken':
        title = "MOST WICKETS LEADERBOARD"
        stat_name = "Wickets"
    else:
        title = "BOWLING LEADERBOARD"
        stat_name = "Stat"
    
    # Create the header
    header = (
        f"🏆 *{title}* 🏆\n\n"
        f"The top {len(leaderboard_data)} bowlers ranked by {stat_name.lower()}\n\n"
    )
    
    # Format the leaderboard entries
    leaderboard_entries = []
    
    for i, player in enumerate(leaderboard_data, 1):
        player_name = player.get('name', 'Unknown Player')
        owner_name = player.get('owner_name', 'Unknown Owner')
        tier = player.get('tier', 'Bronze')
        tier_emoji = get_tier_emoji(tier)
        
        # Get the relevant statistic
        if stat_field == 'bowling_average':
            stat_value = f"{player.get('bowling_average', 0.0):.2f}"
        elif stat_field == 'bowling_strike_rate':
            stat_value = f"{player.get('bowling_strike_rate', 0.0):.2f}"
        elif stat_field == 'bowling_economy':
            stat_value = f"{player.get('bowling_economy', 0.0):.2f}"
        elif stat_field == 'wickets_taken':
            stat_value = f"{player.get('wickets_taken', 0)}"
        else:
            stat_value = "N/A"
        
        # Format as medal for top 3, number for the rest
        if i == 1:
            rank = "🥇"
        elif i == 2:
            rank = "🥈"
        elif i == 3:
            rank = "🥉"
        else:
            rank = f"{i}."
        
        # Add additional bowling stats
        innings = player.get('innings_bowled', 0)
        wickets = player.get('wickets_taken', 0)
        economy = player.get('bowling_economy', 0.0)
        best = player.get('best_bowling', '0/0')
        
        entry = (
            f"{rank} {tier_emoji} *{player_name}*\n"
            f"   *{stat_name}:* {stat_value}\n"
            f"   Innings: {innings} • Wickets: {wickets}\n"
            f"   Economy: {economy:.2f} • Best: {best}\n"
            f"   Owner: {owner_name}\n"
        )
        
        leaderboard_entries.append(entry)
    
    # Add footer with command help
    footer = (
        f"\n*Other leaderboard options:*\n"
        f"• /bowlingleaderboard stat:bowling_average\n"
        f"• /bowlingleaderboard stat:bowling_strike_rate\n"
        f"• /bowlingleaderboard stat:bowling_economy\n"
        f"• /bowlingleaderboard stat:wickets_taken\n"
        f"• /bowlingleaderboard limit:5\n\n"
        f"Check batting stats with /battingleaderboard"
    )
    
    # Combine all parts and send
    message = header + "\n".join(leaderboard_entries) + footer
    update.message.reply_text(message, parse_mode='Markdown')