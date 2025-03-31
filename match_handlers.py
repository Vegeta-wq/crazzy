"""
Match challenge and gameplay handlers for the Cricket Game Bot
"""

import logging
import random
import time
from typing import Dict, List, Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import CallbackContext, ConversationHandler
from telegram.error import RetryAfter, TelegramError, TimedOut, NetworkError

from db import get_user_teams, get_team, get_user_coins, update_user_coins
from match_engine import CricketMatch, Player, Team
from telegram_utils import send_message_safely, edit_message_safely, answer_callback_safely

# States for the match challenge conversation
MATCH_SETUP = 1
MATCH_CONFIRMATION = 2
MATCH_IN_PROGRESS = 3

# Logger
logger = logging.getLogger(__name__)

# Dictionary to track active matches
active_matches = {}  # {match_id: CricketMatch object}

def challenge_command(update: Update, context: CallbackContext) -> int:
    """Start a match challenge by replying to another user's message"""
    user = update.effective_user
    
    # Check if the command was used in a reply
    if update.message.reply_to_message is None:
        update.message.reply_text(
            "You need to reply to another user's message with /challenge to challenge them to a match."
        )
        return ConversationHandler.END
    
    # Get the opponent user
    opponent = update.message.reply_to_message.from_user
    
    # Don't allow challenging yourself
    if opponent.id == user.id:
        update.message.reply_text("You can't challenge yourself to a match!")
        return ConversationHandler.END
    
    # Get challenger's teams
    challenger_teams = get_user_teams(user.id)
    
    if not challenger_teams:
        update.message.reply_text(
            "You don't have any teams to play with. Use /create_team to create a team first."
        )
        return ConversationHandler.END
    
    # Get opponent's teams
    opponent_teams = get_user_teams(opponent.id)
    
    if not opponent_teams:
        update.message.reply_text(
            f"{opponent.first_name} doesn't have any teams to play with."
        )
        return ConversationHandler.END
    
    # Automatically select the first team for the challenger
    challenger_team = challenger_teams[0]
    challenger_team_id = challenger_team['id']
    challenger_team_name = challenger_team['name']
    
    # Get detailed challenger team data
    challenger_team_details = get_team(challenger_team_id, user.id)
    if not challenger_team_details:
        update.message.reply_text("Error: Your team couldn't be found. Please try again.")
        return ConversationHandler.END
    
    # Calculate challenger team rating
    challenger_players = challenger_team_details.get('players', [])
    challenger_player_count = len(challenger_players)
    challenger_team_rating = 0
    
    if challenger_player_count > 0:
        player_ovrs = [p.get('total_ovr', 0) for p in challenger_players]
        challenger_team_rating = sum(player_ovrs) // challenger_player_count if player_ovrs else 0
    
    # Store user and opponent IDs in chat_data to make it accessible to both users
    match_key = f"match_{user.id}_{opponent.id}"
    context.chat_data[match_key] = {
        'challenger_id': user.id,
        'challenger_name': user.first_name,
        'opponent_id': opponent.id,
        'opponent_name': opponent.first_name,
        'match_state': 'setup',
        'match_cost': 100,  # Default match cost (simplify with fixed cost)
        'challenger_team_id': challenger_team_id,
        'challenger_team_name': challenger_team_name
    }
    
    # Store match key in user_data for both users for easy reference
    context.user_data['current_match_key'] = match_key
    
    # Create keyboard buttons for the different match costs
    # Include match_key in callback data for proper tracking
    keyboard = [
        [InlineKeyboardButton("Accept (100 coins)", callback_data=f"accept_challenge:{match_key}")],
        [InlineKeyboardButton("❌ Decline", callback_data=f"decline_challenge:{match_key}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the challenge message
    message = update.message.reply_text(
        f"🏏 MATCH CHALLENGE 🏏\n\n"
        f"{user.first_name} is challenging {opponent.first_name} to a cricket match!\n\n"
        f"Challenger: {user.first_name}\n"
        f"Team: {challenger_team_name} (OVR: {challenger_team_rating})\n\n"
        f"Entry Cost: 100 coins\n"
        f"Winner gets: 200 coins\n\n"
        f"{opponent.first_name}, do you accept?",
        reply_markup=reply_markup
    )
    
    # Save message ID for later edits
    context.user_data['setup_message_id'] = message.message_id
    
    return MATCH_CONFIRMATION

def match_setup_handler(update: Update, context: CallbackContext) -> int:
    """Handle team selection and match setup"""
    query = update.callback_query
    query.answer()
    
    # Get the match key from user_data
    match_key = context.user_data.get('current_match_key')
    
    # If match_key exists, get match data from chat_data
    if match_key and match_key in context.chat_data:
        match_data = context.chat_data[match_key]
        challenger_id = match_data.get('challenger_id')
    else:
        # Fallback to user_data for backward compatibility
        challenger_id = context.user_data.get('challenger_id')
    
    # If we still don't have challenger_id, we can't proceed
    if not challenger_id:
        query.edit_message_text("Error: Match data not found. Please start a new challenge.")
        return ConversationHandler.END
    
    # Ensure only the challenger can proceed with this step
    if query.from_user.id != challenger_id:
        query.answer("Only the challenger can select teams and setup the match.", show_alert=True)
        return MATCH_SETUP
    
    # Handle cancel (both with and without match key)
    if query.data == "cancel_challenge" or query.data.startswith("decline_challenge:"):
        query.edit_message_text("Match challenge cancelled.")
        return ConversationHandler.END
    
    # Handle team selection by challenger
    if query.data.startswith("select_team_"):
        # Extract team ID from callback data
        team_id = int(query.data.split("_")[-1])
        
        # Store team ID in both user_data and chat_data for better reliability
        context.user_data['challenger_team_id'] = team_id
        
        # Also store in chat_data if we have a match key
        match_key = context.user_data.get('current_match_key')
        if match_key and match_key in context.chat_data:
            context.chat_data[match_key]['challenger_team_id'] = team_id
            logger.debug(f"Stored challenger team ID {team_id} in chat_data[{match_key}]")
        
        # Get team details
        team = get_team(team_id, challenger_id)
        if not team:
            query.edit_message_text("Error: Team not found.")
            return ConversationHandler.END
        
        # Store team name in both user_data and chat_data
        context.user_data['challenger_team_name'] = team['name']
        
        if match_key and match_key in context.chat_data:
            context.chat_data[match_key]['challenger_team_name'] = team['name']
            logger.debug(f"Stored challenger team name '{team['name']}' in chat_data[{match_key}]")
        
        # Get opponent's ID and name
        # First check if we have match data in chat_data
        match_key = context.user_data.get('current_match_key')
        if match_key and match_key in context.chat_data:
            opponent_id = context.chat_data[match_key].get('opponent_id')
            opponent_name = context.chat_data[match_key].get('opponent_name', 'Your opponent')
        else:
            # Fallback to user_data
            opponent_id = context.user_data.get('opponent_id')
            opponent_name = context.user_data.get('opponent_name', 'Your opponent')
        
        # Debug log
        logger.debug(f"Getting teams for opponent ID: {opponent_id}, name: {opponent_name}")
        
        # Get opponent teams
        opponent_teams = get_user_teams(opponent_id) if opponent_id else []
        logger.debug(f"Opponent teams: {opponent_teams}")
        
        if not opponent_teams:
            query.edit_message_text(
                f"{opponent_name} doesn't have any teams to play with."
            )
            return ConversationHandler.END
        
        # Since opponent has teams, we'll let them select their own team when they accept
        # Now prompt challenger to select match cost
        
        # Create match cost selection keyboard
        keyboard = [
            [InlineKeyboardButton("100 coins", callback_data="confirm_100")],
            [InlineKeyboardButton("250 coins", callback_data="confirm_250")],
            [InlineKeyboardButton("500 coins", callback_data="confirm_500")],
            [InlineKeyboardButton("1000 coins", callback_data="confirm_1000")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_challenge")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get opponent name from the match data
        match_key = context.user_data.get('current_match_key')
        if match_key and match_key in context.chat_data:
            opponent_name = context.chat_data[match_key].get('opponent_name', 'Your opponent')
        else:
            opponent_name = context.user_data.get('opponent_name', 'Your opponent')
            
        query.edit_message_text(
            f"You selected: {context.user_data['challenger_team_name']}\n\n"
            f"How many coins do you want to wager on this match?\n"
            f"(Both players will need to pay this amount, winner gets double)",
            reply_markup=reply_markup
        )
        
        return MATCH_SETUP
    
    # Handle opponent team selection (from the opponent, after accepting a challenge)
    if query.data.startswith("select_opponent_team_"):
        # Extract team ID from callback data
        team_id = int(query.data.split("_")[-1])
        
        # Get match key from user_data
        match_key = context.user_data.get('current_match_key')
        
        # Get match data
        if match_key and match_key in context.chat_data:
            match_data = context.chat_data[match_key]
            challenger_id = match_data.get('challenger_id')
            opponent_id = match_data.get('opponent_id')
            
            # Get match cost from chat_data
            match_cost = match_data.get('match_cost', 100)
        else:
            # Fallback to user_data
            challenger_id = context.user_data.get('challenger_id')
            opponent_id = context.user_data.get('opponent_id')
            match_cost = context.user_data.get('match_cost_pending', 100)
        
        # Verify this is coming from the opponent
        if query.from_user.id != opponent_id:
            query.answer("Only the opponent can select their team.", show_alert=True)
            return MATCH_CONFIRMATION
        
        # Deduct coins from opponent now that they've selected their team
        update_user_coins(opponent_id, -match_cost)
        
        # Store team details 
        team = get_team(team_id, opponent_id)
        if not team:
            query.edit_message_text("Error: Team not found. Please start a new challenge.")
            # Refund both players since we can't continue
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
        
        # Store in chat_data and user_data
        context.user_data['opponent_team_id'] = team_id
        context.user_data['opponent_team_name'] = team['name']
        
        if match_key and match_key in context.chat_data:
            context.chat_data[match_key]['opponent_team_id'] = team_id
            context.chat_data[match_key]['opponent_team_name'] = team['name']
        
        # Update message
        loading_msg = query.edit_message_text(
            f"Match setup complete! ⚡ Starting the match..."
        )
        
        # Get the challenger's team details
        challenger_team_id = None
        if match_key and match_key in context.chat_data:
            challenger_team_id = context.chat_data[match_key].get('challenger_team_id')
        
        if not challenger_team_id:
            error_msg = f"Error: Could not find challenger's team."
            logger.error(error_msg)
            loading_msg.edit_text(error_msg)
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
        
        # Get team details with better error handling
        challenger_team = None
        opponent_team = None
        
        try:
            challenger_team = get_team(challenger_team_id, challenger_id)
            logger.debug(f"Challenger team details: {challenger_team}")
        except Exception as e:
            logger.error(f"Error getting challenger team: {e}")
            
        try:
            opponent_team = get_team(team_id, opponent_id)
            logger.debug(f"Opponent team details: {opponent_team}")
        except Exception as e:
            logger.error(f"Error getting opponent team: {e}")
        
        if not challenger_team:
            error_msg = f"Error: Could not load challenger's team (ID: {challenger_team_id})."
            logger.error(error_msg)
            loading_msg.edit_text(error_msg)
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
            
        if not opponent_team:
            error_msg = f"Error: Could not load opponent's team (ID: {team_id})."
            logger.error(error_msg)
            loading_msg.edit_text(error_msg)
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
        
        # Get team names
        challenger_team_name = challenger_team.get('name', 'Team 1')
        opponent_team_name = team['name']
        
        # Convert DB team format to match engine Team objects
        challenger_team_obj = create_team_obj(
            challenger_team, 
            challenger_team_name, 
            challenger_id
        )
        
        opponent_team_obj = create_team_obj(
            opponent_team, 
            opponent_team_name, 
            opponent_id
        )
        
        # Start the match
        match_id = f"{challenger_id}_{opponent_id}_{int(time.time())}"
        context.user_data['match_id'] = match_id
        
        # Get challenger and opponent names
        if match_key and match_key in context.chat_data:
            challenger_name = context.chat_data[match_key].get('challenger_name', 'Challenger')
            opponent_name = context.chat_data[match_key].get('opponent_name', 'Opponent')
        else:
            challenger_name = context.user_data.get('challenger_name', 'Challenger')
            opponent_name = query.from_user.first_name
        
        # Create match object
        try:
            # Define dummy functions to handle the None type errors
            def dummy_scorecard_func(data):
                # This function is never called, we handle scorecards in simulate_match
                pass
            
            def dummy_match_end_func(data):
                # This function is never called, we handle match end in simulate_match
                pass
            
            # Create a wrapper function for sending messages
            def telegram_message_wrapper(message_data):
                """Adapts the dictionary-based message data to Telegram's bot.send_message format"""
                # Get chat_id from match or use the update's chat_id
                chat_id = update.effective_chat.id
                
                # Extract message text
                if "commentary" in message_data:
                    text = message_data["commentary"]
                elif "message" in message_data:
                    text = message_data["message"]
                elif "event" in message_data:
                    # Build appropriate message based on event type
                    event = message_data.get("event")
                    if event == "match_start":
                        text = f"🏏 MATCH START 🏏\n\n{message_data.get('commentary', '')}"
                    elif event == "innings_break":
                        team = message_data.get("team", "")
                        score = message_data.get("score", 0)
                        wickets = message_data.get("wickets", 0)
                        overs = message_data.get("overs", 0)
                        balls = message_data.get("balls", 0)
                        text = f"🏏 INNINGS COMPLETE 🏏\n\n{team}: {score}/{wickets} ({overs}.{balls} overs)"
                    else:
                        # Default fallback for unknown events
                        text = f"Match update: {message_data}"
                else:
                    # Default fallback
                    text = f"Match update: {message_data}"
                
                # Send the message
                context.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
            
            # Set up the match
            match_type = "friendly"
            match_id_str = f"match_{int(time.time())}"
            
            cricket_match = CricketMatch(
                team1=challenger_team_obj,
                team2=opponent_team_obj,
                total_overs=5,  # Short T5 format for quick matches
                chat_id=update.effective_chat.id,
                send_message_func=telegram_message_wrapper,
                update_scorecard_func=dummy_scorecard_func,  # Use dummy function instead of None
                match_end_func=dummy_match_end_func,  # Use dummy function instead of None
                match_type=match_type,

                match_id=match_id_str
            )
            
            # Store the match
            active_matches[match_id] = cricket_match
            
            # Create match context
            match_context = {
                'match_id': match_id,
                'challenger_id': challenger_id,
                'opponent_id': opponent_id,
                'challenger_name': challenger_name,
                'opponent_name': opponent_name,
                'match_cost': match_cost,
                'chat_id': update.effective_chat.id,
                'cricket_match': cricket_match
            }
            
            # Update setup message
            loading_msg.edit_text(
                f"⚾ MATCH STARTING ⚾\n\n"
                f"{challenger_name} vs {opponent_name}\n"
                f"{challenger_team_name} vs {opponent_team_name}\n\n"
                f"Format: T5 (5 overs per side)\n"
                f"Stake: {match_cost * 2} coins\n\n"
                f"The toss is about to happen! Match commentary coming soon..."
            )
            
            # Start match simulation in a non-blocking way
            simulate_match(context.bot, match_context)
            
            return MATCH_IN_PROGRESS
            
        except Exception as e:
            logger.error(f"Error starting match: {e}")
            loading_msg.edit_text(f"Error starting match: {str(e)}")
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
        # Opponent team selection complete - the match starts after this
        
        return MATCH_SETUP
    
    # Handle final confirmation
    if query.data.startswith("confirm_"):
        # Extract match cost from callback data
        match_cost = int(query.data.split("_")[-1])
        context.user_data['match_cost'] = match_cost
        
        # Save match cost in chat_data
        match_key = context.user_data.get('current_match_key')
        if match_key and match_key in context.chat_data:
            context.chat_data[match_key]['match_cost'] = match_cost
            logger.debug(f"Saved match_cost {match_cost} to chat_data[{match_key}]")
        
        # Deduct coins from challenger
        update_user_coins(challenger_id, -match_cost)
        
        # Get opponent name from the match data again to ensure consistency
        if match_key and match_key in context.chat_data:
            opponent_name = context.chat_data[match_key].get('opponent_name', 'Your opponent')
        else:
            opponent_name = context.user_data.get('opponent_name', 'Your opponent')
            
        # Get team names from chat_data if available
        if match_key and match_key in context.chat_data:
            challenger_team_name = context.chat_data[match_key].get('challenger_team_name') or context.user_data.get('challenger_team_name', 'Team 1')
            opponent_team_name = context.chat_data[match_key].get('opponent_team_name') or context.user_data.get('opponent_team_name', 'Team 2')
        else:
            challenger_team_name = context.user_data.get('challenger_team_name', 'Team 1')
            opponent_team_name = context.user_data.get('opponent_team_name', 'Team 2')
        
        # Store match key in opponent's callback data via inline keyboard
        # This ensures the opponent will have access to the match data when they accept/decline
        callback_data_accept = f"accept_challenge:{match_key}"
        callback_data_decline = f"decline_challenge:{match_key}"
        
        # Update keyboard with match key information
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept Challenge", callback_data=callback_data_accept),
                InlineKeyboardButton("❌ Decline", callback_data=callback_data_decline)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message with new keyboard containing match key
        query.edit_message_text(
            f"⚡ MATCH CHALLENGE ⚡\n\n"
            f"{query.from_user.first_name} has challenged {opponent_name} "
            f"to a cricket match!\n\n"
            f"{query.from_user.first_name}'s team: {challenger_team_name}\n"
            f"{opponent_name}'s team: {opponent_team_name}\n\n"
            f"Match cost: {match_cost} coins each\n"
            f"Winner gets: {match_cost * 2} coins\n\n"
            f"{opponent_name}, do you accept this challenge?",
            reply_markup=reply_markup
        )
        
        # Tag the opponent in a new message for notification
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"@{update.callback_query.from_user.username} has challenged you to a cricket match! Check the message above ☝️",
            reply_to_message_id=context.user_data['setup_message_id']
        )
        
        return MATCH_CONFIRMATION
    
    return MATCH_SETUP

def match_confirmation_handler(update: Update, context: CallbackContext) -> int:
    """Handle match acceptance or declining"""
    query = update.callback_query
    query.answer()
    
    # First check if we have a match key in the callback data
    # The format should be "accept_challenge:match_123_456" or "decline_challenge:match_123_456"
    match_key = None
    match_data = None
    
    # Debug the entire callback data
    logger.debug(f"Callback data: {query.data}")
    
    # Extract match_key from callback data with more lenient parsing
    if ":" in query.data:
        action, key = query.data.split(":", 1)
        logger.debug(f"Split callback data - action: {action}, key: {key}")
        # Accept both formats: with and without "match_" prefix
        if key.startswith("match_") or action.startswith("accept_challenge") or action.startswith("decline_challenge"):
            match_key = key
            logger.debug(f"Found match key in callback data: {match_key}")
            
            # Get match data from chat_data using this key
            if match_key in context.chat_data:
                match_data = context.chat_data[match_key]
                logger.debug(f"Found match data using key from callback: {match_data}")
                
                # Store key in user_data for future reference
                context.user_data['current_match_key'] = match_key
    
    # If we didn't find a match key in callback data, try to find it in chat_data
    if not match_key or not match_data:
        # Debug what we have in chat_data
        logger.debug(f"Looking for match data in chat_data for user {query.from_user.id}")
        for key in context.chat_data:
            if key.startswith("match_"):
                logger.debug(f"Found match key: {key} with data: {context.chat_data[key]}")
                # This is a match key, get the match data
                potential_match_data = context.chat_data[key]
                # Check if this is the opponent for the current match
                if potential_match_data.get('opponent_id') == query.from_user.id:
                    match_data = potential_match_data
                    match_key = key
                    logger.debug(f"Match found for user {query.from_user.id} with match key {match_key}")
                    
                    # Store key in user_data for future reference
                    context.user_data['current_match_key'] = match_key
                    break
    
    if not match_data:
        logger.warning(f"No match data found in chat_data for user {query.from_user.id}")
        # Fallback to user_data for backward compatibility
        challenger_id = context.user_data.get('challenger_id')
        opponent_id = context.user_data.get('opponent_id')
        
        # If we still don't have the IDs, we can't proceed
        if not challenger_id or not opponent_id:
            logger.error(f"Could not find challenger_id or opponent_id for user {query.from_user.id}")
            query.edit_message_text("Error: Match data not found. Please start a new challenge.")
            return ConversationHandler.END
        
        logger.debug(f"Using fallback data: challenger_id={challenger_id}, opponent_id={opponent_id}")
    else:
        # Use match data from chat_data
        challenger_id = match_data.get('challenger_id')
        opponent_id = match_data.get('opponent_id')
        logger.debug(f"Using match data from chat_data: challenger_id={challenger_id}, opponent_id={opponent_id}")
    
    # Log the challenger and opponent IDs for debugging
    logger.debug(f"Challenge: challenger_id={challenger_id}, opponent_id={opponent_id}, user_id={query.from_user.id}")
    
    # Ensure the right person is responding
    if query.from_user.id != opponent_id:
        query.answer("This is not your challenge to accept or decline.", show_alert=True)
        return MATCH_CONFIRMATION
    
    # Handle decline
    if query.data.startswith("decline_challenge"):
        # Refund challenger's coins
        match_cost = context.user_data.get('match_cost', 100)
        
        # Get match cost from chat_data if available
        if match_key and match_key in context.chat_data:
            match_cost = context.chat_data[match_key].get('match_cost', match_cost)
        
        update_user_coins(challenger_id, match_cost)
        
        query.edit_message_text(
            f"Match challenge declined by {query.from_user.first_name}.\n"
            f"{match_cost} coins have been refunded to the challenger."
        )
        return ConversationHandler.END
    
    # Handle accept
    if query.data.startswith("accept_challenge"):
        # Get match cost from chat_data if available, otherwise from user_data
        match_cost = context.user_data.get('match_cost', 100)
        
        # Make sure we have a valid match_key (double-check by parsing from the callback data)
        if ":" in query.data:
            _, parsed_match_key = query.data.split(":", 1)
            if parsed_match_key and parsed_match_key in context.chat_data:
                match_key = parsed_match_key
                context.user_data['current_match_key'] = match_key
                logger.debug(f"Parsed match_key from callback data: {match_key}")
        
        # Get match cost from chat_data if available
        if match_key and match_key in context.chat_data:
            match_cost = context.chat_data[match_key].get('match_cost', match_cost)
            
        logger.debug(f"Match cost for acceptance: {match_cost}")
        opponent_coins = get_user_coins(opponent_id)
        
        # Check if opponent has enough coins
        if opponent_coins < match_cost:
            query.edit_message_text(
                f"{query.from_user.first_name} doesn't have enough coins for this match "
                f"(required: {match_cost}, available: {opponent_coins}).\n"
                f"{match_cost} coins have been refunded to the challenger."
            )
            # Refund challenger's coins
            update_user_coins(challenger_id, match_cost)
            return ConversationHandler.END
        
        # Get opponent's teams
        opponent_teams = get_user_teams(opponent_id)
        logger.debug(f"Teams for opponent {opponent_id}: {opponent_teams}")
        
        if not opponent_teams:
            query.edit_message_text(
                f"You don't have any teams to play with. Use /create_team to create a team first.\n"
                f"{match_cost} coins have been refunded to the challenger."
            )
            # Refund challenger's coins
            update_user_coins(challenger_id, match_cost)
            return ConversationHandler.END
        
        # Automatically select the first team for the opponent
        opponent_team = opponent_teams[0]
        opponent_team_id = opponent_team['id']
        opponent_team_name = opponent_team['name']
        
        # Get detailed opponent team data
        opponent_team_details = get_team(opponent_team_id, opponent_id)
        if not opponent_team_details:
            query.edit_message_text("Error: Your team couldn't be found. Please try again.")
            # Refund challenger's coins
            update_user_coins(challenger_id, match_cost)
            return ConversationHandler.END
        
        # Calculate opponent team rating for display purposes
        opponent_players = opponent_team_details.get('players', [])
        opponent_player_count = len(opponent_players)
        opponent_team_rating = 0
        
        if opponent_player_count > 0:
            player_ovrs = [p.get('total_ovr', 0) for p in opponent_players]
            opponent_team_rating = sum(player_ovrs) // opponent_player_count if player_ovrs else 0
        
        # Deduct coins from opponent
        update_user_coins(opponent_id, -match_cost)
        
        # Store opponent team info in match data
        if match_key and match_key in context.chat_data:
            context.chat_data[match_key]['opponent_team_id'] = opponent_team_id
            context.chat_data[match_key]['opponent_team_name'] = opponent_team_name
        
        # Store in user_data as well
        context.user_data['opponent_team_id'] = opponent_team_id
        context.user_data['opponent_team_name'] = opponent_team_name
        
        # Get challenger team name and challenger name
        if match_key and match_key in context.chat_data:
            challenger_name = context.chat_data[match_key].get('challenger_name', 'Challenger')
            challenger_team_name = context.chat_data[match_key].get('challenger_team_name', 'Team 1')
            challenger_team_id = context.chat_data[match_key].get('challenger_team_id')
        else:
            challenger_name = context.user_data.get('challenger_name', 'Challenger')
            challenger_team_name = context.user_data.get('challenger_team_name', 'Team 1')
            challenger_team_id = context.user_data.get('challenger_team_id')
        
        # Update message to show match is starting
        loading_msg = query.edit_message_text(
            f"⚡ MATCH CHALLENGE ACCEPTED ⚡\n\n"
            f"{challenger_name}: {challenger_team_name} (OVR: ?)\n"
            f"{query.from_user.first_name}: {opponent_team_name} (OVR: {opponent_team_rating})\n\n"
            f"Match is starting... ⏳"
        )
        
        # Get team details with better error handling
        challenger_team = None
        opponent_team = None
        
        try:
            challenger_team = get_team(challenger_team_id, challenger_id)
            logger.debug(f"Challenger team details: {challenger_team}")
        except Exception as e:
            logger.error(f"Error getting challenger team: {e}")
            
        try:
            opponent_team = get_team(opponent_team_id, opponent_id)
            logger.debug(f"Opponent team details: {opponent_team}")
        except Exception as e:
            logger.error(f"Error getting opponent team: {e}")
        
        if not challenger_team:
            error_msg = f"Error: Could not load challenger's team (ID: {challenger_team_id})."
            logger.error(error_msg)
            loading_msg.edit_text(error_msg)
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
            
        if not opponent_team:
            error_msg = f"Error: Could not load opponent's team (ID: {opponent_team_id})."
            logger.error(error_msg)
            loading_msg.edit_text(error_msg)
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            return ConversationHandler.END
        
        # Convert DB team format to match engine Team objects
        challenger_team_obj = create_team_obj(
            challenger_team, 
            challenger_team_name, 
            challenger_id
        )
        
        opponent_team_obj = create_team_obj(
            opponent_team, 
            opponent_team_name, 
            opponent_id
        )
        
        # Start the match
        match_id = f"{challenger_id}_{opponent_id}_{int(time.time())}"
        context.user_data['match_id'] = match_id
        
        # Create match object
        try:
            # Define dummy functions to handle the None type errors
            def dummy_scorecard_func(data):
                # This function is never called, we handle scorecards in simulate_match
                pass
            
            def dummy_match_end_func(data):
                # This function is never called, we handle match end in simulate_match
                pass
            
            # Create a wrapper function for sending messages
            def telegram_message_wrapper(message_data):
                """Adapts the dictionary-based message data to Telegram's bot.send_message format"""
                # Get chat_id from match or use the update's chat_id
                chat_id = update.effective_chat.id
                
                # Extract message text
                if "commentary" in message_data:
                    text = message_data["commentary"]
                elif "message" in message_data:
                    text = message_data["message"]
                elif "event" in message_data:
                    # Build appropriate message based on event type
                    event = message_data.get("event")
                    if event == "match_start":
                        text = f"🏏 MATCH START 🏏\n\n{message_data.get('commentary', '')}"
                    elif event == "innings_break":
                        team = message_data.get("team", "")
                        score = message_data.get("score", 0)
                        wickets = message_data.get("wickets", 0)
                        overs = message_data.get("overs", 0)
                        balls = message_data.get("balls", 0)
                        text = f"🏏 INNINGS COMPLETE 🏏\n\n{team}: {score}/{wickets} ({overs}.{balls} overs)"
                    else:
                        # Default fallback for unknown events
                        text = f"Match update: {message_data}"
                else:
                    # Default fallback
                    text = f"Match update: {message_data}"
                
                # Send the message
                context.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
            
            # Set up the match
            cricket_match = CricketMatch(
                team1=challenger_team_obj,
                team2=opponent_team_obj,
                total_overs=5,  # Short T5 format
                chat_id=update.effective_chat.id,
                send_message_func=telegram_message_wrapper,
                update_scorecard_func=lambda data: context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=f"🏏 SCORECARD: {data.get('batting_team', '')}: {data.get('score', 0)}/{data.get('wickets', 0)} ({data.get('overs', '')})"
                ),
                match_end_func=lambda data: context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=f"🏏 MATCH RESULT: {data.get('winner', 'Unknown')} won!" 
                ),
            )
            
            # Store the match
            active_matches[match_id] = cricket_match
            
            # Create match context
            match_context = {
                'match_id': match_id,
                'challenger_id': challenger_id,
                'opponent_id': opponent_id,
                'challenger_name': challenger_name,
                'opponent_name': query.from_user.first_name,
                'match_cost': match_cost,
                'start_time': int(time.time())
            }
            
            # Save match context in chat_data
            context.chat_data[f"match_context_{match_id}"] = match_context
            
            # Start the simulation directly rather than in a thread
            # This is a simplified approach
            # Get the match
            cricket_match = active_matches.get(match_id)
            if cricket_match:
                # Simulate the match
                try:
                    # Create a new match context for simulation
                    sim_context = {
                        'match_id': match_id,
                        'cricket_match': cricket_match,
                        'chat_id': update.effective_chat.id,
                        'challenger_id': challenger_id,
                        'opponent_id': opponent_id,
                        'challenger_name': challenger_name,
                        'opponent_name': query.from_user.first_name,
                        'match_cost': match_cost
                    }
                    # Run the simulation
                    simulate_match(context.bot, sim_context)
                except Exception as e:
                    logger.error(f"Error simulating match: {e}")
                    logger.exception("Match simulation error details:")
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"❌ Error during match simulation: {str(e)}"
                    )
            
            return MATCH_IN_PROGRESS
            
        except Exception as e:
            logger.error(f"Error setting up match: {e}")
            logger.exception("Match setup error details:")
            
            # Update message with error
            query.edit_message_text(
                f"❌ Error setting up the match: {str(e)}\n"
                f"The match cost has been refunded to both players."
            )
            
            # Refund both players
            update_user_coins(challenger_id, match_cost)
            update_user_coins(opponent_id, match_cost)
            
            return ConversationHandler.END
        
        return MATCH_CONFIRMATION
    
    return MATCH_CONFIRMATION

def create_team_obj(team_data: Dict, team_name: str, user_id: int) -> Team:
    """Create a Team object from database team data"""
    players = []
    
    # Extract player details from team_data
    team_players = team_data.get('players', [])
    
    for p in team_players:
        # Ensure OVR values are integers
        batting_ovr = p.get('batting_ovr', 0)
        bowling_ovr = p.get('bowling_ovr', 0)
        total_ovr = p.get('total_ovr', 0)
        
        # Convert string OVRs to integers if needed
        if isinstance(batting_ovr, str):
            try:
                batting_ovr = int(batting_ovr)
            except (ValueError, TypeError):
                batting_ovr = 0
                
        if isinstance(bowling_ovr, str):
            try:
                bowling_ovr = int(bowling_ovr)
            except (ValueError, TypeError):
                bowling_ovr = 0
                
        if isinstance(total_ovr, str):
            try:
                total_ovr = int(total_ovr)
            except (ValueError, TypeError):
                total_ovr = 0
        
        # Log player data for debugging
        logger.debug(f"Creating Player object for {p.get('name')}: batting_ovr={batting_ovr}, bowling_ovr={bowling_ovr}, total_ovr={total_ovr}")
        
        # Create Player object
        player = Player(
            id=p['id'],
            name=p['name'],
            role=p['role'],
            team=p['team'],
            batting_type=p['batting_type'],
            bowling_type=p['bowling_type'],
            batting_ovr=batting_ovr,
            bowling_ovr=bowling_ovr,
            total_ovr=total_ovr,
            position=p.get('position', 0),
            tier=p.get('tier', 'Bronze'),
            # Set attributes based on OVR ratings
            batting_timing=min(99, batting_ovr + random.randint(-5, 5)),
            batting_technique=min(99, batting_ovr + random.randint(-5, 5)),
            batting_power=min(99, batting_ovr + random.randint(-5, 5)),
            bowling_pace=min(99, bowling_ovr + random.randint(-5, 5)),
            bowling_variation=min(99, bowling_ovr + random.randint(-5, 5)),
            bowling_accuracy=min(99, bowling_ovr + random.randint(-5, 5))
        )
        players.append(player)
    
    # Create and return Team object
    return Team(
        id=team_data['id'],
        name=team_name,
        owner_id=user_id,
        players=players
    )

def simulate_match(bot, match_context: Dict, delay: float = 3.0):
    """Simulate the match in a non-blocking way with configurable delay
    
    Args:
        bot: The Telegram bot instance
        match_context: Dictionary containing match data
        delay: Delay in seconds between ball commentaries (default: 3.0)
    """
    # Initialize variables that might be accessed in the except block
    match_id = None
    chat_id = None
    
    try:
        match_id = match_context['match_id']
        cricket_match = match_context['cricket_match']
        chat_id = match_context['chat_id']
        
        # Match ID variable to reference the match later
        match_key = None
        
        # Create a bot wrapper function for this simulation
        def simulation_message_wrapper(message_data):
            """Adapts the dictionary-based message data to Telegram's bot.send_message format"""
            # Extract message text
            if "commentary" in message_data:
                text = message_data["commentary"]
            elif "message" in message_data:
                text = message_data["message"]
            elif "event" in message_data:
                # Build appropriate message based on event type
                event = message_data.get("event")
                if event == "match_start":
                    text = f"🏏 MATCH START 🏏\n\n{message_data.get('commentary', '')}"
                elif event == "innings_break":
                    team = message_data.get("team", "")
                    score = message_data.get("score", 0)
                    wickets = message_data.get("wickets", 0)
                    overs = message_data.get("overs", 0)
                    balls = message_data.get("balls", 0)
                    text = f"🏏 INNINGS COMPLETE 🏏\n\n{team}: {score}/{wickets} ({overs}.{balls} overs)"
                else:
                    # Default fallback for unknown events
                    text = f"Match update: {message_data}"
            else:
                # Default fallback
                text = f"Match update: {message_data}"
            
            # Send the message with RetryAfter handling
            send_message_safely(
                bot=bot,
                chat_id=chat_id,
                text=text
            )
        
        # Update the cricket match with our new wrapper
        cricket_match.send_message_func = simulation_message_wrapper
        
        # Create a scorecard update wrapper function
        def update_scorecard_wrapper(scorecard_data):
            """Adapts the scorecard dictionary to a formatted message for Telegram"""
            # Check if detailed scorecard is requested
            detailed = scorecard_data.get("detailed", False)
            
            # Extract basic match information
            batting_team = scorecard_data.get("batting_team", "Unknown")
            bowling_team = scorecard_data.get("bowling_team", "Unknown")
            score = scorecard_data.get("score", 0)
            wickets = scorecard_data.get("wickets", 0)
            overs = scorecard_data.get("overs", "0.0")
            current_run_rate = scorecard_data.get("current_run_rate", 0)
            
            # Get target information if available
            target = scorecard_data.get("target")
            required_run_rate = scorecard_data.get("required_run_rate", 0)
            
            # Format the basic scorecard
            if detailed:
                # Start with scorecard header
                message = (
                    f"╔═══════════════════════════╗\n"
                    f"║       📊 DETAILED SCORECARD       ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"🏏 {batting_team}: {score}/{wickets} ({overs} overs)\n"
                    f"📈 CRR: {current_run_rate:.2f}"
                )
                
                if target:
                    # Calculate balls and runs remaining
                    overs_parts = overs.split('.')
                    current_overs = int(overs_parts[0])
                    current_balls = int(overs_parts[1]) if len(overs_parts) > 1 else 0
                    total_overs = cricket_match.total_overs
                    
                    balls_completed = current_overs * 6 + current_balls
                    balls_remaining = (total_overs * 6) - balls_completed
                    runs_needed = target - score
                    
                    message += f"\n🎯 Target: {target} ({runs_needed} needed from {balls_remaining} balls, RRR: {required_run_rate:.2f})"
                
                # Add batsmen details with improved formatting
                message += "\n\n┌─────── BATSMEN ───────┐"
                current_batsmen = [b.get("name") for b in scorecard_data.get("current_batsmen", [])]
                
                # Add all batsmen who have faced a ball
                for batsman in scorecard_data.get("batsmen", []):
                    name = batsman.get("name", "Unknown")
                    runs = batsman.get("runs", 0)
                    balls = batsman.get("balls", 0)
                    fours = batsman.get("fours", 0)
                    sixes = batsman.get("sixes", 0)
                    strike_rate = batsman.get("strike_rate", 0)
                    is_out = batsman.get("is_out", False)
                    
                    # Mark current batsmen with *
                    if name in current_batsmen:
                        name = f"{name}* 🏏"
                    
                    # Format the batsman's stats
                    if is_out:
                        out_method = batsman.get("out_method", "Unknown")
                        bowler = batsman.get("bowler_who_dismissed", "")
                        fielder = batsman.get("fielder_who_dismissed", "")
                        
                        if out_method == "Caught":
                            dismissal = f"c {fielder} b {bowler}"
                        elif out_method == "Bowled":
                            dismissal = f"b {bowler}"
                        elif out_method == "LBW":
                            dismissal = f"lbw b {bowler}"
                        elif out_method == "Run Out":
                            dismissal = f"run out ({fielder})"
                        else:
                            dismissal = out_method
                            
                        batting_line = f"{name}: {runs} ({balls}) - {dismissal}"
                    else:
                        batting_line = f"{name}: {runs} ({balls}) - {fours}×4, {sixes}×6, SR: {strike_rate:.1f}"
                    
                    message += f"\n│ {batting_line}"
                
                message += "\n└───────────────────────┘"
                
                # Add fall of wickets with better formatting
                if scorecard_data.get("fall_of_wickets"):
                    message += "\n\n┌─── FALL OF WICKETS ───┐"
                    wicket_list = []
                    
                    for wicket in scorecard_data.get("fall_of_wickets", []):
                        score = wicket.get("score", 0)
                        wicket_num = wicket.get("wicket", 0)
                        player = wicket.get("player_out", "Unknown")
                        overs = wicket.get("overs", "0.0")
                        
                        wicket_list.append(f"{wicket_num}-{score} ({player}, {overs})")
                    
                    message += f"\n│ {', '.join(wicket_list)}"
                    message += "\n└───────────────────────┘"
                
                # Add bowler information with improved formatting
                message += "\n\n┌─────── BOWLERS ───────┐"
                
                # Get current bowler name to ensure consistency
                current_bowler_name = scorecard_data.get("current_bowler", {}).get("name", "Unknown")
                
                for bowler in scorecard_data.get("bowlers", []):
                    name = bowler.get("name", "Unknown")
                    overs = bowler.get("overs", 0)
                    maidens = bowler.get("maidens", 0)
                    runs = bowler.get("runs", 0)
                    wickets = bowler.get("wickets", 0)
                    economy = bowler.get("economy", 0)
                    
                    # Mark current bowler with * - ensure it matches the over announcement
                    if name == current_bowler_name or bowler.get("is_bowling", False):
                        name = f"{name}* 🎯"
                    
                    message += f"\n│ {name}: {overs}-{maidens}-{runs}-{wickets} (Econ: {economy:.2f})"
                
                message += "\n└───────────────────────┘"
                
                # Add current partnership if available
                partnership = scorecard_data.get("current_partnership", {})
                if partnership and partnership.get("balls", 0) > 0:
                    p_runs = partnership.get("runs", 0)
                    p_balls = partnership.get("balls", 0)
                    p_rate = partnership.get("run_rate", 0)
                    
                    message += f"\n\n🤝 Current Partnership: {p_runs} runs, {p_balls} balls (RR: {p_rate:.2f})"
            else:
                # This is a normal (non-detailed) scorecard shown after every over
                message = (
                    f"╔═══════════════════════════╗\n"
                    f"║          📊 SCORECARD          ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"🏏 {batting_team}: {score}/{wickets} ({overs} overs)\n"
                    f"📈 CRR: {current_run_rate:.2f}"
                )
                
                if target:
                    # Calculate balls and runs remaining
                    overs_parts = overs.split('.')
                    current_overs = int(overs_parts[0])
                    current_balls = int(overs_parts[1]) if len(overs_parts) > 1 else 0
                    total_overs = cricket_match.total_overs
                    
                    balls_completed = current_overs * 6 + current_balls
                    balls_remaining = (total_overs * 6) - balls_completed
                    runs_needed = target - score
                    
                    message += f"\n🎯 Target: {target} ({runs_needed} needed from {balls_remaining} balls, RRR: {required_run_rate:.2f})"
                
                # Add current batsmen with better formatting
                message += "\n\n┌─────── STRIKERS ───────┐"
                
                for batsman in scorecard_data.get("current_batsmen", []):
                    name = batsman.get("name", "Unknown")
                    runs = batsman.get("runs", 0)
                    balls = batsman.get("balls", 0)
                    
                    message += f"\n│ {name}: {runs} ({balls})"
                
                message += "\n└───────────────────────┘"
                
                # Add current bowler - ensure it matches the over announcement
                bowler = scorecard_data.get("current_bowler", {})
                if bowler:
                    name = bowler.get("name", "Unknown")
                    overs = bowler.get("overs", 0)
                    wickets = bowler.get("wickets", 0)
                    runs = bowler.get("runs", 0)
                    
                    message += "\n\n┌─── CURRENT BOWLER ────┐"
                    message += f"\n│ {name}: {overs} overs, {wickets}/{runs}"
                    message += "\n└───────────────────────┘"
            
            # Send the formatted scorecard with RetryAfter handling
            send_message_safely(
                bot=bot,
                chat_id=chat_id,
                text=message
            )
        
        # Update the cricket match with our scorecard wrapper
        cricket_match.update_scorecard_func = update_scorecard_wrapper
        
        # Send toss update
        toss_winner = random.choice([0, 1])  # 0 for team1, 1 for team2
        toss_choice = random.choice(['bat', 'bowl'])
        
        # Get team names for toss message
        team1_name = cricket_match.team1.name
        team2_name = cricket_match.team2.name
        
        toss_message = (
            f"🏏 TOSS UPDATE 🏏\n\n"
            f"{team1_name if toss_winner == 0 else team2_name} won the toss and elected to {toss_choice} first."
        )
        
        send_message_safely(
            bot=bot,
            chat_id=chat_id,
            text=toss_message
        )
        
        # Determine batting and bowling teams based on toss
        if (toss_winner == 0 and toss_choice == 'bat') or (toss_winner == 1 and toss_choice == 'bowl'):
            # Team 1 bats first
            batting_first = cricket_match.team1
            bowling_first = cricket_match.team2
        else:
            # Team 2 bats first
            batting_first = cricket_match.team2
            bowling_first = cricket_match.team1
        
        # Start the full match simulation with reduced commentary frequency
        cricket_match.simulate_match(
            delay_between_balls=4.0  # 4 seconds between commentary messages to avoid Telegram RetryAfter errors
        )
        
        # Match finished, handle results by completing the match
        result = cricket_match.complete_match()
        result_type = result.get("result_type", "tie")
        
        # Get final scores
        team1_score = f"{cricket_match.team1_score}/{cricket_match.team1_wickets}"
        team2_score = f"{cricket_match.team2_score}/{cricket_match.team2_wickets}"
        
        # Prepare match result data
        match_result_data = {
            "team1_name": cricket_match.team1.name,
            "team2_name": cricket_match.team2.name,
            "team1_score": cricket_match.team1_score,
            "team1_wickets": cricket_match.team1_wickets,
            "team1_overs": cricket_match.team1_overs,
            "team2_score": cricket_match.team2_score,
            "team2_wickets": cricket_match.team2_wickets,
            "team2_overs": cricket_match.team2_overs,
            "result_type": result_type,
            "match_id": match_id
        }
        
        # Get match cost
        match_cost = match_context['match_cost']
        
        # Extract reward values from result
        team1_reward = result.get("team1_reward", random.randint(1000, 1500))
        team2_reward = result.get("team2_reward", random.randint(500, 600))
        
        # Handle tie case
        if result_type == "tie":
            # It's a tie, give equal rewards to both players
            challenger_reward = team1_reward
            opponent_reward = team2_reward
            
            # Refund match cost plus tie reward
            update_user_coins(match_context['challenger_id'], match_cost + challenger_reward)
            update_user_coins(match_context['opponent_id'], match_cost + opponent_reward)
            
            # Create a more detailed tie message with improved UI
            tie_message = (
                f"╔═══════════════════════════╗\n"
                f"║     🏏 MATCH RESULT: TIE! 🏏     ║\n"
                f"╚═══════════════════════════╝\n\n"
                f"┌─────── FINAL SCORES ─────┐\n"
                f"│ {match_context['challenger_name']} (Team 1): {team1_score}\n"
                f"│ {match_context['opponent_name']} (Team 2): {team2_score}\n"
                f"└───────────────────────────┘\n\n"
                f"What an incredible match! It ends in a dramatic tie! 🤝\n\n"
                f"💰 REWARDS:\n"
                f"• {match_context['challenger_name']}: {challenger_reward} coins + {match_cost} refund\n"
                f"• {match_context['opponent_name']}: {opponent_reward} coins + {match_cost} refund"
            )
            
            send_message_safely(
                bot=bot,
                chat_id=chat_id,
                text=tie_message
            )
            
            # Collect player statistics in case of a tie
            # First, get database user IDs
            from db import get_or_create_user, update_player_stats_after_match
            challenger_db_user = get_or_create_user(match_context['challenger_id'])
            opponent_db_user = get_or_create_user(match_context['opponent_id'])
            
            # Collect team1 player performance data
            team1_performance = []
            for player in cricket_match.team1.players:
                is_batsman = True
                is_bowler = player.role.lower() in ['bowler', 'all-rounder'] or player.balls_bowled > 0
                
                team1_performance.append({
                    'player_id': player.id,
                    'is_batsman': is_batsman,
                    'is_bowler': is_bowler,
                    'runs': player.runs,
                    'balls_faced': player.balls_faced,
                    'is_out': player.is_out,
                    'fours': player.fours,
                    'sixes': player.sixes,
                    'wickets': player.wickets,
                    'overs_bowled': player.overs_bowled,
                    'balls_bowled': player.balls_bowled,
                    'runs_conceded': player.runs_conceded,
                    'maidens': player.maidens
                })
            
            # Collect team2 player performance data
            team2_performance = []
            for player in cricket_match.team2.players:
                is_batsman = True
                is_bowler = player.role.lower() in ['bowler', 'all-rounder'] or player.balls_bowled > 0
                
                team2_performance.append({
                    'player_id': player.id,
                    'is_batsman': is_batsman,
                    'is_bowler': is_bowler,
                    'runs': player.runs,
                    'balls_faced': player.balls_faced,
                    'is_out': player.is_out,
                    'fours': player.fours,
                    'sixes': player.sixes,
                    'wickets': player.wickets,
                    'overs_bowled': player.overs_bowled,
                    'balls_bowled': player.balls_bowled,
                    'runs_conceded': player.runs_conceded,
                    'maidens': player.maidens
                })
            
            # Update player stats for both teams (tie counts as half win)
            update_player_stats_after_match(challenger_db_user['id'], team1_performance, is_winner=False)
            update_player_stats_after_match(opponent_db_user['id'], team2_performance, is_winner=False)
            
            # Clean up
            if match_id in active_matches:
                del active_matches[match_id]
            
            return
        
        # Determine winner based on result type
        if result_type == "team1_win":
            winner_id = match_context['challenger_id']
            loser_id = match_context['opponent_id']
            winner_name = match_context['challenger_name']
            winner_team = cricket_match.team1.name
            winner_reward = team1_reward
            loser_reward = team2_reward
        else:  # team2_win
            winner_id = match_context['opponent_id']
            loser_id = match_context['challenger_id']
            winner_name = match_context['opponent_name']
            winner_team = cricket_match.team2.name
            winner_reward = team2_reward
            loser_reward = team1_reward
        
        # Award coins based on match result
        update_user_coins(winner_id, match_cost + winner_reward)
        update_user_coins(loser_id, loser_reward)
        
        # Collect player statistics for the winner and loser
        # First, get database user IDs
        from db import get_or_create_user, update_player_stats_after_match
        winner_db_user = get_or_create_user(winner_id)
        loser_db_user = get_or_create_user(loser_id)
        
        # Collect team1 player performance data
        team1_performance = []
        for player in cricket_match.team1.players:
            is_batsman = True  # Everyone bats in cricket
            is_bowler = player.role.lower() in ['bowler', 'all-rounder'] or player.balls_bowled > 0
            
            team1_performance.append({
                'player_id': player.id,
                'is_batsman': is_batsman,
                'is_bowler': is_bowler,
                'runs': player.runs,
                'balls_faced': player.balls_faced,
                'is_out': player.is_out,
                'fours': player.fours,
                'sixes': player.sixes,
                'wickets': player.wickets,
                'overs_bowled': player.overs_bowled,
                'balls_bowled': player.balls_bowled,
                'runs_conceded': player.runs_conceded,
                'maidens': player.maidens
            })
        
        # Collect team2 player performance data
        team2_performance = []
        for player in cricket_match.team2.players:
            is_batsman = True  # Everyone bats in cricket
            is_bowler = player.role.lower() in ['bowler', 'all-rounder'] or player.balls_bowled > 0
            
            team2_performance.append({
                'player_id': player.id,
                'is_batsman': is_batsman,
                'is_bowler': is_bowler,
                'runs': player.runs,
                'balls_faced': player.balls_faced,
                'is_out': player.is_out,
                'fours': player.fours,
                'sixes': player.sixes,
                'wickets': player.wickets,
                'overs_bowled': player.overs_bowled,
                'balls_bowled': player.balls_bowled,
                'runs_conceded': player.runs_conceded,
                'maidens': player.maidens
            })
        
        # Update player stats based on which team won
        if result_type == "team1_win":
            update_player_stats_after_match(winner_db_user['id'], team1_performance, is_winner=True)
            update_player_stats_after_match(loser_db_user['id'], team2_performance, is_winner=False)
        else:  # team2_win
            update_player_stats_after_match(winner_db_user['id'], team2_performance, is_winner=True)
            update_player_stats_after_match(loser_db_user['id'], team1_performance, is_winner=False)
        
        # Create a more detailed win message with improved UI
        win_message = (
            f"╔═══════════════════════════╗\n"
            f"║   🏏 MATCH RESULT: VICTORY! 🏏   ║\n"
            f"╚═══════════════════════════╝\n\n"
            f"┌─────── FINAL SCORES ─────┐\n"
            f"│ {match_context['challenger_name']} (Team 1): {team1_score}\n"
            f"│ {match_context['opponent_name']} (Team 2): {team2_score}\n"
            f"└───────────────────────────┘\n\n"
            f"🎉 {winner_name} ({winner_team}) wins the match! 🎉\n\n"
            f"💰 REWARDS:\n"
            f"• {winner_name}: {winner_reward} coins + {match_cost} refund\n"
            f"• {match_context['challenger_name'] if winner_id == match_context['opponent_id'] else match_context['opponent_name']}: {loser_reward} coins"
        )
        
        # Send result message with RetryAfter handling
        send_message_safely(
            bot=bot,
            chat_id=chat_id,
            text=win_message
        )
        
        # Clean up
        if match_id in active_matches:
            del active_matches[match_id]
            
    except Exception as e:
        logger.error(f"Error in match simulation: {e}")
        
        # Get chat_id from context if not already defined
        error_chat_id = match_context.get('chat_id')
        if error_chat_id:
            send_message_safely(
                bot=bot,
                chat_id=error_chat_id,
                text=f"Error in match simulation: {str(e)}\n"
                     f"The match has been cancelled and all coins refunded."
            )
        
        # Refund both players
        update_user_coins(match_context['challenger_id'], match_context['match_cost'])
        update_user_coins(match_context['opponent_id'], match_context['match_cost'])
        
        # Clean up
        error_match_id = match_context.get('match_id')
        if error_match_id and error_match_id in active_matches:
            del active_matches[error_match_id]

def cancel_match(update: Update, context: CallbackContext) -> None:
    """Admin command to cancel an active match"""
    user = update.effective_user
    
    # Check if user is admin
    from db import is_admin
    if not is_admin(user.id):
        update.message.reply_text("Only admins can cancel matches.")
        return
    
    # List active matches
    if not active_matches:
        update.message.reply_text("There are no active matches to cancel.")
        return
    
    # Cancel all matches
    for match_id, match in active_matches.items():
        # Extract user IDs from match_id
        try:
            user1_id, user2_id, _ = match_id.split('_')
            user1_id, user2_id = int(user1_id), int(user2_id)
            
            # Refund both players (assuming match cost is 100)
            update_user_coins(user1_id, 100)
            update_user_coins(user2_id, 100)
            
        except Exception as e:
            logger.error(f"Error cancelling match {match_id}: {e}")
    
    # Clear active matches
    active_matches.clear()
    
    update.message.reply_text("All active matches have been cancelled and coins refunded.")