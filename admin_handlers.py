#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Admin command handlers for the Cricket Game Bot
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from db import (
    is_admin, get_all_users, find_user_by_username, 
    update_user_coins, give_player_to_user,
    update_pack_status, delete_pack,
    get_player, search_players,
    delete_user_data
)

logger = logging.getLogger(__name__)

# Define conversation states
(
    MAIN_MENU, USER_MANAGEMENT, PACK_MANAGEMENT, PLAYER_MANAGEMENT,
    FIND_USER, GIVE_COINS, GIVE_PLAYER, SEARCH_PLAYER,
    PACK_ACTION, SELECT_USER, SELECT_PLAYER, CONFIRM_GIVE,
    ADMIN_MENU, USER_MENU, DELETE_USER_DATA, CONFIRM_DELETE  # Added DELETE states
) = range(16)


def admin_panel(update: Update, context: CallbackContext) -> int:
    """Admin panel main menu."""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not is_admin(user_id):
        update.message.reply_text(
            "❌ You do not have permission to access the admin panel."
        )
        return ConversationHandler.END
    
    # Create keyboard with admin options
    keyboard = [
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
        [InlineKeyboardButton("📦 Pack Management", callback_data="admin_packs")],
        [InlineKeyboardButton("🏏 Player Management", callback_data="admin_players")],
        [InlineKeyboardButton("🔄 Bot Status", callback_data="admin_status")],
        [InlineKeyboardButton("❌ Exit", callback_data="admin_exit")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clear any previous conversation data
    context.user_data.clear()
    
    update.message.reply_text(
        "🔧 *ADMIN PANEL*\n\n"
        "Welcome to the Cricket Game Bot admin panel.\n"
        "Please select an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU


def admin_menu_handler(update: Update, context: CallbackContext) -> int:
    """Handle main menu selections (non-async version for compatibility)"""
    query = update.callback_query
    query.answer()
    
    choice = query.data.split('_')[1]
    
    if choice == 'exit':
        query.edit_message_text("Admin panel closed.")
        return ConversationHandler.END
        
    elif choice == 'menu':
        # Create keyboard with admin options
        keyboard = [
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📦 Pack Management", callback_data="admin_packs")],
            [InlineKeyboardButton("🏏 Player Management", callback_data="admin_players")],
            [InlineKeyboardButton("🔄 Bot Status", callback_data="admin_status")],
            [InlineKeyboardButton("❌ Exit", callback_data="admin_exit")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "👨‍💼 <b>Admin Panel</b>\n\n"
            "Welcome to the Cricket Game Bot admin panel.\n"
            "Please select an option:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        return MAIN_MENU
    
    elif choice == 'users':
        # User management menu
        keyboard = [
            [InlineKeyboardButton("👥 List All Users", callback_data="users_list")],
            [InlineKeyboardButton("🔍 Find User", callback_data="users_find")],
            [InlineKeyboardButton("💰 Give Coins", callback_data="users_coins")],
            [InlineKeyboardButton("🎮 Give Player", callback_data="users_player")],
            [InlineKeyboardButton("🗑️ Delete User Data", callback_data="users_delete")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "👥 *USER MANAGEMENT*\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return USER_MANAGEMENT
    
    elif choice == 'packs':
        # Pack management menu
        keyboard = [
            [InlineKeyboardButton("📦 List All Packs", callback_data="packs_list")],
            [InlineKeyboardButton("➕ Create New Pack", callback_data="packs_create")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="packs_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "📦 *PACK MANAGEMENT*\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return PACK_MANAGEMENT
    
    elif choice == 'players':
        # Player management menu
        keyboard = [
            [InlineKeyboardButton("🏏 List All Players", callback_data="players_list")],
            [InlineKeyboardButton("➕ Add New Player", callback_data="players_add")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="players_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🏏 *PLAYER MANAGEMENT*\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return PLAYER_MANAGEMENT
    
    elif choice == 'status':
        # Show bot status
        from health_checker import check_health
        status = check_health()
        
        status_text = "🔄 *BOT STATUS*\n\n"
        
        for component, info in status.items():
            emoji = "✅" if info["status"] else "❌"
            status_text += f"{emoji} *{component}*: {info['message']}\n"
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            status_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    else:
        # Unknown option
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Unknown option selected.",
            reply_markup=reply_markup
        )
        return MAIN_MENU


# User Management Handlers
def user_management_handler(update: Update, context: CallbackContext) -> int:
    """Handle user management menu selections (non-async version for compatibility)"""
    query = update.callback_query
    query.answer()
    
    choice = query.data.split('_')[1]
    
    if choice == 'back':
        # Return to main menu - fixed to not use await
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("🎮 Player Management", callback_data="admin_players")],
            [InlineKeyboardButton("📦 Pack Management", callback_data="admin_packs")],
            [InlineKeyboardButton("❌ Exit Admin Panel", callback_data="admin_exit")]
        ])
        query.edit_message_text(
            "👨‍💼 <b>Admin Panel</b>\n\nSelect an option:",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
        return ADMIN_MENU
    
    elif choice == 'list':
        # List all users with pagination
        page = context.user_data.get('user_page', 1)
        users = get_all_users()
        
        if not users:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "No users found in the system.",
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
        
        # Paginate users
        items_per_page = 5
        total_pages = (len(users) + items_per_page - 1) // items_per_page
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages))
        context.user_data['user_page'] = page
        
        # Get users for current page
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(users))
        current_users = users[start_idx:end_idx]
        
        # Format user list
        response = f"👥 *USERS* (Page {page}/{total_pages})\n\n"
        
        for idx, user in enumerate(current_users, start=1):
            response += f"{idx}. *{user['name']}*\n"
            response += f"   ID: {user['telegram_id']}\n"
            response += f"   💰 Coins: {user['coins']}\n\n"
        
        # Add navigation buttons
        keyboard = []
        
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data="users_prev"))
        
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ▶️", callback_data="users_next"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="users_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return USER_MANAGEMENT
    
    elif choice == 'prev':
        # Go to previous page
        context.user_data['user_page'] = context.user_data.get('user_page', 1) - 1
        # Call list handler again
        query.data = 'users_list'
        return user_management_handler(update, context)
    
    elif choice == 'next':
        # Go to next page
        context.user_data['user_page'] = context.user_data.get('user_page', 1) + 1
        # Call list handler again
        query.data = 'users_list'
        return user_management_handler(update, context)
    
    elif choice == 'find':
        # Start user search conversation
        keyboard = [
            [InlineKeyboardButton("⬅️ Cancel", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🔍 *FIND USER*\n\n"
            "Please enter a username to search for:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return FIND_USER
    
    elif choice == 'coins':
        # Start give coins conversation
        users = get_all_users()
        
        if not users:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "No users found in the system.",
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
        
        # Format user list with buttons
        response = "💰 *GIVE COINS*\n\nSelect a user to give coins to:"
        
        # Create keyboard with user buttons
        keyboard = []
        for user in users[:10]:  # Limit to first 10 users
            keyboard.append([
                InlineKeyboardButton(
                    f"{user['name']} ({user['coins']} coins)", 
                    callback_data=f"coins_user_{user['telegram_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔍 Search User", callback_data="coins_search")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="users_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return GIVE_COINS
    
    elif choice == 'player':
        # Start give player conversation
        users = get_all_users()
        
        if not users:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "No users found in the system.",
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
        
        # Format user list with buttons
        response = "🎮 *GIVE PLAYER*\n\nSelect a user to give a player to:"
        
        # Create keyboard with user buttons
        keyboard = []
        for user in users[:10]:  # Limit to first 10 users
            keyboard.append([
                InlineKeyboardButton(
                    f"{user['name']}", 
                    callback_data=f"player_user_{user['telegram_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔍 Search User", callback_data="player_search")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="users_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return GIVE_PLAYER
        
    elif choice == 'delete':
        # Start delete user data conversation
        users = get_all_users()
        
        if not users:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "No users found in the system.",
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
        
        # Format user list with buttons
        response = "🗑️ *DELETE USER DATA*\n\nSelect a user whose data you want to delete:"
        
        # Create keyboard with user buttons
        keyboard = []
        for user in users[:10]:  # Limit to first 10 users
            keyboard.append([
                InlineKeyboardButton(
                    f"{user['name']} (ID: {user['telegram_id']})", 
                    callback_data=f"user_{user['telegram_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔍 Search User", callback_data="delete_search")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="users_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return DELETE_USER_DATA
    
    else:
        # Unknown option
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Unknown option selected.",
            reply_markup=reply_markup
        )
        return USER_MANAGEMENT


def find_user_handler(update: Update, context: CallbackContext) -> int:
    """Handle user search"""
    # Check if this is a callback query
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        if query.data == "users_back":
            query.data = "users_list"
            return user_management_handler(update, context)
        
        return USER_MANAGEMENT
    
    # Get search term from message
    search_term = update.message.text.strip()
    
    # Store original message id for responding
    context.user_data['admin_msg_id'] = update.effective_message.message_id - 1
    
    # Search for users
    users = find_user_by_username(search_term)
    
    # Create response message
    if not users:
        response = f"No users found matching '{search_term}'"
    else:
        response = f"🔍 *SEARCH RESULTS*\n\nFound {len(users)} users matching '{search_term}':\n\n"
        
        for idx, user in enumerate(users[:10], start=1):  # Limit to first 10 results
            response += f"{idx}. *{user['name']}*\n"
            response += f"   ID: {user['telegram_id']}\n"
            response += f"   💰 Coins: {user['coins']}\n\n"
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to User Management", callback_data="users_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Edit the original message with results
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['admin_msg_id'],
            text=response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        # If editing fails, send a new message
        update.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return USER_MANAGEMENT


def give_coins_handler(update: Update, context: CallbackContext) -> int:
    """Handle giving coins to a user"""
    query = update.callback_query
    query.answer()
    
    parts = query.data.split('_')
    action = parts[0]
    
    if action == 'users':
        # Go back to user management
        query.data = "users_list"; return user_management_handler(update, context)
        return USER_MENU
    
    elif action == 'coins':
        subaction = parts[1]
        
        if subaction == 'search':
            # Start user search
            keyboard = [
                [InlineKeyboardButton("⬅️ Cancel", callback_data="coins_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🔍 *SEARCH USER*\n\n"
                "Please enter a username to search for:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Store the return state
            context.user_data['search_return'] = 'give_coins'
            return FIND_USER
        
        elif subaction == 'cancel':
            # Return to user management
            query.data = "users_list"; return user_management_handler(update, context)
            return USER_MENU
        
        elif subaction == 'user':
            # User selected, get amount
            user_id = int(parts[2])
            context.user_data['target_user_id'] = user_id
            
            keyboard = [
                [
                    InlineKeyboardButton("100 coins", callback_data="amount_100"),
                    InlineKeyboardButton("500 coins", callback_data="amount_500")
                ],
                [
                    InlineKeyboardButton("1000 coins", callback_data="amount_1000"),
                    InlineKeyboardButton("5000 coins", callback_data="amount_5000")
                ],
                [InlineKeyboardButton("Custom Amount", callback_data="amount_custom")],
                [InlineKeyboardButton("⬅️ Cancel", callback_data="coins_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "💰 *GIVE COINS*\n\n"
                "Select an amount to give:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return GIVE_COINS
        
        return GIVE_COINS
    
    elif action == 'amount':
        amount = parts[1]
        user_id = context.user_data.get('target_user_id')
        
        if not user_id:
            # No user selected, return to user management
            query.data = "users_list"; return user_management_handler(update, context)
            return USER_MENU
        
        if amount == 'custom':
            # Ask for custom amount
            keyboard = [
                [InlineKeyboardButton("⬅️ Cancel", callback_data="coins_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "💰 *CUSTOM AMOUNT*\n\n"
                "Please enter the number of coins to give:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            context.user_data['awaiting_coins_amount'] = True
            return GIVE_COINS
        
        else:
            # Fixed amount selected
            amount = int(amount)
            success, result = update_user_coins(user_id, amount)
            
            if success:
                response = f"✅ Successfully added {amount} coins!\n\nNew balance: {result} coins"
            else:
                response = f"❌ Failed to add coins: {result}"
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to User Management", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                response,
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
    
    return USER_MANAGEMENT


def process_custom_coins(update: Update, context: CallbackContext) -> int:
    """Process custom coin amount input"""
    if not context.user_data.get('awaiting_coins_amount'):
        return USER_MANAGEMENT
    
    # Get amount from message
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        update.message.reply_text(
            "❌ Please enter a valid positive number."
        )
        return GIVE_COINS
    
    # Get target user
    user_id = context.user_data.get('target_user_id')
    if not user_id:
        update.message.reply_text(
            "❌ No user selected. Please try again."
        )
        return USER_MANAGEMENT
    
    # Update user coins
    success, result = update_user_coins(user_id, amount)
    
    # Create response
    if success:
        response = f"✅ Successfully added {amount} coins!\n\nNew balance: {result} coins"
    else:
        response = f"❌ Failed to add coins: {result}"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to User Management", callback_data="users_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send response as new message
    update.message.reply_text(
        response,
        reply_markup=reply_markup
    )
    
    # Clear awaiting flag
    context.user_data['awaiting_coins_amount'] = False
    
    return USER_MANAGEMENT


def give_player_handler(update: Update, context: CallbackContext) -> int:
    """Handle giving a player to a user"""
    query = update.callback_query
    query.answer()
    
    parts = query.data.split('_')
    action = parts[0]
    
    if action == 'users':
        # Go back to user management
        query.data = "users_list"; return user_management_handler(update, context)
        return USER_MENU
    
    elif action == 'player':
        subaction = parts[1]
        
        if subaction == 'search':
            # Start user search
            keyboard = [
                [InlineKeyboardButton("⬅️ Cancel", callback_data="player_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🔍 *SEARCH USER*\n\n"
                "Please enter a username to search for:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Store the return state
            context.user_data['search_return'] = 'give_player'
            return FIND_USER
        
        elif subaction == 'cancel':
            # Return to user management
            query.data = "users_list"; return user_management_handler(update, context)
            return USER_MENU
        
        elif subaction == 'user':
            # User selected, search for player
            user_id = int(parts[2])
            context.user_data['target_user_id'] = user_id
            
            # Get available players through search function
            players = search_players("")
            
            if not players:
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back", callback_data="player_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    "No players found in the system.",
                    reply_markup=reply_markup
                )
                return GIVE_PLAYER
            
            # Display list of players with pagination
            page = context.user_data.get('player_page', 1)
            items_per_page = 5
            total_pages = (len(players) + items_per_page - 1) // items_per_page
            
            # Ensure page is within bounds
            page = max(1, min(page, total_pages))
            context.user_data['player_page'] = page
            
            # Get players for current page
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(players))
            current_players = players[start_idx:end_idx]
            
            # Format player list
            from utils import get_tier_emoji
            response = f"🏏 *SELECT PLAYER* (Page {page}/{total_pages})\n\n"
            response += "Choose a player to give to the user:\n\n"
            
            # Create keyboard with player buttons
            keyboard = []
            for player in current_players:
                tier_emoji = get_tier_emoji(player['tier'])
                keyboard.append([
                    InlineKeyboardButton(
                        f"{tier_emoji} {player['name']} ({player['total_ovr']} OVR)",
                        callback_data=f"select_player_{player['id']}"
                    )
                ])
            
            # Add navigation buttons
            nav_row = []
            if page > 1:
                nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data="player_prev"))
            
            if page < total_pages:
                nav_row.append(InlineKeyboardButton("Next ▶️", callback_data="player_next"))
            
            if nav_row:
                keyboard.append(nav_row)
            
            keyboard.append([InlineKeyboardButton("🔍 Search Player", callback_data="player_search_player")])
            keyboard.append([InlineKeyboardButton("⬅️ Cancel", callback_data="player_cancel")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return SELECT_PLAYER
        
        elif subaction == 'prev':
            # Go to previous player page
            context.user_data['player_page'] = context.user_data.get('player_page', 1) - 1
            
            # Simulate a user selection to refresh the list
            query.data = f"player_user_{context.user_data.get('target_user_id')}"
            return give_player_handler(update, context)
        
        elif subaction == 'next':
            # Go to next player page
            context.user_data['player_page'] = context.user_data.get('player_page', 1) + 1
            
            # Simulate a user selection to refresh the list
            query.data = f"player_user_{context.user_data.get('target_user_id')}"
            return give_player_handler(update, context)
        
        elif subaction == 'search_player':
            # Start player search
            keyboard = [
                [InlineKeyboardButton("⬅️ Cancel", callback_data="player_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🔍 *SEARCH PLAYER*\n\n"
                "Please enter a player name to search for:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Store the return state
            context.user_data['search_return'] = 'give_player'
            return SEARCH_PLAYER
    
    elif action == 'select':
        subaction = parts[1]
        
        if subaction == 'player':
            # Player selected, confirm
            player_id = int(parts[2])
            context.user_data['selected_player_id'] = player_id
            
            # Get player details
            from db import get_player
            player = get_player(player_id)
            
            if not player:
                query.edit_message_text(
                    "❌ Player not found. Please try again."
                )
                return GIVE_PLAYER
            
            # Get user details
            user_id = context.user_data.get('target_user_id')
            from db import get_or_create_user
            user = get_or_create_user(user_id)
            
            # Format confirmation message
            from utils import get_tier_emoji, format_player_info
            tier_emoji = get_tier_emoji(player['tier'])
            
            response = f"🎮 *CONFIRM PLAYER GIFT*\n\n"
            response += f"Are you sure you want to give the following player to *{user['name']}*?\n\n"
            response += f"{tier_emoji} *{player['name']}* ({player['total_ovr']} OVR)\n"
            response += f"Role: {player['role']} • Team: {player['team']}\n\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
                    InlineKeyboardButton("❌ Cancel", callback_data="confirm_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return CONFIRM_GIVE
    
    elif action == 'confirm':
        choice = parts[1]
        
        if choice == 'no':
            # Return to user management
            query.data = "users_list"; return user_management_handler(update, context)
            return USER_MENU
        
        elif choice == 'yes':
            # Give player to user
            user_id = context.user_data.get('target_user_id')
            player_id = context.user_data.get('selected_player_id')
            
            if not user_id or not player_id:
                query.edit_message_text(
                    "❌ Missing user or player ID. Please try again."
                )
                return USER_MANAGEMENT
            
            # Give player to user
            success, result = give_player_to_user(user_id, player_id)
            
            # Create response
            if success:
                response = f"✅ {result}"
            else:
                response = f"❌ Failed: {result}"
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to User Management", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                response,
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
    
    return GIVE_PLAYER


def search_player_handler(update: Update, context: CallbackContext) -> int:
    """Handle player search"""
    # Check if this is a callback query
    if update.callback_query:
        query = update.callback_query
        query.answer()
        
        if query.data == "player_cancel":
            query.data = "users_list"; return user_management_handler(update, context)
            return USER_MENU
        
        return SELECT_PLAYER
    
    # Get search term from message
    search_term = update.message.text.strip()
    
    # Store original message id for responding
    context.user_data['admin_msg_id'] = update.effective_message.message_id - 1
    
    # Search for players
    from db import search_players
    players = search_players(search_term)
    
    # Create keyboard with player buttons
    from utils import get_tier_emoji
    keyboard = []
    
    if not players:
        response = f"No players found matching '{search_term}'"
    else:
        response = f"🔍 *SEARCH RESULTS*\n\nFound {len(players)} players matching '{search_term}':\n\n"
        
        # Add player buttons
        for player in players[:10]:  # Limit to first 10 results
            tier_emoji = get_tier_emoji(player['tier'])
            keyboard.append([
                InlineKeyboardButton(
                    f"{tier_emoji} {player['name']} ({player['total_ovr']} OVR)",
                    callback_data=f"select_player_{player['id']}"
                )
            ])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("⬅️ Cancel", callback_data="player_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Edit the original message with results
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['admin_msg_id'],
            text=response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        # If editing fails, send a new message
        update.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return SELECT_PLAYER


# Pack Management Handlers
def pack_management_handler(update: Update, context: CallbackContext) -> int:
    """Handle pack management menu selections"""
    query = update.callback_query
    query.answer()
    
    # Check if we're returning from a pack action
    admin_action = context.user_data.get('admin_action')
    if admin_action:
        choice = admin_action.split('_')[1]
        # Clear it after use
        context.user_data.pop('admin_action', None)
    else:
        # Normal flow - get choice from callback data
        choice = query.data.split('_')[1]
    
    if choice == 'back':
        # Return to main menu
        # Direct implementation instead of await
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("🎮 Player Management", callback_data="admin_players")],
            [InlineKeyboardButton("📦 Pack Management", callback_data="admin_packs")],
            [InlineKeyboardButton("❌ Exit Admin Panel", callback_data="admin_exit")]
        ])
        query.edit_message_text(
            "👨‍💼 <b>Admin Panel</b>\n\nSelect an option:",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
        return ADMIN_MENU
    
    elif choice == 'list':
        # List all packs
        from db import list_packs
        packs = list_packs(active_only=False)
        
        if not packs:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="packs_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "No packs found in the system.",
                reply_markup=reply_markup
            )
            return PACK_MANAGEMENT
        
        # Format pack list
        response = f"📦 *PACKS*\n\nFound {len(packs)} packs:\n\n"
        
        # Add buttons for each pack
        keyboard = []
        for pack in packs:
            status = "✅ Active" if pack['is_active'] else "❌ Inactive"
            keyboard.append([
                InlineKeyboardButton(
                    f"{pack['name']} ({status})",
                    callback_data=f"pack_view_{pack['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="packs_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return PACK_ACTION
    
    elif choice == 'create':
        # Start the addpack conversation
        query.edit_message_text(
            "Please use the /addpack command to create a new pack."
        )
        return ConversationHandler.END
    
    return PACK_MANAGEMENT


def pack_action_handler(update: Update, context: CallbackContext) -> int:
    """Handle pack actions (view, toggle, delete)"""
    query = update.callback_query
    query.answer()
    
    # Import needed functions at the beginning
    from db import get_pack, update_pack_status, delete_pack
    from utils import format_pack_info
    
    parts = query.data.split('_')
    action = parts[0]
    
    if action == 'packs':
        # Return to pack management
        return pack_management_handler(update, context)
    
    elif action == 'pack':
        subaction = parts[1]
        
        if subaction == 'confirm' and parts[2] == 'delete':
            # For 'pack_confirm_delete_X' format
            pack_id = int(parts[3])
        else:
            # For 'pack_view_X', 'pack_toggle_X', 'pack_delete_X' formats
            pack_id = int(parts[2])
        
        # Get pack details
        pack = get_pack(pack_id)
        
        if not pack:
            query.edit_message_text(
                f"❌ Pack with ID {pack_id} not found."
            )
            return PACK_MANAGEMENT
        
        if subaction == 'view':
            # View pack details
            pack_info = format_pack_info(pack)
            
            # Add action buttons
            status_text = "❌ Deactivate" if pack['is_active'] else "✅ Activate"
            keyboard = [
                [
                    InlineKeyboardButton(status_text, callback_data=f"pack_toggle_{pack_id}"),
                    InlineKeyboardButton("🗑️ Delete", callback_data=f"pack_delete_{pack_id}")
                ],
                [InlineKeyboardButton("⬅️ Back", callback_data="packs_list")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                pack_info,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return PACK_ACTION
        
        elif subaction == 'toggle':
            # Toggle pack active status
            new_status = not pack['is_active']
            try:
                success, message = update_pack_status(pack_id, new_status)
                
                if success:
                    status_word = "activated" if new_status else "deactivated"
                    response = f"✅ Pack '{pack['name']}' has been {status_word}."
                else:
                    response = f"❌ Failed to update pack status: {message}"
            except Exception as e:
                response = f"❌ Error updating pack status: {str(e)}"
            
            # Show confirmation message
            query.edit_message_text(response)
            
            # Wait a moment to show the confirmation message
            import asyncio
            import time; time.sleep(1)
            
            # Create a new context for pack list
            context.user_data['admin_action'] = 'packs_list'
            return pack_management_handler(update, context)
        
        elif subaction == 'delete':
            # Confirm delete pack
            keyboard = [
                [
                    InlineKeyboardButton("✅ Yes, delete", callback_data=f"pack_confirm_delete_{pack_id}"),
                    InlineKeyboardButton("❌ No, cancel", callback_data=f"pack_view_{pack_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"❓ Are you sure you want to delete the pack '{pack['name']}'?\n\n"
                f"This action cannot be undone.",
                reply_markup=reply_markup
            )
            return PACK_ACTION
        
        elif subaction == 'confirm':
            # Confirmed delete
            if parts[2] == 'delete':
                try:
                    success, message = delete_pack(pack_id)
                    
                    if success:
                        response = f"✅ Pack deleted successfully."
                    else:
                        response = f"❌ Failed to delete pack: {message}"
                except Exception as e:
                    response = f"❌ Error deleting pack: {str(e)}"
                
                # Show confirmation message
                query.edit_message_text(response)
                
                # Wait a moment to show the confirmation message
                import asyncio
                import time; time.sleep(1)
                
                # Create a new context for pack list
                context.user_data['admin_action'] = 'packs_list'
                return pack_management_handler(update, context)
    
    return PACK_ACTION


# Player Management Handlers
def player_management_handler(update: Update, context: CallbackContext) -> int:
    """Handle player management menu selections"""
    query = update.callback_query
    query.answer()
    
    choice = query.data.split('_')[1]
    
    if choice == 'back':
        # Return to main menu - Direct implementation instead of await
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("🎮 Player Management", callback_data="admin_players")],
            [InlineKeyboardButton("📦 Pack Management", callback_data="admin_packs")],
            [InlineKeyboardButton("❌ Exit Admin Panel", callback_data="admin_exit")]
        ])
        query.edit_message_text(
            "👨‍💼 <b>Admin Panel</b>\n\nSelect an option:",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
        return ADMIN_MENU
    
    elif choice == 'list':
        # List all players
        # Get players through search with empty string to get all
        players = search_players("")
        
        if not players:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="players_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "No players found in the system.",
                reply_markup=reply_markup
            )
            return PLAYER_MANAGEMENT
        
        # Paginate players
        page = context.user_data.get('player_page', 1)
        items_per_page = 5
        total_pages = (len(players) + items_per_page - 1) // items_per_page
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages))
        context.user_data['player_page'] = page
        
        # Get players for current page
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(players))
        current_players = players[start_idx:end_idx]
        
        # Format player list
        from utils import get_tier_emoji
        response = f"🏏 *PLAYERS* (Page {page}/{total_pages})\n\n"
        
        for player in current_players:
            tier_emoji = get_tier_emoji(player['tier'])
            response += f"{tier_emoji} *{player['name']}* ({player['total_ovr']} OVR)\n"
            response += f"   {player['role']} • {player['team']}\n\n"
        
        # Add navigation buttons
        keyboard = []
        
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data="players_prev"))
        
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ▶️", callback_data="players_next"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        keyboard.append([InlineKeyboardButton("🔍 Search Player", callback_data="players_search")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="players_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return PLAYER_MANAGEMENT
    
    elif choice == 'prev':
        # Go to previous page
        context.user_data['player_page'] = context.user_data.get('player_page', 1) - 1
        # Call list handler again
        query.data = 'players_list'
        return player_management_handler(update, context)
    
    elif choice == 'next':
        # Go to next page
        context.user_data['player_page'] = context.user_data.get('player_page', 1) + 1
        # Call list handler again
        query.data = 'players_list'
        return player_management_handler(update, context)
    
    elif choice == 'search':
        # Start player search
        keyboard = [
            [InlineKeyboardButton("⬅️ Cancel", callback_data="players_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "🔍 *SEARCH PLAYER*\n\n"
            "Please enter a player name or team to search for:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Set search return state
        context.user_data['search_return'] = 'player_management'
        return SEARCH_PLAYER
    
    elif choice == 'add':
        # Start the add player conversation
        query.edit_message_text(
            "Please use the /add command to add a new player."
        )
        return ConversationHandler.END
    
    return PLAYER_MANAGEMENT


# Cancel handler
def delete_user_data_handler(update: Update, context: CallbackContext) -> int:
    """Handle user data deletion process"""
    query = update.callback_query
    query.answer()
    
    data = query.data
    logger.info(f"Received callback data in delete_user_data_handler: {data}")
    logger.info(f"Current conversation state: {context.user_data.get('state', 'UNKNOWN')}")
    logger.info(f"Target user ID: {context.user_data.get('target_user_id', 'NONE')}")
    logger.info(f"Delete options: {context.user_data.get('delete_options', {})}")
    
    # Handle direct user selection first
    if data.startswith("user_") and len(data.split("_")) > 1:
        try:
            # Extract user ID from callback data
            user_id = int(data.split("_")[1])
            logger.info(f"Direct user selection: {user_id}")
            
            # Store the user ID in context
            context.user_data['target_user_id'] = user_id
            
            # Show deletion options
            keyboard = [
                [InlineKeyboardButton("✅ Delete ALL User Data", callback_data="delete_all_data")],
                [
                    InlineKeyboardButton("🎮 Delete Players Only", callback_data="delete_players_only"),
                    InlineKeyboardButton("💰 Delete Coins Only", callback_data="delete_coins_only")
                ],
                [
                    InlineKeyboardButton("🏏 Delete Teams Only", callback_data="delete_teams_only"),
                    InlineKeyboardButton("🛒 Delete Marketplace Only", callback_data="delete_market_only")
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🗑️ *DELETE USER DATA*\n\n"
                f"Select what to delete for user ID: {user_id}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return CONFIRM_DELETE
        except (ValueError, IndexError) as e:
            logger.error(f"Error processing user ID from callback data: {e}")
    
    # Special case for one-click delete options
    if data == "delete_all_data":
        user_id = context.user_data.get('target_user_id')
        if not user_id:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="users_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text("❌ No user selected for deletion.", reply_markup=reply_markup)
            return USER_MANAGEMENT
        
        # Set all options to True for complete deletion
        delete_options = {
            'players': True,
            'coins': True,
            'teams': True,
            'marketplace': True
        }
        
        # Show confirmation message
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete ALL Data", callback_data="delete_execute_all")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"⚠️ *CONFIRM COMPLETE DELETION*\n\n"
            f"Are you sure you want to delete ALL data for user with ID {user_id}?\n\n"
            f"This will delete:\n"
            f"• 🎮 Players\n"
            f"• 💰 Coins\n"
            f"• 🏏 Teams\n"
            f"• 🛒 Marketplace listings\n\n"
            f"This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        context.user_data['delete_options'] = delete_options
        return CONFIRM_DELETE
    
    # Handle one-click single option deletion
    elif data in ["delete_players_only", "delete_coins_only", "delete_teams_only", "delete_market_only"]:
        user_id = context.user_data.get('target_user_id')
        if not user_id:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="users_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text("❌ No user selected for deletion.", reply_markup=reply_markup)
            return USER_MANAGEMENT
        
        # Map the button to the correct option
        option_type = None
        option_name = None
        
        if data == "delete_players_only":
            option_type = "players"
            option_name = "🎮 Players"
        elif data == "delete_coins_only":
            option_type = "coins"
            option_name = "💰 Coins"
        elif data == "delete_teams_only":
            option_type = "teams"
            option_name = "🏏 Teams"
        elif data == "delete_market_only":
            option_type = "marketplace"
            option_name = "🛒 Marketplace listings"
        
        # Set just this option to True
        delete_options = {
            'players': option_type == "players",
            'coins': option_type == "coins",
            'teams': option_type == "teams",
            'marketplace': option_type == "marketplace"
        }
        
        # Show confirmation message
        keyboard = [
            [InlineKeyboardButton(f"✅ Yes, Delete {option_name}", callback_data=f"delete_execute_{option_type}")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"⚠️ *CONFIRM DELETION*\n\n"
            f"Are you sure you want to delete {option_name} for user with ID {user_id}?\n\n"
            f"This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        context.user_data['delete_options'] = delete_options
        return CONFIRM_DELETE
        
    # Special case for direct option clicks from the first selection menu
    elif data.startswith("delete_option_"):
        logger.info("This code should no longer be used with the new one-click approach")
        return DELETE_USER_DATA
    
    # Handle confirm button direct click
    if data == "delete_confirm":
        user_id = context.user_data.get('target_user_id')
        delete_options = context.user_data.get('delete_options', {})
        
        if not user_id:
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "❌ No user selected for deletion.",
                reply_markup=reply_markup
            )
            return USER_MANAGEMENT
        
        if not any(delete_options.values()):
            keyboard = [
                [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "❌ Please select at least one type of data to delete.",
                reply_markup=reply_markup
            )
            return DELETE_USER_DATA
        
        # Show confirmation screen
        options_text = []
        if delete_options.get('players', False):
            options_text.append("🎮 Players")
        if delete_options.get('coins', False):
            options_text.append("💰 Coins")
        if delete_options.get('teams', False):
            options_text.append("🏏 Teams")
        if delete_options.get('marketplace', False):
            options_text.append("🛒 Marketplace listings")
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete Data", callback_data="delete_execute")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"⚠️ *CONFIRM DELETION*\n\n"
            f"Are you sure you want to delete the following data for user with ID {user_id}?\n\n"
            f"• " + "\n• ".join(options_text) + "\n\n"
            f"This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRM_DELETE
    
    # For execute actions, directly handle any of the execute patterns
    if data.startswith("delete_execute"):
        # Handle any of our execute patterns (delete_execute, delete_execute_all, delete_execute_players, etc.)
        user_id = context.user_data.get('target_user_id')
        logger.info(f"Execute delete action - current user_id: {user_id}")
        
        # Store the current state for debugging purposes
        context.user_data['state'] = 'EXECUTING_DELETE'
        
        # For the specific type execution, set the appropriate options
        if data == "delete_execute_all":
            # Set all options for complete deletion
            delete_options = {
                'players': True,
                'coins': True,
                'teams': True,
                'marketplace': True
            }
            context.user_data['delete_options'] = delete_options
            logger.info("Setting all delete options for complete deletion")
        elif data == "delete_execute_players":
            delete_options = {'players': True, 'coins': False, 'teams': False, 'marketplace': False}
            context.user_data['delete_options'] = delete_options
        elif data == "delete_execute_coins":
            delete_options = {'players': False, 'coins': True, 'teams': False, 'marketplace': False}
            context.user_data['delete_options'] = delete_options
        elif data == "delete_execute_teams":
            delete_options = {'players': False, 'coins': False, 'teams': True, 'marketplace': False}
            context.user_data['delete_options'] = delete_options
        elif data == "delete_execute_marketplace":
            delete_options = {'players': False, 'coins': False, 'teams': False, 'marketplace': True}
            context.user_data['delete_options'] = delete_options
        
        # Get the options we need to delete
        delete_options = context.user_data.get('delete_options', {})
        
        # Execute the deletion
        logger.info(f"Executing deletion for user {user_id} with options: {delete_options}")
        success, message = delete_user_data(user_id, delete_options)
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Back to User Management", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if success:
            query.edit_message_text(
                f"✅ *SUCCESS*\n\n{message}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            query.edit_message_text(
                f"❌ *ERROR*\n\n{message}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        # Clear user data
        if 'delete_options' in context.user_data:
            del context.user_data['delete_options']
        if 'target_user_id' in context.user_data:
            del context.user_data['target_user_id']
        
        return USER_MANAGEMENT
    
    # Standard parsing for other callback patterns
    parts = data.split('_')
    
    if len(parts) < 2:
        # Invalid data
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "❌ Invalid option selected.",
            reply_markup=reply_markup
        )
        return USER_MANAGEMENT
    
    action = parts[0]
    subaction = parts[1] if len(parts) > 1 else None
    
    if action == 'users':
        # Go back to user management
        query.data = "users_list"
        return user_management_handler(update, context)
    
    elif action == 'delete':
        if subaction == 'search':
            # Start user search for deletion
            keyboard = [
                [InlineKeyboardButton("⬅️ Cancel", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🔍 *SEARCH USER*\n\n"
                "Please enter a username to search for:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Store the return state
            context.user_data['search_return'] = 'delete_user_data'
            return FIND_USER
        
        elif subaction == 'user' and len(parts) > 2:
            # User selected for deletion
            user_id = int(parts[2])
            context.user_data['target_user_id'] = user_id
            
            # Show direct deletion options
            keyboard = [
                [InlineKeyboardButton("✅ Delete ALL User Data", callback_data="delete_all_data")],
                [
                    InlineKeyboardButton("🎮 Delete Players Only", callback_data="delete_players_only"),
                    InlineKeyboardButton("💰 Delete Coins Only", callback_data="delete_coins_only")
                ],
                [
                    InlineKeyboardButton("🏏 Delete Teams Only", callback_data="delete_teams_only"),
                    InlineKeyboardButton("🛒 Delete Marketplace Only", callback_data="delete_market_only")
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                "🗑️ *DELETE USER DATA*\n\n"
                f"Select what to delete for user ID: {user_id}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return CONFIRM_DELETE
        
        elif subaction == 'option':
            # Toggle selection of an option
            if len(parts) < 3:
                return DELETE_USER_DATA
                
            option = parts[2]
            valid_options = ['players', 'coins', 'teams', 'marketplace']
            
            if option in valid_options:
                # Toggle the option
                if 'delete_options' not in context.user_data:
                    context.user_data['delete_options'] = {opt: False for opt in valid_options}
                
                context.user_data['delete_options'][option] = not context.user_data['delete_options'][option]
                logger.info(f"Toggled option {option} to {context.user_data['delete_options'][option]}")
                
                # Show updated options
                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"🎮 Players ✓" if context.user_data['delete_options']['players'] else "🎮 Players", 
                            callback_data="delete_option_players"
                        ),
                        InlineKeyboardButton(
                            f"💰 Coins ✓" if context.user_data['delete_options']['coins'] else "💰 Coins", 
                            callback_data="delete_option_coins"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            f"🏏 Teams ✓" if context.user_data['delete_options']['teams'] else "🏏 Teams", 
                            callback_data="delete_option_teams"
                        ),
                        InlineKeyboardButton(
                            f"🛒 Marketplace ✓" if context.user_data['delete_options']['marketplace'] else "🛒 Marketplace", 
                            callback_data="delete_option_marketplace"
                        )
                    ],
                    [InlineKeyboardButton("✅ Confirm Deletion", callback_data="delete_confirm")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="users_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    "🗑️ *DELETE USER DATA*\n\n"
                    "Select the type of data to delete (multiple selections possible):",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                return DELETE_USER_DATA
        
        elif subaction == 'confirm':
            # Confirm deletion of selected options
            user_id = context.user_data.get('target_user_id')
            delete_options = context.user_data.get('delete_options', {})
            
            if not user_id:
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back", callback_data="users_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    "❌ No user selected for deletion.",
                    reply_markup=reply_markup
                )
                return USER_MANAGEMENT
            
            if not any(delete_options.values()):
                keyboard = [
                    [InlineKeyboardButton("⬅️ Back", callback_data="delete_user_" + str(user_id))]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    "❌ Please select at least one type of data to delete.",
                    reply_markup=reply_markup
                )
                return DELETE_USER_DATA
            
            # Show confirmation screen
            options_text = []
            if delete_options.get('players', False):
                options_text.append("🎮 Players")
            if delete_options.get('coins', False):
                options_text.append("💰 Coins")
            if delete_options.get('teams', False):
                options_text.append("🏏 Teams")
            if delete_options.get('marketplace', False):
                options_text.append("🛒 Marketplace listings")
            
            keyboard = [
                [InlineKeyboardButton("✅ Yes, Delete Data", callback_data="delete_execute")],
                [InlineKeyboardButton("❌ No, Cancel", callback_data="delete_user_" + str(user_id))]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"⚠️ *CONFIRM DELETION*\n\n"
                f"Are you sure you want to delete the following data for user with ID {user_id}?\n\n"
                f"• " + "\n• ".join(options_text) + "\n\n"
                f"This action cannot be undone.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return CONFIRM_DELETE
        
        elif subaction == 'execute':
            # Execute deletion
            user_id = context.user_data.get('target_user_id')
            delete_options = context.user_data.get('delete_options', {})
            
            success, message = delete_user_data(user_id, delete_options)
            
            keyboard = [
                [InlineKeyboardButton("⬅️ Back to User Management", callback_data="users_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if success:
                query.edit_message_text(
                    f"✅ *SUCCESS*\n\n{message}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                query.edit_message_text(
                    f"❌ *ERROR*\n\n{message}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            # Clear user data
            if 'delete_options' in context.user_data:
                del context.user_data['delete_options']
            if 'target_user_id' in context.user_data:
                del context.user_data['target_user_id']
            
            return USER_MANAGEMENT
    
    # Default: return to user management
    query.data = "users_list"
    return user_management_handler(update, context)


def cancel_admin(update: Update, context: CallbackContext) -> int:
    """Cancel and end the conversation."""
    user = update.effective_user
    
    # Clear conversation data
    context.user_data.clear()
    
    update.message.reply_text(
        f"Admin panel closed. Type /admin to open it again."
    )
    
    return ConversationHandler.END