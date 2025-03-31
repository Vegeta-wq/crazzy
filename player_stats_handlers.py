#!/usr/bin/env python3
"""
Player statistics command handlers
"""
from typing import Dict, List, Optional, Tuple, Any
import logging
import random
import time
import json
import asyncio
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from db import get_or_create_user, get_player_stats, get_user_player_stats, get_leaderboard, get_player

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_tier_emoji(tier: str) -> str:
    """Get emoji representation for a tier"""
    tier_emojis = {
        'Bronze': '🥉',
        'Silver': '🥈',
        'Gold': '🥇',
        'Platinum': '💎',
        'Diamond': '💠',
        'Legendary': '🌟'
    }
    return tier_emojis.get(tier, '❓')

def format_player_statistics(stats: Dict) -> str:
    """
    Format player statistics for display in Telegram

    Args:
        stats: Dictionary containing player statistics

    Returns:
        Formatted text for Telegram message
    """
    if not stats:
        return "No statistics available for this player."

    player_info = get_player(stats['player_id'])
    tier_emoji = get_tier_emoji(player_info.get('tier', 'Bronze'))

    # Format batting statistics section
    batting_stats = (
        f"🏏 *BATTING STATISTICS*\n"
        f"Matches: {stats['matches_batted']}\n"
        f"Innings: {stats['innings_batted']}\n"
        f"Runs: {stats['total_runs']}\n"
        f"Average: {stats['batting_average']:.2f}\n"
        f"Strike Rate: {stats['batting_strike_rate']:.2f}\n"
        f"50s: {stats['fifties']}\n"
        f"100s: {stats['hundreds']}\n"
        f"Boundaries: {stats['total_fours']} fours, {stats['total_sixes']} sixes\n"
    )

    # Format bowling statistics section
    bowling_stats = (
        f"🎯 *BOWLING STATISTICS*\n"
        f"Matches: {stats['matches_bowled']}\n"
        f"Innings: {stats['innings_bowled']}\n"
        f"Wickets: {stats['wickets_taken']}\n"
        f"Economy: {stats['bowling_economy']:.2f}\n"
        f"Average: {stats['bowling_average']:.2f} runs per wicket\n"
        f"3-wicket hauls: {stats['three_wicket_hauls']}\n"
        f"5-wicket hauls: {stats['five_wicket_hauls']}\n"
    )

    return f"{tier_emoji} *{player_info.get('name', 'Unknown Player')}* ({player_info.get('role', 'Unknown Role')})\n\n{batting_stats}\n{bowling_stats}"

def player_stats_command(update: Update, context: CallbackContext) -> None:
    """Display statistics for a specific player"""
    message = update.message
    user = update.effective_user

    # Get user ID from database
    user_data = get_or_create_user(user.id)
    user_id = user_data['id']

    # Check if a player ID was provided
    if not context.args:
        message.reply_text(
            "Please provide a player ID. Usage: /playerstats [player_id]"
        )
        return

    try:
        player_id = int(context.args[0])

        # Get player statistics
        stats = get_player_stats(user_id, player_id)

        if not stats:
            message.reply_text(
                "No statistics found for this player. Try playing matches with them to collect data!"
            )
            return

        # Format and send the statistics
        formatted_stats = format_player_statistics(stats)
        message.reply_text(
            formatted_stats,
            parse_mode=ParseMode.MARKDOWN
        )

    except (ValueError, IndexError):
        message.reply_text(
            "Invalid player ID. Usage: /playerstats [player_id]"
        )
    except Exception as e:
        logger.error(f"Error retrieving player stats: {e}")
        message.reply_text(f"Error retrieving player statistics: {str(e)}")

