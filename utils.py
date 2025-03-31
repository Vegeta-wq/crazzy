#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility functions for the Cricket Game Bot
"""

import logging

logger = logging.getLogger(__name__)


def get_tier_emoji(tier):
    """Get emoji for player tier"""
    tier_emojis = {
        "Bronze": "🥉",
        "Silver": "🥈",
        "Gold": "🥇",
        "Platinum": "💎",
        "Heroic": "🏆",
        "Icons": "👑"
    }
    return tier_emojis.get(tier, "")

def get_attribute_color(value):
    """Get color indicator based on attribute value"""
    if value >= 90:
        return "🟩" # Excellent
    elif value >= 75:
        return "🟨" # Good
    elif value >= 60:
        return "🟧" # Average
    else:
        return "🟥" # Poor

def format_player_info(player):
    """Format player information for display"""
    if not player:
        return "Player not found"
    
    # Create a visual representation of attribute ratings
    def rating_bar(value, max_length=10):
        if value is None:
            return "░" * max_length + " `N/A`"
        filled = int((value / 100) * max_length)
        return "▓" * filled + "░" * (max_length - filled)
    
    # Get tier emoji
    tier_emoji = get_tier_emoji(player['tier'])
    
    # Format player information with markdown formatting
    info = f"🏏 *PLAYER PROFILE: {player['name']}* 🏏\n\n"
    
    # Display tier with emoji prominently
    info += f"{tier_emoji} *{player['tier']} TIER* {tier_emoji}\n\n"
    
    # Basic information
    info += f"*Basic Information:*\n"
    info += f"📋 ID: `{player['id']}`\n"
    info += f"👥 Team: `{player['team']}`\n"
    info += f"🎯 Role: `{player['role']}`\n"
    
    # Add edition information if available
    if 'edition' in player and player['edition']:
        info += f"✨ Edition: `{player['edition']}`\n"
    
    # Optional basic info
    if 'age' in player and player['age']:
        info += f"🎂 Age: `{player['age']}`\n"
    if 'nationality' in player and player['nationality']:
        info += f"🌍 Country: `{player['nationality']}`\n"
        
    info += f"🏏 Batting: `{player['batting_type']}`\n"
    info += f"🔄 Bowling: `{player['bowling_type']}`\n\n"
    
    # Overall ratings section with color indicators
    info += "*OVERALL RATINGS:*\n"
    info += f"{get_attribute_color(player['batting_ovr'])} Batting: `{player['batting_ovr']}`\n"
    info += f"{get_attribute_color(player['bowling_ovr'])} Bowling: `{player['bowling_ovr']}`\n"
    
    # Display fielding OVR if available
    if 'fielding_ovr' in player and player['fielding_ovr']:
        info += f"{get_attribute_color(player['fielding_ovr'])} Fielding: `{player['fielding_ovr']}`\n"
        
    info += f"{get_attribute_color(player['total_ovr'])} TOTAL OVR: `{player['total_ovr']}`\n\n"
    
    # Batting attributes
    info += "*BATTING ATTRIBUTES:*\n"
    info += f"⏱️ Timing:    {rating_bar(player['batting_timing'])} `{player['batting_timing']}`\n"
    info += f"🎯 Technique: {rating_bar(player['batting_technique'])} `{player['batting_technique']}`\n"
    info += f"💪 Power:     {rating_bar(player['batting_power'])} `{player['batting_power']}`\n"
    
    # Optional batting attributes
    if 'batting_speed' in player and player['batting_speed']:
        info += f"🏃 Speed:     {rating_bar(player['batting_speed'])} `{player['batting_speed']}`\n"
    
    info += "\n"
    
    # Bowling attributes
    info += "*BOWLING ATTRIBUTES:*\n"
    info += f"⚡ Pace:      {rating_bar(player['bowling_pace'])} `{player['bowling_pace']}`\n"
    info += f"🎭 Variation: {rating_bar(player['bowling_variation'])} `{player['bowling_variation']}`\n"
    info += f"🎯 Accuracy:  {rating_bar(player['bowling_accuracy'])} `{player['bowling_accuracy']}`\n"
    
    # Optional bowling attributes
    if 'bowling_control' in player and player['bowling_control']:
        info += f"🎮 Control:   {rating_bar(player['bowling_control'])} `{player['bowling_control']}`\n"
    
    info += "\n"
    
    # Additional attributes
    additional_section = ""
    
    if 'fielding_ability' in player and player['fielding_ability']:
        additional_section += f"🧤 Fielding:  {rating_bar(player['fielding_ability'])} `{player['fielding_ability']}`\n"
    
    if 'fitness' in player and player['fitness']:
        additional_section += f"💪 Fitness:   {rating_bar(player['fitness'])} `{player['fitness']}`\n"
    
    if additional_section:
        info += "*ADDITIONAL ATTRIBUTES:*\n" + additional_section + "\n"
    
    # Add image URL if available
    if player['image_url']:
        if player['image_url'].startswith('telegram:'):
            info += "🖼️ [Player image attached via Telegram]"
        else:
            info += f"🖼️ Image: {player['image_url']}"
    
    return info


def validate_attribute(value, min_val=1, max_val=100):
    """Validate attribute values"""
    try:
        value = int(value)
        if min_val <= value <= max_val:
            return value, None
        else:
            return None, f"Value must be between {min_val} and {max_val}"
    except ValueError:
        return None, "Value must be a number"


def calculate_overall_ratings(batting_attrs, bowling_attrs):
    """Calculate overall ratings from individual attributes"""
    batting_ovr = sum(batting_attrs) // len(batting_attrs) if batting_attrs else 0
    bowling_ovr = sum(bowling_attrs) // len(bowling_attrs) if bowling_attrs else 0
    total_ovr = (batting_ovr + bowling_ovr) // 2
    
    return batting_ovr, bowling_ovr, total_ovr


def format_pack_info(pack):
    """Format pack information for display"""
    if not pack:
        return "Pack not found"
    
    # Create a visually appealing header with pack name
    info = f"📦 *PACK: {pack['name']}* 📦\n"
    info += f"{'━' * 20}\n\n"
    
    # Basic information section with description
    if pack.get('description'):
        info += f"📝 *Description:*\n{pack['description']}\n\n"
    
    # Price and contents with enhanced formatting
    info += "💼 *PACK DETAILS:*\n"
    info += f"💰 Price: {pack['price']} coins\n"
    info += f"🎮 Players: {pack['min_players']}"
    if pack['min_players'] != pack['max_players']:
        info += f"-{pack['max_players']}"
    info += " per pack\n"
    
    # Status with visual indicator
    if pack.get('is_active'):
        info += f"🟢 Status: *AVAILABLE NOW!*\n\n"
    else:
        info += f"🔴 Status: *CURRENTLY UNAVAILABLE*\n\n"
    
    # OVR range with visual indicator
    info += "🏏 *PLAYER CRITERIA:*\n"
    
    if pack['min_ovr'] is not None or pack['max_ovr'] is not None:
        min_ovr = pack['min_ovr'] if pack['min_ovr'] is not None else 0
        max_ovr = pack['max_ovr'] if pack['max_ovr'] is not None else 100
        
        # Add a quality indicator based on min OVR
        quality_indicator = ""
        if min_ovr >= 90:
            quality_indicator = "🟩 Elite Quality"
        elif min_ovr >= 75:
            quality_indicator = "🟨 High Quality"
        elif min_ovr >= 60:
            quality_indicator = "🟧 Medium Quality" 
        else:
            quality_indicator = "🟥 Basic Quality"
            
        info += f"📊 OVR Range: {min_ovr}-{max_ovr} {quality_indicator}\n"
    
    # Available tiers with emojis
    if 'tiers' in pack and pack['tiers']:
        info += "🏆 Tiers: "
        
        # Handle both string and list formats for tiers
        if isinstance(pack['tiers'], str):
            tiers = pack['tiers'].split(',')
        else:
            tiers = pack['tiers']
            
        tier_displays = []
        for tier in tiers:
            if isinstance(tier, str):
                tier_name = tier.strip()
                emoji = get_tier_emoji(tier_name)
                tier_displays.append(f"{emoji} {tier_name}")
        
        info += f"{' • '.join(tier_displays)}\n"
    
    # Special limited time or promotional indicator
    if pack.get('is_special'):
        info += "\n🌟 *SPECIAL OFFER!* 🌟\n"
    elif pack.get('is_limited'):
        info += "\n⏱️ *LIMITED TIME OFFER!* ⏱️\n"
    
    # Pack image if available (as note, actual image is sent separately)
    if pack.get('image_url'):
        info += "\n🖼️ *Pack includes showcase image*"
    
    # Add a note about what's in the pack
    info += "\n\n💡 *Open this pack to discover new players for your collection!*"
    
    return info


def format_user_info(user, include_players=False):
    """Format user information for display"""
    if not user:
        return "User not found"
    
    # Format user information with enhanced markdown formatting and decorative elements
    info = f"👤 *USER PROFILE* 👤\n"
    info += f"{'━' * 20}\n\n"
    
    # Basic information section with improved visual hierarchy
    info += "📋 *BASIC INFORMATION:*\n"
    info += f"🆔 ID: `{user['telegram_id']}`\n"
    if user.get('name'):
        info += f"📝 Name: `{user['name']}`\n"
    
    # Coins with visual money bag and formatted number
    coins = user['coins']
    
    # Create visual coin bar
    def coin_meter(value, max_value=15000, segments=10):
        filled = min(segments, int((value / max_value) * segments))
        return "█" * filled + "▒" * (segments - filled)
    
    # Add visual indicator based on coin amount
    coin_indicator = ""
    if coins >= 10000:
        coin_indicator = "🤑 *RICH!*"
    elif coins >= 5000:
        coin_indicator = "💎 *Wealthy*"
    elif coins >= 1000:
        coin_indicator = "💵 *Comfortable*"
    elif coins >= 100:
        coin_indicator = "👛 *Modest*"
    else:
        coin_indicator = "🪙 *Starter*"
        
    # Format coins with comma separator for better readability
    formatted_coins = f"{coins:,}"
    
    info += f"💰 Coins: `{formatted_coins}` {coin_indicator}\n"
    info += f"   {coin_meter(coins)} \n\n"
    
    # Player statistics with enhanced visual elements
    if include_players and 'player_count' in user:
        info += "🏆 *COLLECTION STATS:*\n"
        info += f"🏏 Total Players: `{user['player_count']}`\n"
        
        # Show tier distribution if available with graphical representation
        if 'tier_distribution' in user and user['tier_distribution']:
            info += "📊 *Tier Distribution:*\n"
            
            # Sort tiers in order of rarity (default order is fine for our tiers)
            tier_order = ["Bronze", "Silver", "Gold", "Platinum", "Heroic", "Icons"]
            # Filter to include only tiers that exist in the distribution
            ordered_tiers = [t for t in tier_order if t in user['tier_distribution']]
            
            # Get the highest count for scaling the bars
            max_count = max(user['tier_distribution'].values()) if user['tier_distribution'] else 1
            
            for tier in ordered_tiers:
                count = user['tier_distribution'].get(tier, 0)
                emoji = get_tier_emoji(tier)
                # Add visual bar representing proportion of collection
                bar_length = min(10, int((count / max_count) * 10))
                bar = "█" * bar_length + "▒" * (10 - bar_length)
                info += f"  {emoji} {tier}: `{count}` {bar}\n"
        
        info += "\n"
    
    # Creation date in readable format with calendar emoji
    from datetime import datetime
    created_at = datetime.strptime(user['created_at'], "%Y-%m-%d %H:%M:%S")
    formatted_date = created_at.strftime('%d %b %Y')
    
    # Calculate account age
    now = datetime.now()
    days_active = (now - created_at).days
    
    info += "📅 *ACCOUNT INFO:*\n"
    info += f"📆 Member since: `{formatted_date}`\n"
    
    # Show account age with appropriate indicator
    if days_active > 365:
        years = days_active // 365
        remaining_days = days_active % 365
        
        info += f"🎖️ Account Age: `{years} year"
        if years > 1:
            info += "s"
        if remaining_days > 0:
            info += f", {remaining_days} days`\n"
        else:
            info += "`\n"
    else:
        info += f"⏱️ Account Age: `{days_active} days`\n"
    
    # Add any achievements or special status with decorative elements
    if user.get('is_admin'):
        info += "\n👑 *ADMIN ACCOUNT* 👑"
    elif user.get('vip_status'):
        info += f"\n✨ *VIP STATUS: {user['vip_status'].upper()}* ✨"
    
    # Add a friendly message at the end
    info += "\n\n🎮 *Ready to collect more cricket superstars?*"
    
    return info
