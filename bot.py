#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot initialization and configuration
"""

import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from handlers import (
    start, help_command, admin_command, deleteuser_command, deleteteam_command, add_player_start, 
    process_name, process_role, process_team, process_batting_type,
    process_bowling_type, process_batting_timing, process_batting_technique,
    process_batting_power, process_bowling_pace, process_bowling_variation,
    process_bowling_accuracy, process_player_image, process_tier, process_edition, cancel, 
    health_check, view_player, search_player, list_players, test_role_filter,
    marketplace, market_buy_handler, market_sell_handler, buy_confirm_handler, sell_player,
    sell_player_handler, market_listings_command, buy_player_command, set_price_command,
    # Manual OVR handlers
    process_manual_ovr_choice, process_batting_ovr, process_bowling_ovr, process_total_ovr,
    # Player management handlers
    delete_player_command, delete_player_callback, 
    # User and pack handlers
    user_profile, add_pack_start, manage_packs,
    view_pack, open_pack_command, my_players,
    # Pack creation handlers
    process_pack_name, process_pack_description, process_pack_price,
    process_pack_min_players, process_pack_max_players, process_pack_min_ovr,
    process_pack_max_ovr, process_pack_tiers, process_pack_image, process_pack_active,
    # Team management handlers
    create_team_start, process_team_name, process_team_description, skip_description,
    teams_menu, teams_callback_handler,
    # Special states for team management
    TEAM_MANAGEMENT, TEAM_VIEW, TEAM_EDIT, TEAM_ADD_PLAYER, PLAYER_POSITION
)
from match_handlers import (
    challenge_command, match_setup_handler, match_confirmation_handler,
    cancel_match, MATCH_SETUP, MATCH_CONFIRMATION, MATCH_IN_PROGRESS
)
# Tournament functionality has been removed
from admin_handlers import (
    admin_panel, admin_menu_handler, user_management_handler, find_user_handler,
    give_coins_handler, process_custom_coins, give_player_handler, search_player_handler,
    pack_management_handler, pack_action_handler, player_management_handler, cancel_admin,
    delete_user_data_handler,  # New handler for user data deletion
    # Admin panel states
    MAIN_MENU, USER_MANAGEMENT, PACK_MANAGEMENT, PLAYER_MANAGEMENT,
    FIND_USER, GIVE_COINS, GIVE_PLAYER, SEARCH_PLAYER,
    PACK_ACTION, SELECT_USER, SELECT_PLAYER, CONFIRM_GIVE,
)
from player_stats_handlers import (
    player_stats_command, my_stats_command, batting_leaderboard_command, 
    bowling_leaderboard_command
)
# States for admin user data deletion
DELETE_USER_DATA, CONFIRM_DELETE = range(54, 56)
from db import init_db

logger = logging.getLogger(__name__)

# Define conversation states for player addition
(
    NAME, ROLE, TEAM, BATTING_TYPE, BOWLING_TYPE, 
    BATTING_TIMING, BATTING_TECHNIQUE, BATTING_POWER,
    BOWLING_PACE, BOWLING_VARIATION, BOWLING_ACCURACY,
    MANUAL_OVR_CHOICE, BATTING_OVR, BOWLING_OVR, TOTAL_OVR,
    PLAYER_IMAGE, TIER, EDITION
) = range(18)

# Define conversation states for pack creation
(
    PACK_NAME, PACK_DESCRIPTION, PACK_PRICE, PACK_MIN_PLAYERS, 
    PACK_MAX_PLAYERS, PACK_MIN_OVR, PACK_MAX_OVR, PACK_TIERS,
    PACK_IMAGE, PACK_ACTIVE
) = range(17, 27)

# Define conversation states for team creation
CREATE_TEAM_NAME, CREATE_TEAM_DESCRIPTION = range(100, 102)


def async_to_sync(async_func):
    """Convert an async handler to a synchronous function for PTB v13 compatibility."""
    import asyncio
    import inspect
    
    def wrapper(update, context):
        # Check if the function is actually async or not
        if not inspect.iscoroutinefunction(async_func):
            # If it's not async, just call it directly
            return async_func(update, context)
            
        # Otherwise, handle it as an async function
        # Create a new event loop for this handler call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async function to completion
            return loop.run_until_complete(async_func(update, context))
        finally:
            # Clean up
            loop.close()
    
    return wrapper

def setup_bot():
    """Initialize and configure the bot with all required handlers"""
    
    # Initialize database
    init_db()
    
    # Get token from environment variable
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_TOKEN or TELEGRAM_BOT_TOKEN environment variable found")
        raise ValueError("TELEGRAM_TOKEN or TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Create the Updater and get the dispatcher
    # Add a unique session name to avoid conflicts with other instances
    updater = Updater(token=token, use_context=True, workers=4, request_kwargs={
        'read_timeout': 30, 'connect_timeout': 30
    })
    dispatcher = updater.dispatcher
    
    # Define conversation handler for player addition
    add_player_conv = ConversationHandler(
        entry_points=[CommandHandler('add', async_to_sync(add_player_start))],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_name))],
            ROLE: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_role))],
            TEAM: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_team))],
            BATTING_TYPE: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_batting_type)),
                CallbackQueryHandler(async_to_sync(process_batting_type), pattern=r'^batting_')
            ],
            BOWLING_TYPE: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_bowling_type)),
                CallbackQueryHandler(async_to_sync(process_bowling_type), pattern=r'^bowling_')
            ],
            BATTING_TIMING: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_batting_timing)),
                CallbackQueryHandler(async_to_sync(process_batting_timing), pattern=r'^timing_')
            ],
            BATTING_TECHNIQUE: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_batting_technique)),
                CallbackQueryHandler(async_to_sync(process_batting_technique), pattern=r'^technique_')
            ],
            BATTING_POWER: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_batting_power)),
                CallbackQueryHandler(async_to_sync(process_batting_power), pattern=r'^power_')
            ],
            BOWLING_PACE: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_bowling_pace)),
                CallbackQueryHandler(async_to_sync(process_bowling_pace), pattern=r'^pace_')
            ],
            BOWLING_VARIATION: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_bowling_variation)),
                CallbackQueryHandler(async_to_sync(process_bowling_variation), pattern=r'^variation_')
            ],
            BOWLING_ACCURACY: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_bowling_accuracy)),
                CallbackQueryHandler(async_to_sync(process_bowling_accuracy), pattern=r'^accuracy_')
            ],
            MANUAL_OVR_CHOICE: [CallbackQueryHandler(async_to_sync(process_manual_ovr_choice))],
            BATTING_OVR: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_batting_ovr)),
                CallbackQueryHandler(async_to_sync(process_batting_ovr), pattern=r'^batting_ovr_')
            ],
            BOWLING_OVR: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_bowling_ovr)),
                CallbackQueryHandler(async_to_sync(process_bowling_ovr), pattern=r'^bowling_ovr_')
            ],
            TOTAL_OVR: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_total_ovr)),
                CallbackQueryHandler(async_to_sync(process_total_ovr), pattern=r'^total_ovr_')
            ],
            PLAYER_IMAGE: [MessageHandler(Filters.text | Filters.photo, async_to_sync(process_player_image))],
            TIER: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_tier)),
                CallbackQueryHandler(async_to_sync(process_tier), pattern=r'^tier_')
            ],
            EDITION: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_edition)),
                CallbackQueryHandler(async_to_sync(process_edition), pattern=r'^edition_')
            ],
        },
        fallbacks=[CommandHandler('cancel', async_to_sync(cancel))],
        per_message=False  # Allow the same handler to be used for text messages and callbacks
    )
    
    # Add command handlers with async-to-sync adapter
    dispatcher.add_handler(CommandHandler("start", async_to_sync(start)))
    dispatcher.add_handler(CommandHandler("help", async_to_sync(help_command)))
    dispatcher.add_handler(CommandHandler("admin", async_to_sync(admin_command)))
    dispatcher.add_handler(CommandHandler("deleteteam", async_to_sync(deleteteam_command)))
    dispatcher.add_handler(CommandHandler("health", async_to_sync(health_check)))
    dispatcher.add_handler(CommandHandler("test_filter", async_to_sync(test_role_filter)))
    dispatcher.add_handler(CommandHandler("view", async_to_sync(view_player)))
    dispatcher.add_handler(CommandHandler("search", async_to_sync(search_player)))
    dispatcher.add_handler(CommandHandler("list", async_to_sync(list_players)))
    dispatcher.add_handler(CommandHandler("deleteuser", async_to_sync(deleteuser_command)))
    
    # Add player management handlers
    dispatcher.add_handler(CommandHandler("delete", async_to_sync(delete_player_command)))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(delete_player_callback), pattern=r'^delete_'))
    
    # Add user and pack handlers
    dispatcher.add_handler(CommandHandler("profile", async_to_sync(user_profile)))
    dispatcher.add_handler(CommandHandler("packs", async_to_sync(manage_packs)))
    dispatcher.add_handler(CommandHandler("viewpack", async_to_sync(view_pack)))
    dispatcher.add_handler(CommandHandler("openpack", async_to_sync(open_pack_command)))
    dispatcher.add_handler(CommandHandler("myplayers", async_to_sync(my_players)))
    
    # Add marketplace handlers
    dispatcher.add_handler(CommandHandler("market", async_to_sync(marketplace)))
    dispatcher.add_handler(CommandHandler("listings", async_to_sync(market_listings_command)))
    dispatcher.add_handler(CommandHandler("setprice", async_to_sync(set_price_command)))
    dispatcher.add_handler(CommandHandler("sell", async_to_sync(sell_player)))
    dispatcher.add_handler(CommandHandler("buy", async_to_sync(buy_player_command)))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(market_buy_handler), pattern=r'^market_buy_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(market_sell_handler), pattern=r'^market_sell_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(sell_player_handler), pattern=r'^sell_player_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(buy_confirm_handler), pattern=r'^buy_confirm_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(marketplace), pattern=r'^market_main$'))
    
    # Add new interactive team management handlers
    dispatcher.add_handler(CommandHandler("teams", async_to_sync(teams_menu)))
    
    # Team management conversation handler for interactive team management
    team_management_handler = ConversationHandler(
        entry_points=[
            CommandHandler("teams", async_to_sync(teams_menu)),
            CallbackQueryHandler(async_to_sync(teams_callback_handler), pattern=r'^team_|^view_team_|^add_player_|^remove_player_|^edit_team_|^delete_team_|^confirm_delete_team_|^back_to_team_menu$')
        ],
        states={
            TEAM_MANAGEMENT: [
                # Expanded pattern to include all team-related callbacks
                CallbackQueryHandler(async_to_sync(teams_callback_handler), pattern=r'^team_|^view_team_|^back_to_team_menu$|^delete_team_|^confirm_delete_team_')
            ],
            TEAM_VIEW: [
                # Made sure confirm_delete_team_ is properly handled
                CallbackQueryHandler(async_to_sync(teams_callback_handler), pattern=r'^team_|^view_team_|^add_player_|^remove_player_|^edit_team_|^delete_team_|^confirm_delete_team_|^remove_pl_|^filter_')
            ],
            TEAM_ADD_PLAYER: [
                CallbackQueryHandler(async_to_sync(teams_callback_handler), pattern=r'^select_player_|^view_team_|^filter_|^add_player_')
            ],
            PLAYER_POSITION: [
                CallbackQueryHandler(async_to_sync(teams_callback_handler), pattern=r'^position_|^view_team_')
            ]
        },
        fallbacks=[CommandHandler("cancel", async_to_sync(cancel))],
        per_message=False,  # This is important for callback handlers
    )
    dispatcher.add_handler(team_management_handler)
    
    # Add callback handlers for pack operations
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(open_pack_command), pattern=r'^pack_open_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(open_pack_command), pattern=r'^openpack_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(view_pack), pattern=r'^viewpack_'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(manage_packs), pattern=r'^packs_view'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(my_players), pattern=r'^myplayers_view'))
    dispatcher.add_handler(CallbackQueryHandler(async_to_sync(my_players), pattern=r'^myplayers_page_'))
    
    # Define conversation handler for pack creation
    add_pack_conv = ConversationHandler(
        entry_points=[CommandHandler('addpack', async_to_sync(add_pack_start))],
        states={
            PACK_NAME: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_name))],
            PACK_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_description))],
            PACK_PRICE: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_price))],
            PACK_MIN_PLAYERS: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_min_players))],
            PACK_MAX_PLAYERS: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_max_players))],
            PACK_MIN_OVR: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_min_ovr))],
            PACK_MAX_OVR: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_max_ovr))],
            PACK_TIERS: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_tiers))],
            PACK_IMAGE: [MessageHandler(Filters.text | Filters.photo, async_to_sync(process_pack_image))],
            PACK_ACTIVE: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_pack_active)),
                CallbackQueryHandler(async_to_sync(process_pack_active), pattern=r'^pack_active_')
            ],
        },
        fallbacks=[CommandHandler('cancel', async_to_sync(cancel))],
        per_message=False  # Allow the same handler to be used for text messages and callbacks
    )
    
    # Define conversation handler for admin panel
    admin_panel_conv = ConversationHandler(
        entry_points=[CommandHandler('adminpanel', async_to_sync(admin_panel))],
        states={
            MAIN_MENU: [CallbackQueryHandler(async_to_sync(admin_menu_handler), pattern=r'^admin_')],
            USER_MANAGEMENT: [
                CallbackQueryHandler(async_to_sync(user_management_handler), pattern=r'^users_'),
                CallbackQueryHandler(async_to_sync(give_coins_handler), pattern=r'^coins_'),
                CallbackQueryHandler(async_to_sync(give_player_handler), pattern=r'^player_'),
                CallbackQueryHandler(async_to_sync(delete_user_data_handler), pattern=r'^delete_'),
            ],
            FIND_USER: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(find_user_handler)),
                CallbackQueryHandler(async_to_sync(find_user_handler), pattern=r'^users_')
            ],
            GIVE_COINS: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_custom_coins)),
                CallbackQueryHandler(async_to_sync(give_coins_handler), pattern=r'^(amount_|coins_)')
            ],
            GIVE_PLAYER: [
                CallbackQueryHandler(async_to_sync(give_player_handler), pattern=r'^player_')
            ],
            SEARCH_PLAYER: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(search_player_handler)),
                CallbackQueryHandler(async_to_sync(search_player_handler), pattern=r'^player_')
            ],
            SELECT_PLAYER: [
                CallbackQueryHandler(async_to_sync(give_player_handler), pattern=r'^(select_player_|player_)')
            ],
            CONFIRM_GIVE: [
                CallbackQueryHandler(async_to_sync(give_player_handler), pattern=r'^confirm_')
            ],
            PACK_MANAGEMENT: [
                CallbackQueryHandler(async_to_sync(pack_management_handler), pattern=r'^packs_')
            ],
            PACK_ACTION: [
                CallbackQueryHandler(async_to_sync(pack_action_handler), pattern=r'^(pack_|packs_)')
            ],
            PLAYER_MANAGEMENT: [
                CallbackQueryHandler(async_to_sync(player_management_handler), pattern=r'^players_')
            ],
            DELETE_USER_DATA: [
                CallbackQueryHandler(async_to_sync(delete_user_data_handler))
            ],
            CONFIRM_DELETE: [
                CallbackQueryHandler(async_to_sync(delete_user_data_handler), pattern=r'^delete_execute|^delete_all_data|^delete_players_only|^delete_coins_only|^delete_teams_only|^delete_market_only|^delete_confirm|^users_back$')
            ]
        },
        fallbacks=[CommandHandler('cancel', async_to_sync(cancel_admin))],
        per_message=False
    )
    
    # Define conversation handler for team creation
    create_team_conv = ConversationHandler(
        entry_points=[CommandHandler('create_team', async_to_sync(create_team_start))],
        states={
            CREATE_TEAM_NAME: [MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_team_name))],
            CREATE_TEAM_DESCRIPTION: [
                MessageHandler(Filters.text & ~Filters.command, async_to_sync(process_team_description)),
                CommandHandler('skip', async_to_sync(skip_description))
            ],
        },
        fallbacks=[CommandHandler('cancel', async_to_sync(cancel))],
        per_message=False
    )

    # Define the match challenge conversation handler (simplified version)
    match_challenge_handler = ConversationHandler(
        entry_points=[CommandHandler('challenge', async_to_sync(challenge_command))],
        states={
            MATCH_CONFIRMATION: [
                CallbackQueryHandler(async_to_sync(match_confirmation_handler), pattern=r'^accept_challenge|^decline_challenge$')
            ],
            MATCH_IN_PROGRESS: [
                # No handlers needed for the match simulation itself
            ]
        },
        fallbacks=[CommandHandler('cancel', async_to_sync(cancel))],
        per_message=False,
        # Use chat_data to share context between users in the same chat
        per_chat=True,
        # Allow nested conversations to ensure both users can interact
        allow_reentry=True
    )
    
    # Add command for canceling matches (admin only)
    dispatcher.add_handler(CommandHandler('cancel_match', async_to_sync(cancel_match)))
    
    # Add the conversation handlers
    dispatcher.add_handler(add_player_conv)
    dispatcher.add_handler(add_pack_conv)
    dispatcher.add_handler(admin_panel_conv) 
    dispatcher.add_handler(create_team_conv)
    dispatcher.add_handler(match_challenge_handler)
    
    # Add player statistics handlers
    dispatcher.add_handler(CommandHandler("playerstats", async_to_sync(player_stats_command)))
    dispatcher.add_handler(CommandHandler("mystats", async_to_sync(my_stats_command)))
    dispatcher.add_handler(CommandHandler("battingleaderboard", async_to_sync(batting_leaderboard_command)))
    dispatcher.add_handler(CommandHandler("bowlingleaderboard", async_to_sync(bowling_leaderboard_command)))
    
    # Tournament functionality has been removed
    
    # Define error handler
    def error_handler(update, context):
        """Log errors caused by updates."""
        logger.error("Exception while handling an update:", exc_info=context.error)
        # Send a message to the user
        if update and update.effective_chat:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An error occurred while processing your request. The developers have been notified."
            )
    
    # Register the error handler
    dispatcher.add_error_handler(error_handler)
    
    logger.info("Bot configuration completed")
    
    # Return the updater object so it can be stopped externally
    return updater