def my_stats_command(update: Update, context: CallbackContext) -> None:
    """Display statistics for all players owned by the user"""
    message = update.message
    user = update.effective_user

    # Get user ID from database
    user_data = get_or_create_user(user.id)
    user_id = user_data['id']

    # Parse any arguments for filtering or sorting
    sort_by = 'batting_average'  # Default sort
    sort_order = 'desc'  # Default order
    role_filter = None
    page = 1
    page_size = 5

    if context.args:
        for arg in context.args:
            if arg.startswith('sort:'):
                sort_by = arg.split(':')[1]
            elif arg.startswith('order:'):
                sort_order = arg.split(':')[1]
            elif arg.startswith('role:'):
                role_filter = arg.split(':')[1]
            elif arg.startswith('page:'):
                try:
                    page = int(arg.split(':')[1])
                except ValueError:
                    page = 1

    # Calculate offset
    offset = (page - 1) * page_size

    # Get player statistics
    try:
        stats_list = get_user_player_stats(
            user_id=user_id,
            sort_by=sort_by,
            sort_order=sort_order,
            role_filter=role_filter,
            limit=page_size,
            offset=offset
        )

        if not stats_list:
            message.reply_text(
                "No player statistics found. Try playing some matches to collect data!"
            )
            return

        # Build the response message
        response = f"🏏 *YOUR PLAYER STATISTICS* 🏏\n\n"

        for idx, stats in enumerate(stats_list, 1):
            player_info = get_player(stats['player_id'])
            tier_emoji = get_tier_emoji(player_info.get('tier', 'Bronze'))

            response += (
                f"{idx}. {tier_emoji} *{player_info.get('name', 'Unknown')}* (ID: {stats['player_id']})\n"
                f"   Role: {player_info.get('role', 'Unknown')}\n"
                f"   Batting: {stats['runs_scored']} runs, Avg: {stats['batting_average']:.2f}, SR: {stats['batting_strike_rate']:.2f}\n"
                f"   Bowling: {stats['wickets_taken']} wickets, Econ: {stats['bowling_economy']:.2f}, Avg: {stats['bowling_average']:.2f}\n\n"
            )

        # Add pagination controls
        if page > 1 or len(stats_list) == page_size:
            response += "\n*Page Controls*\n"
            if page > 1:
                response += f"Use `/mystats page:{page-1}` for previous page\n"
            if len(stats_list) == page_size:
                response += f"Use `/mystats page:{page+1}` for next page\n"

        # Add usage instructions
        response += (
            "\n*Usage*:\n"
            "`/mystats [sort:field] [order:asc|desc] [role:type] [page:num]`\n"
            "Fields: batting_average, bowling_average, total_runs, total_wickets"
        )

        message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error retrieving player stats: {e}")
        message.reply_text(f"Error retrieving player statistics: {str(e)}")

def batting_leaderboard_command(update: Update, context: CallbackContext) -> None:
    """Display a leaderboard of the top batsmen"""
    message = update.message

    # Parse arguments for specific stat
    stat_field = 'batting_average'  # Default
    limit = 10

    if context.args:
        for arg in context.args:
            if arg.startswith('stat:'):
                stat_field = arg.split(':')[1]
            elif arg.startswith('limit:'):
                try:
                    limit = int(arg.split(':')[1])
                    limit = min(limit, 20)  # Cap at 20 to avoid too long messages
                except ValueError:
                    limit = 10

    try:
        # Get the leaderboard data
        leaderboard = get_leaderboard(
            stat_type='batting',
            stat_field=stat_field,
            limit=limit
        )

        if not leaderboard:
            message.reply_text(
                "No batting statistics found yet. Play some matches to collect data!"
            )
            return

        # Determine what stat we're showing
        stat_name = {
            'batting_average': 'Batting Average',
            'batting_strike_rate': 'Strike Rate',
            'total_runs': 'Runs',
            'total_fours': 'Fours',
            'total_sixes': 'Sixes',
            'fifties': '50s',
            'hundreds': '100s'
        }.get(stat_field, 'Batting Average')

        # Build the response message
        response = f"🏆 *BATTING LEADERBOARD - {stat_name}* 🏆\n\n"

        for idx, stats in enumerate(leaderboard, 1):
            player_info = get_player(stats['player_id'])
            tier_emoji = get_tier_emoji(player_info.get('tier', 'Bronze'))

            # Format the stat value
            if stat_field in ['batting_average', 'batting_strike_rate', 'bowling_average', 'economy_rate']:
                stat_value = f"{stats[stat_field]:.2f}"
            else:
                stat_value = str(stats[stat_field])

            response += (
                f"{idx}. {tier_emoji} *{player_info.get('name', 'Unknown')}* (ID: {stats['player_id']})\n"
                f"   {stat_name}: {stat_value}\n"
                f"   Matches: {stats['matches_batted']}, Runs: {stats['total_runs']}, Avg: {stats['batting_average']:.2f}\n\n"
            )

        # Add usage instructions
        response += (
            "\n*Usage*:\n"
            "`/battingleaderboard [stat:field] [limit:num]`\n"
            "Fields: batting_average, batting_strike_rate, total_runs, total_fours, total_sixes, fifties, hundreds"
        )

        message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error retrieving batting leaderboard: {e}")
        message.reply_text(f"Error retrieving batting leaderboard: {str(e)}")

def bowling_leaderboard_command(update: Update, context: CallbackContext) -> None:
    """Display a leaderboard of the top bowlers"""
    message = update.message

    # Parse arguments for specific stat
    stat_field = 'bowling_average'  # Default
    limit = 10

    if context.args:
        for arg in context.args:
            if arg.startswith('stat:'):
                stat_field = arg.split(':')[1]
            elif arg.startswith('limit:'):
                try:
                    limit = int(arg.split(':')[1])
                    limit = min(limit, 20)  # Cap at 20 to avoid too long messages
                except ValueError:
                    limit = 10

    try:
        # Get the leaderboard data
        leaderboard = get_leaderboard(
            stat_type='bowling',
            stat_field=stat_field,
            limit=limit
        )

        if not leaderboard:
            message.reply_text(
                "No bowling statistics found yet. Play some matches to collect data!"
            )
            return

        # Determine what stat we're showing
        stat_name = {
            'bowling_average': 'Bowling Average',
            'economy_rate': 'Economy Rate',
            'total_wickets': 'Wickets',
            'three_wicket_hauls': '3-Wicket Hauls',
            'five_wicket_hauls': '5-Wicket Hauls',
            'maidens': 'Maidens'
        }.get(stat_field, 'Bowling Average')

        # For bowling average, lower is better (sort ascending)
        sort_indicator = "↓" if stat_field in ['bowling_average', 'economy_rate'] else "↑"

        # Build the response message
        response = f"🏆 *BOWLING LEADERBOARD - {stat_name} {sort_indicator}* 🏆\n\n"

        for idx, stats in enumerate(leaderboard, 1):
            player_info = get_player(stats['player_id'])
            tier_emoji = get_tier_emoji(player_info.get('tier', 'Bronze'))

            # Format the stat value
            if stat_field in ['batting_average', 'batting_strike_rate', 'bowling_average', 'economy_rate']:
                stat_value = f"{stats[stat_field]:.2f}"
            else:
                stat_value = str(stats[stat_field])

            response += (
                f"{idx}. {tier_emoji} *{player_info.get('name', 'Unknown')}* (ID: {stats['player_id']})\n"
                f"   {stat_name}: {stat_value}\n"
                f"   Matches: {stats['innings_bowled']}, Wickets: {stats['wickets_taken']}, Econ: {stats['bowling_economy']:.2f}\n\n"
            )

        # Add usage instructions
        response += (
            "\n*Usage*:\n"
            "`/bowlingleaderboard [stat:field] [limit:num]`\n"
            "Fields: bowling_average, economy_rate, total_wickets, three_wicket_hauls, five_wicket_hauls, maidens"
        )

        message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error retrieving bowling leaderboard: {e}")
        message.reply_text(f"Error retrieving bowling leaderboard: {str(e)}")