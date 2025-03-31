#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database setup and operations
"""

import os
import sqlite3
import logging
import random
import json
import time
from typing import Tuple, Dict, List, Optional, Any, Union
from sqlite3 import Error

logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.getenv("DB_PATH", "cricket_bot.db")

# Admin IDs (comma-separated list of Telegram user IDs for admins)
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
if not ADMIN_IDS:
    logger.warning("No admin IDs configured. Set ADMIN_IDS environment variable.")


def get_db_connection():
    """Create a connection to the SQLite database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    except Error as e:
        logger.error(f"Database connection error: {e}")
        raise


def init_db():
    """Initialize the database with required tables"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create marketplace listings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS marketplace_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (seller_id) REFERENCES users (id),
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')

        # Create marketplace transactions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS marketplace_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            seller_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES marketplace_listings (id),
            FOREIGN KEY (buyer_id) REFERENCES users (id),
            FOREIGN KEY (seller_id) REFERENCES users (id),
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')
        
        # First drop the tables with foreign key dependencies in reverse order
        drop_tables = False  # Set this to True to force a table schema reset
        
        if drop_tables:
            logger.info("Dropping tables to update schema...")
            try:
                cursor.execute("DROP TABLE IF EXISTS team_players")
                cursor.execute("DROP TABLE IF EXISTS teams")
                logger.info("Tables dropped successfully. Will recreate with updated schema.")
            except Error as e:
                logger.error(f"Error dropping tables: {e}")
        
        # Create players table with enhanced fields
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            team TEXT NOT NULL,
            age INTEGER,
            nationality TEXT,
            batting_type TEXT NOT NULL,
            bowling_type TEXT NOT NULL,
            batting_timing INTEGER NOT NULL,
            batting_technique INTEGER NOT NULL,
            batting_power INTEGER NOT NULL,
            batting_speed INTEGER,
            fielding_ability INTEGER,
            bowling_pace INTEGER NOT NULL,
            bowling_variation INTEGER NOT NULL,
            bowling_accuracy INTEGER NOT NULL,
            bowling_control INTEGER,
            fitness INTEGER,
            batting_ovr INTEGER NOT NULL,
            bowling_ovr INTEGER NOT NULL,
            fielding_ovr INTEGER,
            total_ovr INTEGER NOT NULL,
            image_url TEXT,
            tier TEXT NOT NULL,
            is_in_pack BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create admin table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER NOT NULL UNIQUE,
            name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create users table for players and coin management
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER NOT NULL UNIQUE,
            name TEXT,
            coins INTEGER DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create packs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS packs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            min_players INTEGER NOT NULL DEFAULT 1,
            max_players INTEGER NOT NULL DEFAULT 1,
            min_ovr INTEGER,
            max_ovr INTEGER,
            tiers TEXT NOT NULL,
            image_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create table for user's pack history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pack_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pack_id INTEGER NOT NULL,
            players_obtained TEXT NOT NULL,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (pack_id) REFERENCES packs (id)
        )
        ''')
        
        # Create table for user's player collection
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')
        
        # Create teams table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Create team_players table to store players in teams
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            position INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id),
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        ''')
        
        # Create team strategies table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            batting_aggression REAL DEFAULT 1.0,
            bowling_aggression REAL DEFAULT 1.0,
            batting_focus TEXT DEFAULT "balanced",
            bowling_focus TEXT DEFAULT "balanced",
            field_placement TEXT DEFAULT "standard",
            is_preset BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create team strategy assignments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_strategy_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            strategy_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id),
            FOREIGN KEY (strategy_id) REFERENCES team_strategies (id)
        )
        ''')
        
        # Insert default admins if configured
        for admin_id in ADMIN_IDS:
            cursor.execute(
                "INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)",
                (admin_id,)
            )
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Error as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def is_admin(user_id):
    """Check if a user is an admin"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE telegram_id = ?", (user_id,))
        admin = cursor.fetchone()
        return admin is not None
    except Error as e:
        logger.error(f"Admin check error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def add_player(player_data):
    """Add a new player to the database with optional manual OVR values"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use manual OVR values if provided, otherwise calculate
        if all(key in player_data for key in ['batting_ovr', 'bowling_ovr', 'total_ovr']):
            # Manual OVR values provided
            batting_ovr = player_data['batting_ovr']
            bowling_ovr = player_data['bowling_ovr'] 
            total_ovr = player_data['total_ovr']
        else:
            # Calculate overall ratings
            batting_attrs = [
                player_data['batting_timing'],
                player_data['batting_technique'],
                player_data['batting_power']
            ]
            
            # Add batting_speed if available
            if 'batting_speed' in player_data and player_data['batting_speed'] is not None:
                batting_attrs.append(player_data['batting_speed'])
            
            bowling_attrs = [
                player_data['bowling_pace'],
                player_data['bowling_variation'],
                player_data['bowling_accuracy']
            ]
            
            # Add bowling_control if available
            if 'bowling_control' in player_data and player_data['bowling_control'] is not None:
                bowling_attrs.append(player_data['bowling_control'])
            
            batting_ovr = sum(batting_attrs) // len(batting_attrs)
            bowling_ovr = sum(bowling_attrs) // len(bowling_attrs)
            
            # Calculate fielding_ovr if fielding_ability is provided
            fielding_ovr = player_data.get('fielding_ability', 0)
            
            # Factor in fitness if available
            fitness = player_data.get('fitness', 75)  # Default to 75 if not provided
            
            # Calculate total_ovr with more weight to primary role
            role = player_data['role'].lower()
            if 'batsman' in role:
                total_ovr = int(batting_ovr * 0.6 + bowling_ovr * 0.2 + fielding_ovr * 0.1 + fitness * 0.1)
            elif 'bowler' in role:
                total_ovr = int(bowling_ovr * 0.6 + batting_ovr * 0.2 + fielding_ovr * 0.1 + fitness * 0.1)
            elif 'all-rounder' in role or 'all rounder' in role:
                total_ovr = int(batting_ovr * 0.4 + bowling_ovr * 0.4 + fielding_ovr * 0.1 + fitness * 0.1)
            elif 'wicket' in role:
                total_ovr = int(batting_ovr * 0.3 + fielding_ovr * 0.5 + fitness * 0.2)
            else:
                total_ovr = int((batting_ovr + bowling_ovr + fielding_ovr) / 3)
        
        # Prepare the SQL query and parameters
        fields = [
            'name', 'role', 'team', 'batting_type', 'bowling_type',
            'batting_timing', 'batting_technique', 'batting_power',
            'bowling_pace', 'bowling_variation', 'bowling_accuracy',
            'batting_ovr', 'bowling_ovr', 'total_ovr', 'image_url', 'tier', 'edition'
        ]
        
        values = [
            player_data['name'], player_data['role'], player_data['team'],
            player_data['batting_type'], player_data['bowling_type'],
            player_data['batting_timing'], player_data['batting_technique'], player_data['batting_power'],
            player_data['bowling_pace'], player_data['bowling_variation'], player_data['bowling_accuracy'],
            batting_ovr, bowling_ovr, total_ovr,
            player_data.get('image_url', ''), player_data['tier'], player_data.get('edition', 'Standard')
        ]
        
        # Add optional fields if present
        optional_fields = [
            'age', 'nationality', 'batting_speed', 'fielding_ability', 
            'bowling_control', 'fitness', 'fielding_ovr', 'is_in_pack'
        ]
        
        for field in optional_fields:
            if field in player_data and player_data[field] is not None:
                fields.append(field)
                values.append(player_data[field])
        
        # Build the query dynamically
        placeholders = ', '.join(['?' for _ in range(len(fields))])
        field_list = ', '.join(fields)
        
        query = f"INSERT INTO players ({field_list}) VALUES ({placeholders})"
        cursor.execute(query, values)
        
        player_id = cursor.lastrowid
        conn.commit()
        return player_id
    except Error as e:
        logger.error(f"Error adding player: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_player(player_id):
    """Retrieve a player by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        return dict(player) if player else None
    except Error as e:
        logger.error(f"Error retrieving player: {e}")
        return None
    finally:
        if conn:
            conn.close()


def search_players(search_term):
    """Search for players by name or team"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM players WHERE name LIKE ? OR team LIKE ? ORDER BY name",
            (f"%{search_term}%", f"%{search_term}%")
        )
        players = cursor.fetchall()
        return [dict(player) for player in players]
    except Error as e:
        logger.error(f"Error searching players: {e}")
        return []
    finally:
        if conn:
            conn.close()


def list_all_players(limit=10, offset=0):
    """List all players with pagination"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM players ORDER BY name LIMIT ? OFFSET ?",
            (limit, offset)
        )
        players = cursor.fetchall()
        return [dict(player) for player in players]
    except Error as e:
        logger.error(f"Error listing players: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_player_count():
    """Get the total number of players in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM players")
        result = cursor.fetchone()
        return result['count']
    except Error as e:
        logger.error(f"Error counting players: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def delete_player(player_id):
    """Delete a player from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if player exists
        cursor.execute("SELECT id FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        
        if not player:
            return False, "Player not found"
        
        # Delete the player
        cursor.execute("DELETE FROM players WHERE id = ?", (player_id,))
        
        # Delete related records in user_players
        cursor.execute("DELETE FROM user_players WHERE player_id = ?", (player_id,))
        
        conn.commit()
        return True, f"Player with ID {player_id} has been deleted"
    except Error as e:
        logger.error(f"Error deleting player: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_or_create_user(telegram_id, name=None):
    """Get a user or create if not exists"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        if user:
            # Update last active time
            cursor.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                (telegram_id,)
            )
            conn.commit()
            return dict(user)
        
        # Create new user
        cursor.execute(
            "INSERT INTO users (telegram_id, name) VALUES (?, ?)",
            (telegram_id, name or "User")
        )
        
        conn.commit()
        
        # Get the new user
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        new_user = cursor.fetchone()
        return dict(new_user)
    except Error as e:
        logger.error(f"Error managing user: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_by_id(user_id):
    """Get user by database ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except Error as e:
        logger.error(f"Error retrieving user by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_coins(telegram_id):
    """Get a user's coin balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT coins FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        
        if result:
            return result['coins']
        return 0
    except Error as e:
        logger.error(f"Error getting user coins: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def update_user_coins(user_id, amount):
    """Update a user's coin balance (positive for adding, negative for spending)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determine if this is a telegram_id or a database user_id
        if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
            # Get current balance
            cursor.execute("SELECT coins FROM users WHERE telegram_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "User not found"
            
            current_coins = result['coins']
            new_balance = current_coins + amount
            
            # Don't allow negative balance
            if new_balance < 0:
                return False, "Insufficient coins"
            
            # Update balance
            cursor.execute(
                "UPDATE users SET coins = ? WHERE telegram_id = ?",
                (new_balance, user_id)
            )
        else:
            # Treat as database user_id
            cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "User not found"
            
            current_coins = result['coins']
            new_balance = current_coins + amount
            
            # Don't allow negative balance
            if new_balance < 0:
                return False, "Insufficient coins"
            
            # Update balance
            cursor.execute(
                "UPDATE users SET coins = ? WHERE id = ?",
                (new_balance, user_id)
            )
        
        conn.commit()
        return True, new_balance
    except Error as e:
        logger.error(f"Error updating user coins: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


# Team management functions
def create_team(user_id, team_data):
    """Create a new team for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the database user ID from the Telegram ID
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return False, "User not found"
        
        # Get the actual database user ID from the result
        db_user_id = user['id']
        
        # Debug logging
        logger.info(f"Creating team '{team_data['name']}' for user ID {db_user_id} (telegram ID: {user_id})")
        
        # Insert the team with the database user ID, not telegram ID
        cursor.execute('''
        INSERT INTO teams (user_id, name, description)
        VALUES (?, ?, ?)
        ''', (db_user_id, team_data['name'], team_data.get('description', '')))
        
        team_id = cursor.lastrowid
        conn.commit()
        
        # Log successful creation
        logger.info(f"Team created with ID {team_id} for user {db_user_id}")
        
        return True, team_id
    except Error as e:
        logger.error(f"Error creating team: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_team(team_id, user_id=None):
    """Get a team by ID with optional user ID check for security"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_id is not None:
            # First, get the database user ID from the Telegram ID if it's a Telegram ID
            if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
                user_result = cursor.fetchone()
                if user_result:
                    db_user_id = user_result['id']
                else:
                    return None  # User not found
            else:
                db_user_id = user_id
                
            # If user_id provided, ensure team belongs to user
            cursor.execute(
                "SELECT * FROM teams WHERE id = ? AND user_id = ?", 
                (team_id, db_user_id)
            )
        else:
            # Otherwise just get the team
            cursor.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        
        team = cursor.fetchone()
        
        if not team:
            return None
        
        # Convert to dict
        team_dict = dict(team)
        
        # Get players in this team
        cursor.execute('''
        SELECT p.*, tp.position 
        FROM players p
        JOIN team_players tp ON p.id = tp.player_id
        WHERE tp.team_id = ?
        ORDER BY tp.position
        ''', (team_id,))
        
        players = cursor.fetchall()
        team_dict['players'] = [dict(player) for player in players]
        
        # Get role counts for the team
        team_dict['role_counts'] = count_team_roles(team_dict['players'])
        
        return team_dict
    except Error as e:
        logger.error(f"Error retrieving team: {e}")
        return None
    finally:
        if conn:
            conn.close()


def count_team_roles(players):
    """Count the number of players by role in a team"""
    role_counts = {
        'batsman': 0,
        'bowler': 0,
        'all-rounder': 0,
        'wicket-keeper': 0
    }
    
    for player in players:
        role = player['role'].lower()
        if role in role_counts:
            role_counts[role] += 1
        
    return role_counts


def get_user_teams(user_id):
    """Get all teams belonging to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, get the database user ID from the Telegram ID if it's a Telegram ID
        if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
            user_result = cursor.fetchone()
            if user_result:
                db_user_id = user_result['id']
            else:
                return []  # User not found
        else:
            db_user_id = user_id
        
        cursor.execute(
            "SELECT * FROM teams WHERE user_id = ? ORDER BY created_at DESC", 
            (db_user_id,)
        )
        
        teams = cursor.fetchall()
        
        # For each team, count the number of players
        result = []
        for team in teams:
            team_dict = dict(team)
            
            # Count players
            cursor.execute(
                "SELECT COUNT(*) as count FROM team_players WHERE team_id = ?", 
                (team['id'],)
            )
            
            count = cursor.fetchone()['count']
            team_dict['player_count'] = count
            
            result.append(team_dict)
        
        return result
    except Error as e:
        logger.error(f"Error retrieving user teams: {e}")
        return []
    finally:
        if conn:
            conn.close()


def validate_team_composition(role_counts, new_player_role):
    """Validate team composition based on cricket rules
    
    Limits:
    - Wicket Keepers: minimum 1, maximum 2
    - Batsmen: minimum 4, maximum 6
    - Bowlers: minimum 4, maximum 6
    - All-rounders: minimum 1, maximum 2
    - Total: 11 players
    """
    # Create a copy of the counts to simulate adding the new player
    new_counts = role_counts.copy()
    
    # Add the new player
    if new_player_role in new_counts:
        new_counts[new_player_role] += 1
    
    # Calculate total players after adding the new one
    total_players = sum(new_counts.values())
    
    # Check if team would exceed 11 players
    if total_players > 11:
        return False, "A cricket team cannot have more than 11 players."
    
    # Only check for max limits because we don't want to block adding players
    # until the team is complete. We'll give guidance in the team view instead.
    
    # Check wicket-keeper limit (max 2)
    if new_player_role == "wicket-keeper" and new_counts["wicket-keeper"] > 2:
        return False, "Your team cannot have more than 2 wicket-keepers."
    
    # Check batsmen limit (max 6)
    if new_player_role == "batsman" and new_counts["batsman"] > 6:
        return False, "Your team cannot have more than 6 batsmen."
    
    # Check bowler limit (max 6)
    if new_player_role == "bowler" and new_counts["bowler"] > 6:
        return False, "Your team cannot have more than 6 bowlers."
    
    # Check all-rounder limit (max 2)
    if new_player_role == "all-rounder" and new_counts["all-rounder"] > 2:
        return False, "Your team cannot have more than 2 all-rounders."
    
    return True, "Player role is valid for this team."


def add_player_to_team(team_id, player_id, position=None, user_id=None):
    """Add a player to a team at the specified position with role-based validation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If user_id is provided, verify ownership of the team
        if user_id is not None:
            # First, get the database user ID from the Telegram ID if it's a Telegram ID
            if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
                user_result = cursor.fetchone()
                if user_result:
                    db_user_id = user_result['id']
                else:
                    return False, "User not found"
            else:
                db_user_id = user_id
                
            # Verify team ownership
            cursor.execute(
                "SELECT id FROM teams WHERE id = ? AND user_id = ?", 
                (team_id, db_user_id)
            )
            team = cursor.fetchone()
            
            if not team:
                return False, "Team not found or you don't have access"
            
            # Verify user owns this player by checking user_players
            cursor.execute("""
                SELECT up.id FROM user_players up
                JOIN users u ON up.user_id = u.id
                WHERE (u.id = ? OR u.telegram_id = ?) AND up.player_id = ?
            """, (db_user_id, user_id, player_id))
            
            user_player = cursor.fetchone()
            if not user_player:
                # Debug info about the player and user
                cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
                player_info = cursor.fetchone()
                
                if not player_info:
                    return False, f"Player with ID {player_id} not found"
                
                # Log user's players for debugging
                logger.info(f"User {user_id} (DB ID: {db_user_id}) tried to add player {player_id} but doesn't own it")
                logger.info(f"Player exists: {player_info['name'] if player_info else 'No'}")
                
                return False, "You don't own this player. Please select a player you own."
        
        # Check if player already in team
        cursor.execute(
            "SELECT id FROM team_players WHERE team_id = ? AND player_id = ?", 
            (team_id, player_id)
        )
        
        existing = cursor.fetchone()
        if existing:
            return False, "Player is already in this team"
        
        # Check if position is already filled
        if position is not None:
            cursor.execute(
                "SELECT id FROM team_players WHERE team_id = ? AND position = ?",
                (team_id, position)
            )
            
            existing_position = cursor.fetchone()
            if existing_position:
                return False, f"Position {position} is already filled"
        
        # Get the player's role
        cursor.execute("SELECT role FROM players WHERE id = ?", (player_id,))
        player_result = cursor.fetchone()
        
        if not player_result:
            return False, "Player not found"
        
        player_role = player_result['role'].lower()
        
        # Get the team with all its players
        cursor.execute('''
            SELECT p.* 
            FROM players p
            JOIN team_players tp ON p.id = tp.player_id
            WHERE tp.team_id = ?
        ''', (team_id,))
        
        team_players = cursor.fetchall()
        team_players_list = [dict(player) for player in team_players]
        
        # Count players by role
        role_counts = count_team_roles(team_players_list)
        
        # Apply team composition rules
        valid, message = validate_team_composition(role_counts, player_role)
        if not valid:
            return False, message
        
        # Add player to team
        cursor.execute(
            "INSERT INTO team_players (team_id, player_id, position) VALUES (?, ?, ?)",
            (team_id, player_id, position)
        )
        
        conn.commit()
        return True, "Player added to team"
    except Error as e:
        logger.error(f"Error adding player to team: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def remove_player_from_team(team_id, player_id, user_id=None):
    """Remove a player from a team"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If user_id is provided, verify ownership
        if user_id is not None:
            # First, get the database user ID from the Telegram ID if it's a Telegram ID
            if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
                user_result = cursor.fetchone()
                if user_result:
                    db_user_id = user_result['id']
                else:
                    return False, "User not found"
            else:
                db_user_id = user_id
                
            # Verify team ownership
            cursor.execute(
                "SELECT id FROM teams WHERE id = ? AND user_id = ?", 
                (team_id, db_user_id)
            )
            team = cursor.fetchone()
            
            if not team:
                return False, "Team not found or you don't have access"
        
        # Check if player is in team
        cursor.execute(
            "SELECT id FROM team_players WHERE team_id = ? AND player_id = ?", 
            (team_id, player_id)
        )
        
        existing = cursor.fetchone()
        if not existing:
            return False, "Player is not in this team"
        
        # Remove player from team
        cursor.execute(
            "DELETE FROM team_players WHERE team_id = ? AND player_id = ?",
            (team_id, player_id)
        )
        
        conn.commit()
        return True, "Player removed from team"
    except Error as e:
        logger.error(f"Error removing player from team: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def delete_team(team_id, user_id=None):
    """Delete a team and all its players"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If user_id is provided, verify ownership
        if user_id is not None:
            # First, get the database user ID from the Telegram ID if it's a Telegram ID
            if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
                user_result = cursor.fetchone()
                if user_result:
                    db_user_id = user_result['id']
                else:
                    return False, "User not found"
            else:
                db_user_id = user_id
                
            # Verify team ownership
            cursor.execute(
                "SELECT id FROM teams WHERE id = ? AND user_id = ?", 
                (team_id, db_user_id)
            )
            team = cursor.fetchone()
            
            if not team:
                return False, "Team not found or you don't have access"
        
        # Delete team players first (foreign key constraint)
        cursor.execute("DELETE FROM team_players WHERE team_id = ?", (team_id,))
        
        # Then delete the team
        cursor.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        
        conn.commit()
        return True, "Team deleted successfully"
    except Error as e:
        logger.error(f"Error deleting team: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def update_team(team_id, team_data, user_id=None):
    """Update team information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # If user_id is provided, verify ownership
        if user_id is not None:
            # First, get the database user ID from the Telegram ID if it's a Telegram ID
            if isinstance(user_id, int) and user_id > 1000000:  # Likely a telegram_id
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user_id,))
                user_result = cursor.fetchone()
                if user_result:
                    db_user_id = user_result['id']
                else:
                    return False, "User not found"
            else:
                db_user_id = user_id
            
            # Verify team ownership
            cursor.execute(
                "SELECT id FROM teams WHERE id = ? AND user_id = ?", 
                (team_id, db_user_id)
            )
            team = cursor.fetchone()
            
            if not team:
                return False, "Team not found or you don't have access"
        
        # Update team information
        cursor.execute(
            "UPDATE teams SET name = ?, description = ? WHERE id = ?",
            (team_data.get('name'), team_data.get('description'), team_id)
        )
        
        conn.commit()
        return True, "Team updated successfully"
    except Error as e:
        logger.error(f"Error updating team: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


# Pack management functions
def add_pack(pack_data):
    """Add a new pack to the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert tiers list to comma-separated string if it's a list
        if isinstance(pack_data.get('tiers'), list):
            pack_data['tiers'] = ','.join(pack_data['tiers'])
        
        cursor.execute('''
        INSERT INTO packs (
            name, description, price, min_players, max_players, 
            min_ovr, max_ovr, tiers, image_url, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pack_data['name'],
            pack_data.get('description', ''),
            pack_data['price'],
            pack_data.get('min_players', 1),
            pack_data.get('max_players', 1),
            pack_data.get('min_ovr'),
            pack_data.get('max_ovr'),
            pack_data['tiers'],
            pack_data.get('image_url', ''),
            pack_data.get('is_active', 1)
        ))
        
        pack_id = cursor.lastrowid
        conn.commit()
        return pack_id
    except Error as e:
        logger.error(f"Error adding pack: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_pack(pack_id):
    """Get a pack by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
        pack = cursor.fetchone()
        
        if pack:
            pack_dict = dict(pack)
            # Convert tiers string back to list
            if 'tiers' in pack_dict:
                pack_dict['tiers'] = pack_dict['tiers'].split(',')
            return pack_dict
        return None
    except Error as e:
        logger.error(f"Error getting pack: {e}")
        return None
    finally:
        if conn:
            conn.close()


def list_packs(active_only=True):
    """List all packs, optionally filtering for active ones only"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute("SELECT * FROM packs WHERE is_active = 1 ORDER BY price")
        else:
            cursor.execute("SELECT * FROM packs ORDER BY price")
        
        packs = cursor.fetchall()
        result = []
        
        for pack in packs:
            pack_dict = dict(pack)
            # Convert tiers string back to list
            if 'tiers' in pack_dict:
                pack_dict['tiers'] = pack_dict['tiers'].split(',')
            result.append(pack_dict)
        
        return result
    except Error as e:
        logger.error(f"Error listing packs: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_pack_players(pack_id):
    """Get eligible players for a specific pack"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get pack details
        cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
        pack = cursor.fetchone()
        
        if not pack:
            return []
        
        # Build query conditions based on pack criteria
        conditions = []  # Removed is_in_pack condition
        params = []
        
        if pack['min_ovr'] is not None:
            conditions.append("total_ovr >= ?")
            params.append(pack['min_ovr'])
        
        if pack['max_ovr'] is not None:
            conditions.append("total_ovr <= ?")
            params.append(pack['max_ovr'])
        
        # Handle tiers
        tiers = pack['tiers'].split(',')
        tier_placeholders = ', '.join(['?' for _ in tiers])
        conditions.append(f"tier IN ({tier_placeholders})")
        params.extend(tiers)
        
        # Construct and execute the query
        query = "SELECT * FROM players"
        if conditions:
            query += f" WHERE {' AND '.join(conditions)}"
        
        cursor.execute(query, params)
        
        players = cursor.fetchall()
        return [dict(player) for player in players]
    except Error as e:
        logger.error(f"Error getting pack players: {e}")
        return []
    finally:
        if conn:
            conn.close()


def open_pack(user_id, pack_id):
    """Open a pack and get random players"""
    import random
    import json
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get pack details
        cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
        pack = cursor.fetchone()
        
        if not pack:
            return False, "Pack not found"
        
        # Get user details
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return False, "User not found"
        
        # Check if user has enough coins
        if user['coins'] < pack['price']:
            return False, "Insufficient coins"
        
        # Get eligible players for this pack
        eligible_players = get_pack_players(pack_id)
        
        if not eligible_players:
            return False, "No eligible players found for this pack"
        
        # Determine number of players to include
        num_players = random.randint(pack['min_players'], pack['max_players'])
        
        # Select random players
        if len(eligible_players) <= num_players:
            selected_players = eligible_players
        else:
            selected_players = random.sample(eligible_players, num_players)
        
        # Deduct coins from user
        cursor.execute(
            "UPDATE users SET coins = coins - ? WHERE telegram_id = ?",
            (pack['price'], user_id)
        )
        
        # Add players to user's collection
        player_ids = []
        for player in selected_players:
            cursor.execute(
                "INSERT INTO user_players (user_id, player_id) VALUES (?, ?)",
                (user['id'], player['id'])
            )
            player_ids.append(player['id'])
        
        # Record pack opening in history
        cursor.execute(
            "INSERT INTO pack_history (user_id, pack_id, players_obtained) VALUES (?, ?, ?)",
            (user['id'], pack_id, json.dumps(player_ids))
        )
        
        conn.commit()
        
        return True, {
            "pack_name": pack['name'],
            "price": pack['price'],
            "players": selected_players
        }
    except Error as e:
        logger.error(f"Error opening pack: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_user_players(telegram_id):
    """Get all players owned by a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            return []
        
        # Get user's players
        cursor.execute('''
            SELECT p.* FROM players p
            JOIN user_players up ON p.id = up.player_id
            WHERE up.user_id = ?
            ORDER BY p.total_ovr DESC
        ''', (user['id'],))
        
        players = cursor.fetchall()
        return [dict(player) for player in players]
    except Error as e:
        logger.error(f"Error getting user players: {e}")
        return []
    finally:
        if conn:
            conn.close()


def health_check_db():
    """Check if the database is accessible"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return True
    except Error as e:
        logger.error(f"Database health check failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Admin functions
def get_all_users():
    """Get all users in the system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users ORDER BY name")
        users = cursor.fetchall()
        
        return [dict(u) for u in users]
    except Error as e:
        logger.error(f"Error getting all users: {e}")
        return []
    finally:
        if conn:
            conn.close()


def find_user_by_username(username):
    """Find a user by username (partial match)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use LIKE to find username matches
        cursor.execute("SELECT * FROM users WHERE name LIKE ? ORDER BY name", (f"%{username}%",))
        users = cursor.fetchall()
        
        return [dict(u) for u in users]
    except Error as e:
        logger.error(f"Error finding user by username: {e}")
        return []
    finally:
        if conn:
            conn.close()


def give_player_to_user(telegram_id, player_id):
    """Give a specific player to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            return False, "User not found"
        
        # Check if player exists
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cursor.fetchone()
        
        if not player:
            return False, "Player not found"
        
        # Check if user already has this player
        cursor.execute(
            "SELECT * FROM user_players WHERE user_id = ? AND player_id = ?",
            (user['id'], player_id)
        )
        
        existing = cursor.fetchone()
        if existing:
            return False, f"User already has player {player['name']}"
        
        # Add player to user's collection
        cursor.execute(
            "INSERT INTO user_players (user_id, player_id) VALUES (?, ?)",
            (user['id'], player_id)
        )
        
        conn.commit()
        return True, f"Player {player['name']} given to user {user['name']}"
    except Error as e:
        logger.error(f"Error giving player to user: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def delete_user_data(telegram_id, delete_options):
    """Delete specific user data based on provided options
    
    Args:
        telegram_id: The Telegram ID of the user
        delete_options: Dictionary with keys 'players', 'coins', 'teams', 'marketplace', indicating what to delete
        
    Returns:
        Tuple of (success, message)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user's database ID
        cursor.execute("SELECT id, name FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            return False, "User not found"
        
        user_id = user["id"]
        user_name = user["name"]
        
        result_messages = []
        
        # Delete user's players
        if delete_options.get('players', False):
            # Get count first for the message
            cursor.execute("SELECT COUNT(*) as count FROM user_players WHERE user_id = ?", (user_id,))
            player_count = cursor.fetchone()["count"]
            
            # Then delete the records
            cursor.execute("DELETE FROM user_players WHERE user_id = ?", (user_id,))
            result_messages.append(f"Deleted {player_count} players")
        
        # Reset user's coins
        if delete_options.get('coins', False):
            cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
            current_coins = cursor.fetchone()["coins"]
            
            cursor.execute("UPDATE users SET coins = 0 WHERE id = ?", (user_id,))
            result_messages.append(f"Reset {current_coins} coins to 0")
        
        # Delete user's teams
        if delete_options.get('teams', False):
            # First count the teams for the message
            cursor.execute("SELECT COUNT(*) as count FROM teams WHERE user_id = ?", (user_id,))
            team_count = cursor.fetchone()["count"]
            
            # Delete team players associations
            cursor.execute("""
                DELETE FROM team_players
                WHERE team_id IN (SELECT id FROM teams WHERE user_id = ?)
            """, (user_id,))
            
            # Delete team strategy assignments
            cursor.execute("""
                DELETE FROM team_strategy_assignments
                WHERE team_id IN (SELECT id FROM teams WHERE user_id = ?)
            """, (user_id,))
            
            # Delete the teams
            cursor.execute("DELETE FROM teams WHERE user_id = ?", (user_id,))
            
            result_messages.append(f"Deleted {team_count} teams")
        
        # Delete marketplace listings
        if delete_options.get('marketplace', False):
            cursor.execute("""
                UPDATE marketplace_listings 
                SET is_active = 0 
                WHERE seller_id = ? AND is_active = 1
            """, (user_id,))
            
            affected_rows = cursor.rowcount
            result_messages.append(f"Removed {affected_rows} marketplace listings")
        
        conn.commit()
        
        # Format a nice summary message
        if not result_messages:
            return False, "No data was selected for deletion"
            
        summary = f"Data deleted for user {user_name} (ID: {telegram_id}):\n• " + "\n• ".join(result_messages)
        
        return True, summary
    except Error as e:
        logger.error(f"Error giving player to user: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def update_pack_status(pack_id, is_active):
    """Update the active status of a pack"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE packs SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, pack_id)
        )
        
        if cursor.rowcount == 0:
            return False, "Pack not found"
        
        conn.commit()
        return True, "Pack status updated successfully"
    except Error as e:
        logger.error(f"Error updating pack status: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def delete_pack(pack_id):
    """Delete a pack"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM packs WHERE id = ?", (pack_id,))
        
        if cursor.rowcount == 0:
            return False, "Pack not found"
        
        conn.commit()
        return True, "Pack deleted successfully"
    except Error as e:
        logger.error(f"Error deleting pack: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def get_base_price_by_tier(tier: str) -> int:
    """Get base price for a tier"""
    tier_prices = {
        "Bronze": 1000,
        "Silver": 2500,
        "Gold": 5000,
        "Platinum": 10000,
        "Heroic": 25000,
        "Icons": 50000
    }
    return tier_prices.get(tier, 1000)

def calculate_player_value(player_id: int) -> Dict:
    """Calculate the market value of a player based on attributes, rarity, and market factors
    
    Returns a dictionary with:
    - suggested_price: the calculated market value
    - value_factors: breakdown of what contributes to the price
    - price_range: min and max recommended price
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get player details
        cursor.execute("""
            SELECT p.*, 
                   COUNT(DISTINCT up.user_id) as ownership_count,
                   (SELECT COUNT(*) FROM users) as total_users
            FROM players p
            LEFT JOIN user_players up ON p.id = up.player_id
            WHERE p.id = ?
            GROUP BY p.id
        """, (player_id,))
        
        player = cursor.fetchone()
        if not player:
            return {
                "suggested_price": 0,
                "value_factors": {"error": "Player not found"},
                "price_range": {"min": 0, "max": 0}
            }
            
        # Base price from tier
        base_price = get_base_price_by_tier(player["tier"])
        
        # Calculate rarity factor based on ownership percentage
        ownership_percent = (player["ownership_count"] / max(player["total_users"], 1)) * 100
        if ownership_percent < 5:
            rarity_factor = 2.0  # Very rare
        elif ownership_percent < 15:
            rarity_factor = 1.5  # Rare
        elif ownership_percent < 30:
            rarity_factor = 1.2  # Uncommon
        else:
            rarity_factor = 1.0  # Common
            
        # Performance factor based on OVR
        if player["total_ovr"] >= 90:
            performance_factor = 2.0
        elif player["total_ovr"] >= 85:
            performance_factor = 1.8
        elif player["total_ovr"] >= 80:
            performance_factor = 1.5
        elif player["total_ovr"] >= 75:
            performance_factor = 1.3
        elif player["total_ovr"] >= 70:
            performance_factor = 1.1
        else:
            performance_factor = 1.0
            
        # Role factor - some roles may be more in demand
        role_weights = {
            "Batsman": 1.2,
            "Bowler": 1.2, 
            "All-rounder": 1.5,
            "Wicket Keeper": 1.3
        }
        role_factor = role_weights.get(player["role"], 1.0)
        
        # Calculate recent market trends for similar players
        cursor.execute("""
            SELECT AVG(t.price) as avg_price
            FROM marketplace_transactions t
            JOIN players p ON t.player_id = p.id
            WHERE p.tier = ? AND p.role = ?
            AND t.created_at >= datetime('now', '-14 days')
        """, (player["tier"], player["role"]))
        
        trend_data = cursor.fetchone()
        if trend_data and trend_data["avg_price"]:
            market_trend_factor = trend_data["avg_price"] / max(base_price, 1)
            # Limit extreme variations
            market_trend_factor = max(0.7, min(market_trend_factor, 1.3))
        else:
            market_trend_factor = 1.0
        
        # Calculate final value
        calculated_value = int(base_price * rarity_factor * performance_factor * role_factor * market_trend_factor)
        
        # Create price range (±15%)
        min_price = int(calculated_value * 0.85)
        max_price = int(calculated_value * 1.15)
        
        return {
            "suggested_price": calculated_value,
            "value_factors": {
                "base_price": base_price,
                "rarity_factor": round(rarity_factor, 2),
                "performance_factor": round(performance_factor, 2),
                "role_factor": round(role_factor, 2),
                "market_trend_factor": round(market_trend_factor, 2)
            },
            "price_range": {"min": min_price, "max": max_price}
        }
        
    except Error as e:
        logger.error(f"Error calculating player value: {e}")
        return {
            "suggested_price": get_base_price_by_tier(player.get("tier", "Bronze") if player else "Bronze"),
            "value_factors": {"error": str(e)},
            "price_range": {"min": 0, "max": 0}
        }
    finally:
        if conn:
            conn.close()

def get_market_insights() -> Dict:
    """Get market insights such as popular roles, average prices, and trends
    
    Returns a dictionary with market statistics and insights
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insights = {}
        
        # Most traded roles in the last 7 days
        cursor.execute("""
            SELECT p.role, COUNT(*) as trade_count
            FROM marketplace_transactions t
            JOIN players p ON t.player_id = p.id
            WHERE t.created_at >= datetime('now', '-7 days')
            GROUP BY p.role
            ORDER BY trade_count DESC
        """)
        most_traded_roles = cursor.fetchall()
        insights["most_traded_roles"] = most_traded_roles
        
        # Average prices by tier
        cursor.execute("""
            SELECT p.tier, AVG(t.price) as avg_price
            FROM marketplace_transactions t
            JOIN players p ON t.player_id = p.id
            WHERE t.created_at >= datetime('now', '-14 days')
            GROUP BY p.tier
            ORDER BY avg_price DESC
        """)
        avg_prices_by_tier = cursor.fetchall()
        insights["avg_prices_by_tier"] = avg_prices_by_tier
        
        # Most expensive recent sales
        cursor.execute("""
            SELECT p.name, p.tier, p.role, t.price, t.created_at
            FROM marketplace_transactions t
            JOIN players p ON t.player_id = p.id
            ORDER BY t.price DESC
            LIMIT 5
        """)
        top_sales = cursor.fetchall()
        insights["top_sales"] = top_sales
        
        # Recent price changes (comparing last 7 days to previous 7 days)
        cursor.execute("""
            WITH last_week AS (
                SELECT p.tier, AVG(t.price) as avg_price
                FROM marketplace_transactions t
                JOIN players p ON t.player_id = p.id
                WHERE t.created_at BETWEEN datetime('now', '-7 days') AND datetime('now')
                GROUP BY p.tier
            ),
            previous_week AS (
                SELECT p.tier, AVG(t.price) as avg_price
                FROM marketplace_transactions t
                JOIN players p ON t.player_id = p.id
                WHERE t.created_at BETWEEN datetime('now', '-14 days') AND datetime('now', '-7 days')
                GROUP BY p.tier
            )
            SELECT lw.tier, lw.avg_price, 
                   CASE WHEN pw.avg_price IS NULL THEN 0
                        ELSE (lw.avg_price - pw.avg_price) / pw.avg_price * 100
                   END as price_change_percent
            FROM last_week lw
            LEFT JOIN previous_week pw ON lw.tier = pw.tier
        """)
        price_trends = cursor.fetchall()
        insights["price_trends"] = price_trends
        
        return insights
        
    except Error as e:
        logger.error(f"Error getting market insights: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def get_player_price_history(player_id: int) -> List[Dict]:
    """Get price history for a specific player
    
    Returns a list of historical prices from marketplace transactions
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get player transaction history
        cursor.execute("""
            SELECT t.price, t.created_at
            FROM marketplace_transactions t
            WHERE t.player_id = ?
            ORDER BY t.created_at DESC
            LIMIT 10
        """, (player_id,))
        
        transactions = cursor.fetchall()
        return [dict(t) for t in transactions]
        
    except Error as e:
        logger.error(f"Error getting player price history: {e}")
        return []
    finally:
        if conn:
            conn.close()


# Team Strategy Functions
def create_strategy(strategy_data):
    """Create a new team strategy"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert the strategy
        cursor.execute('''
        INSERT INTO team_strategies 
        (name, description, batting_aggression, bowling_aggression, 
         batting_focus, bowling_focus, field_placement, is_preset)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy_data['name'],
            strategy_data.get('description', ''),
            strategy_data.get('batting_aggression', 1.0),
            strategy_data.get('bowling_aggression', 1.0),
            strategy_data.get('batting_focus', 'balanced'),
            strategy_data.get('bowling_focus', 'balanced'),
            strategy_data.get('field_placement', 'standard'),
            strategy_data.get('is_preset', 1)
        ))
        
        strategy_id = cursor.lastrowid
        conn.commit()
        
        return True, strategy_id
    except Error as e:
        logger.error(f"Error creating strategy: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_strategy(strategy_id):
    """Get a strategy by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM team_strategies WHERE id = ?", (strategy_id,))
        strategy = cursor.fetchone()
        
        if not strategy:
            return None
            
        return dict(strategy)
    except Error as e:
        logger.error(f"Error retrieving strategy: {e}")
        return None
    finally:
        if conn:
            conn.close()


def list_strategies(preset_only=False):
    """List all available strategies, optionally filtering for presets only"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if preset_only:
            cursor.execute("SELECT * FROM team_strategies WHERE is_preset = 1")
        else:
            cursor.execute("SELECT * FROM team_strategies")
            
        strategies = cursor.fetchall()
        return [dict(strategy) for strategy in strategies]
    except Error as e:
        logger.error(f"Error listing strategies: {e}")
        return []
    finally:
        if conn:
            conn.close()


def assign_strategy_to_team(team_id, strategy_id):
    """Assign a strategy to a team"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First check if the team already has a strategy
        cursor.execute(
            "SELECT id FROM team_strategy_assignments WHERE team_id = ?", 
            (team_id,)
        )
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing assignment
            cursor.execute(
                "UPDATE team_strategy_assignments SET strategy_id = ?, assigned_at = CURRENT_TIMESTAMP WHERE team_id = ?",
                (strategy_id, team_id)
            )
        else:
            # Create new assignment
            cursor.execute(
                "INSERT INTO team_strategy_assignments (team_id, strategy_id) VALUES (?, ?)",
                (team_id, strategy_id)
            )
            
        conn.commit()
        return True, "Strategy assigned successfully"
    except Error as e:
        logger.error(f"Error assigning strategy: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_team_strategy(team_id):
    """Get the strategy assigned to a team"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT ts.* 
        FROM team_strategies ts
        JOIN team_strategy_assignments tsa ON ts.id = tsa.strategy_id
        WHERE tsa.team_id = ?
        ''', (team_id,))
        
        strategy = cursor.fetchone()
        return dict(strategy) if strategy else None
    except Error as e:
        logger.error(f"Error getting team strategy: {e}")
        return None
    finally:
        if conn:
            conn.close()


def initialize_default_strategies():
    """Initialize a set of default strategy presets if none exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if there are any presets
        cursor.execute("SELECT COUNT(*) as count FROM team_strategies WHERE is_preset = 1")
        result = cursor.fetchone()
        
        if result and result['count'] > 0:
            # Already have presets
            return
            
        # Define default strategy presets
        default_strategies = [
            {
                'name': 'Balanced',
                'description': 'A balanced approach to batting and bowling.',
                'batting_aggression': 1.0,
                'bowling_aggression': 1.0,
                'batting_focus': 'balanced',
                'bowling_focus': 'balanced',
                'field_placement': 'standard'
            },
            {
                'name': 'Aggressive',
                'description': 'Focus on attacking with both bat and ball.',
                'batting_aggression': 1.3,
                'bowling_aggression': 1.2,
                'batting_focus': 'attacking',
                'bowling_focus': 'wicket-taking',
                'field_placement': 'attacking'
            },
            {
                'name': 'Defensive',
                'description': 'Cautious approach prioritizing wicket protection and economy.',
                'batting_aggression': 0.7,
                'bowling_aggression': 0.8,
                'batting_focus': 'defensive',
                'bowling_focus': 'economy',
                'field_placement': 'defensive'
            },
            {
                'name': 'Batting Focus',
                'description': 'Prioritize scoring runs with aggressive batting.',
                'batting_aggression': 1.4,
                'bowling_aggression': 0.9,
                'batting_focus': 'attacking',
                'bowling_focus': 'balanced',
                'field_placement': 'standard'
            },
            {
                'name': 'Bowling Focus',
                'description': 'Prioritize taking wickets with aggressive bowling.',
                'batting_aggression': 0.9,
                'bowling_aggression': 1.4,
                'batting_focus': 'balanced',
                'bowling_focus': 'wicket-taking',
                'field_placement': 'attacking'
            }
        ]
        
        # Insert default strategy presets
        for strategy in default_strategies:
            create_strategy(strategy)
            
        conn.commit()
        logger.info("Default strategies initialized")
    except Error as e:
        logger.error(f"Error initializing default strategies: {e}")
    finally:
        if conn:
            conn.close()


def list_player_for_sale(telegram_id: int, player_id: int, price: int) -> Tuple[bool, str]:
    """List a player for sale in the marketplace"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user's database ID
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            return False, "User not found"

        # Check if user owns the player
        cursor.execute(
            "SELECT * FROM user_players WHERE user_id = ? AND player_id = ?",
            (user['id'], player_id)
        )
        if not cursor.fetchone():
            return False, "You don't own this player"

        # Check if player is already listed
        cursor.execute(
            "SELECT * FROM marketplace_listings WHERE player_id = ? AND is_active = 1",
            (player_id,)
        )
        if cursor.fetchone():
            return False, "This player is already listed for sale"

        # Create listing
        cursor.execute(
            "INSERT INTO marketplace_listings (seller_id, player_id, price) VALUES (?, ?, ?)",
            (user['id'], player_id, price)
        )
        conn.commit()
        return True, "Player listed successfully"
    except Error as e:
        logger.error(f"Error listing player: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def buy_player(telegram_id: int, listing_id: int) -> Tuple[bool, str]:
    """Buy a player from the marketplace"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get buyer's database ID and coins
        cursor.execute("SELECT id, coins FROM users WHERE telegram_id = ?", (telegram_id,))
        buyer = cursor.fetchone()
        if not buyer:
            return False, "Buyer not found"

        # Get listing details
        cursor.execute("""
            SELECT l.*, p.name, u.telegram_id as seller_telegram_id 
            FROM marketplace_listings l
            JOIN players p ON l.player_id = p.id
            JOIN users u ON l.seller_id = u.id
            WHERE l.id = ? AND l.is_active = 1
        """, (listing_id,))
        listing = cursor.fetchone()

        if not listing:
            return False, "Listing not found or already sold"

        if buyer['coins'] < listing['price']:
            return False, "Insufficient coins"

        if buyer['id'] == listing['seller_id']:
            return False, "You cannot buy your own player"

        # Process transaction
        # 1. Deduct coins from buyer
        cursor.execute(
            "UPDATE users SET coins = coins - ? WHERE id = ?",
            (listing['price'], buyer['id'])
        )

        # 2. Add coins to seller
        cursor.execute(
            "UPDATE users SET coins = coins + ? WHERE id = ?",
            (listing['price'], listing['seller_id'])
        )

        # 3. Transfer player ownership
        cursor.execute(
            "UPDATE user_players SET user_id = ? WHERE user_id = ? AND player_id = ?",
            (buyer['id'], listing['seller_id'], listing['player_id'])
        )

        # 4. Mark listing as inactive
        cursor.execute(
            "UPDATE marketplace_listings SET is_active = 0 WHERE id = ?",
            (listing_id,)
        )

        # 5. Record transaction
        cursor.execute("""
            INSERT INTO marketplace_transactions 
            (listing_id, buyer_id, seller_id, player_id, price)
            VALUES (?, ?, ?, ?, ?)
        """, (listing_id, buyer['id'], listing['seller_id'], listing['player_id'], listing['price']))

        conn.commit()
        return True, f"Successfully purchased {listing['name']}"
    except Error as e:
        logger.error(f"Error buying player: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def get_marketplace_listings(limit: int = 10, offset: int = 0):
    """Get active marketplace listings"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                l.id as listing_id,
                l.price,
                l.listed_at,
                p.*,
                u.name as seller_name
            FROM marketplace_listings l
            JOIN players p ON l.player_id = p.id
            JOIN users u ON l.seller_id = u.id
            WHERE l.is_active = 1
            ORDER BY l.listed_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        listings = cursor.fetchall()
        return [dict(listing) for listing in listings]
    except Error as e:
        logger.error(f"Error getting marketplace listings: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_user_data(telegram_id: int, delete_options: dict) -> tuple[bool, str]:
    """Delete specific user data based on provided options
    
    Args:
        telegram_id: The Telegram ID of the user
        delete_options: Dictionary with keys 'players', 'coins', 'teams', 'marketplace', indicating what to delete
        
    Returns:
        Tuple of (success, message)
    """
    deleted_items = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID from telegram_id
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            return False, f"User with Telegram ID {telegram_id} not found"
        
        user_id = user['id']
        
        # Delete players if selected
        if delete_options.get('players', False):
            # First count how many players the user has
            cursor.execute("SELECT COUNT(*) as count FROM user_players WHERE user_id = ?", (user_id,))
            player_count = cursor.fetchone()['count']
            
            # Then delete them
            cursor.execute("DELETE FROM user_players WHERE user_id = ?", (user_id,))
            deleted_items.append(f"Deleted {player_count} players")
        
        # Reset coins if selected
        if delete_options.get('coins', False):
            # First get current coins
            cursor.execute("SELECT coins FROM users WHERE id = ?", (user_id,))
            current_coins = cursor.fetchone()['coins']
            
            # Then reset to 0
            cursor.execute("UPDATE users SET coins = 0 WHERE id = ?", (user_id,))
            deleted_items.append(f"Reset {current_coins} coins to 0")
        
        # Delete teams if selected
        if delete_options.get('teams', False):
            # First count how many teams the user has
            cursor.execute("SELECT COUNT(*) as count FROM teams WHERE user_id = ?", (user_id,))
            team_count = cursor.fetchone()['count']
            
            # Get team IDs to delete team players as well
            cursor.execute("SELECT id FROM teams WHERE user_id = ?", (user_id,))
            team_ids = [row['id'] for row in cursor.fetchall()]
            
            # Delete team players first to avoid foreign key constraints
            for team_id in team_ids:
                cursor.execute("DELETE FROM team_players WHERE team_id = ?", (team_id,))
            
            # Then delete the teams
            cursor.execute("DELETE FROM teams WHERE user_id = ?", (user_id,))
            deleted_items.append(f"Deleted {team_count} teams")
        
        # Delete marketplace listings if selected
        if delete_options.get('marketplace', False):
            # First count how many listings the user has
            cursor.execute("""
                SELECT COUNT(*) as count FROM marketplace_listings 
                WHERE seller_id = ? AND is_active = 1
            """, (user_id,))
            listing_count = cursor.fetchone()['count']
            
            # Mark listings as inactive rather than deleting them
            cursor.execute("""
                UPDATE marketplace_listings 
                SET is_active = 0 
                WHERE seller_id = ? AND is_active = 1
            """, (user_id,))
            
            # Also transfer back any players that were listed
            cursor.execute("""
                UPDATE players SET is_listed = 0
                WHERE id IN (
                    SELECT player_id FROM marketplace_listings
                    WHERE seller_id = ?
                )
            """, (user_id,))
            
            deleted_items.append(f"Removed {listing_count} marketplace listings")
        
        conn.commit()
        
        if not deleted_items:
            return False, "No data selected for deletion"
        
        return True, "Successfully deleted the following data:\n• " + "\n• ".join(deleted_items)
    
    except Error as e:
        logger.error(f"Error deleting user data: {e}")
        if conn:
            conn.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        if conn:
            conn.close()


# Player Statistics Functions
def initialize_player_stats(user_id, player_id):
    """
    Initialize statistics tracking for a player owned by a user
    
    Args:
        user_id: The database ID of the user who owns the player
        player_id: The database ID of the player
        
    Returns:
        bool: True if successful, False if error or already exists
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if stats already exist
        cursor.execute(
            "SELECT id FROM player_stats WHERE player_id = ? AND user_id = ?",
            (player_id, user_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            return False  # Stats already exist
        
        # Create initial stats record
        cursor.execute("""
        INSERT INTO player_stats (
            player_id, user_id, 
            matches_played, innings_batted, runs_scored, balls_faced, not_outs,
            fours, sixes, fifties, hundreds, highest_score,
            innings_bowled, overs_bowled, balls_bowled, runs_conceded, 
            wickets_taken, maidens, three_wicket_hauls, five_wicket_hauls, best_bowling,
            player_of_match, matches_won,
            batting_average, batting_strike_rate, 
            bowling_average, bowling_strike_rate, bowling_economy
        ) VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, '0/0', 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
        """, (player_id, user_id))
        
        conn.commit()
        return True
    
    except Error as e:
        logger.error(f"Error initializing player stats: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def update_player_stats_after_match(user_id, players_performance, is_winner=False):
    """
    Update player statistics after a match
    
    Args:
        user_id: The database ID of the user who owns the players
        players_performance: List of dictionaries containing match performance data
            [
                {
                    'player_id': int,
                    'is_batsman': bool,
                    'is_bowler': bool,
                    'runs': int,
                    'balls_faced': int,
                    'is_out': bool,
                    'fours': int,
                    'sixes': int,
                    'wickets': int,
                    'overs_bowled': float,
                    'balls_bowled': int,
                    'runs_conceded': int,
                    'maidens': int,
                    'is_potm': bool (optional)
                }
            ]
        is_winner: Whether the user's team won the match
        
    Returns:
        bool: True if successful, False if error
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_counts = 0
        
        for player in players_performance:
            player_id = player['player_id']
            
            # Check if stats exist for this player
            cursor.execute(
                "SELECT * FROM player_stats WHERE player_id = ? AND user_id = ?",
                (player_id, user_id)
            )
            stats = cursor.fetchone()
            
            if not stats:
                # Initialize stats if they don't exist yet
                initialize_player_stats(user_id, player_id)
                
                # Fetch the newly created stats
                cursor.execute(
                    "SELECT * FROM player_stats WHERE player_id = ? AND user_id = ?",
                    (player_id, user_id)
                )
                stats = cursor.fetchone()
                
                if not stats:
                    logger.error(f"Failed to initialize stats for player {player_id}")
                    continue
            
            # Extract current stats
            stats_dict = dict(stats)
            
            # Update match participation
            matches_played = stats_dict['matches_played'] + 1
            matches_won = stats_dict['matches_won'] + (1 if is_winner else 0)
            
            # Check if player is the Player of the Match
            is_potm = player.get('is_potm', False)
            player_of_match = stats_dict['player_of_match'] + (1 if is_potm else 0)
            
            # Batting stats updates
            batting_updates = {}
            if player.get('is_batsman', False):
                runs = player.get('runs', 0)
                balls_faced = player.get('balls_faced', 0)
                is_out = player.get('is_out', False)
                fours = player.get('fours', 0)
                sixes = player.get('sixes', 0)
                
                innings_batted = stats_dict['innings_batted'] + 1
                runs_scored = stats_dict['runs_scored'] + runs
                total_balls_faced = stats_dict['balls_faced'] + balls_faced
                not_outs = stats_dict['not_outs'] + (0 if is_out else 1)
                total_fours = stats_dict['fours'] + fours
                total_sixes = stats_dict['sixes'] + sixes
                
                # Update fifties and hundreds
                fifties = stats_dict['fifties']
                hundreds = stats_dict['hundreds']
                if runs >= 100:
                    hundreds += 1
                elif runs >= 50:
                    fifties += 1
                
                # Update highest score
                highest_score = max(stats_dict['highest_score'], runs)
                
                # Calculate batting average
                # Batting average = Runs scored / (innings - not outs)
                batting_average = runs_scored / max(1, innings_batted - not_outs)
                
                # Calculate batting strike rate
                # Strike rate = (Runs scored / Balls faced) * 100
                batting_strike_rate = (runs_scored / max(1, total_balls_faced)) * 100
                
                batting_updates = {
                    'innings_batted': innings_batted,
                    'runs_scored': runs_scored,
                    'balls_faced': total_balls_faced,
                    'not_outs': not_outs,
                    'fours': total_fours,
                    'sixes': total_sixes,
                    'fifties': fifties,
                    'hundreds': hundreds,
                    'highest_score': highest_score,
                    'batting_average': round(batting_average, 2),
                    'batting_strike_rate': round(batting_strike_rate, 2)
                }
            
            # Bowling stats updates
            bowling_updates = {}
            if player.get('is_bowler', False):
                wickets = player.get('wickets', 0)
                overs_bowled = player.get('overs_bowled', 0)
                balls_bowled = player.get('balls_bowled', 0)
                runs_conceded = player.get('runs_conceded', 0)
                maidens = player.get('maidens', 0)
                
                innings_bowled = stats_dict['innings_bowled'] + 1
                total_wickets = stats_dict['wickets_taken'] + wickets
                total_overs_bowled = stats_dict['overs_bowled'] + overs_bowled
                total_balls_bowled = stats_dict['balls_bowled'] + balls_bowled
                total_runs_conceded = stats_dict['runs_conceded'] + runs_conceded
                total_maidens = stats_dict['maidens'] + maidens
                
                # Update 3-wicket and 5-wicket hauls
                three_wickets = stats_dict['three_wicket_hauls']
                five_wickets = stats_dict['five_wicket_hauls']
                if wickets >= 5:
                    five_wickets += 1
                elif wickets >= 3:
                    three_wickets += 1
                
                # Update best bowling
                current_best = stats_dict['best_bowling']
                current_best_w, current_best_r = map(int, current_best.split('/'))
                
                # Better bowling = more wickets or same wickets with fewer runs
                if (wickets > current_best_w or 
                    (wickets == current_best_w and runs_conceded < current_best_r)):
                    new_best = f"{wickets}/{runs_conceded}"
                else:
                    new_best = current_best
                
                # Calculate bowling average
                # Bowling average = Runs conceded / Wickets taken
                bowling_average = total_runs_conceded / max(1, total_wickets)
                
                # Calculate bowling strike rate
                # Strike rate = Balls bowled / Wickets taken
                bowling_strike_rate = total_balls_bowled / max(1, total_wickets)
                
                # Calculate bowling economy
                # Economy = (Runs conceded / Balls bowled) * 6
                bowling_economy = (total_runs_conceded / max(1, total_balls_bowled)) * 6
                
                bowling_updates = {
                    'innings_bowled': innings_bowled,
                    'overs_bowled': total_overs_bowled,
                    'balls_bowled': total_balls_bowled,
                    'runs_conceded': total_runs_conceded,
                    'wickets_taken': total_wickets,
                    'maidens': total_maidens,
                    'three_wicket_hauls': three_wickets,
                    'five_wicket_hauls': five_wickets,
                    'best_bowling': new_best,
                    'bowling_average': round(bowling_average, 2),
                    'bowling_strike_rate': round(bowling_strike_rate, 2),
                    'bowling_economy': round(bowling_economy, 2)
                }
            
            # Combine all updates
            all_updates = {
                'matches_played': matches_played,
                'matches_won': matches_won,
                'player_of_match': player_of_match
            }
            all_updates.update(batting_updates)
            all_updates.update(bowling_updates)
            
            # Generate SQL update statement
            update_fields = ", ".join([f"{key} = ?" for key in all_updates.keys()])
            update_values = list(all_updates.values())
            
            # Add WHERE clause parameters
            update_values.append(player_id)
            update_values.append(user_id)
            
            # Execute the update
            cursor.execute(
                f"UPDATE player_stats SET {update_fields} WHERE player_id = ? AND user_id = ?",
                update_values
            )
            update_counts += 1
        
        conn.commit()
        return update_counts > 0
    
    except Error as e:
        logger.error(f"Error updating player stats: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def get_player_stats(user_id, player_id):
    """
    Get statistics for a specific player owned by a user
    
    Args:
        user_id: The database ID of the user who owns the player
        player_id: The database ID of the player
        
    Returns:
        dict: Player statistics or None if not found
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Join with players table to get player details too
        cursor.execute("""
        SELECT ps.*, p.name, p.role, p.team, p.batting_type, p.bowling_type, p.tier
        FROM player_stats ps 
        JOIN players p ON ps.player_id = p.id
        WHERE ps.player_id = ? AND ps.user_id = ?
        """, (player_id, user_id))
        
        stats = cursor.fetchone()
        if stats:
            return dict(stats)
        return None
    
    except Error as e:
        logger.error(f"Error getting player stats: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_user_player_stats(user_id, sort_by='batting_average', sort_order='desc', role_filter=None, limit=10, offset=0):
    """
    Get statistics for all players owned by a user, with optional sorting and filtering
    
    Args:
        user_id: The database ID of the user
        sort_by: Field to sort by (batting_average, bowling_average, etc.)
        sort_order: 'asc' or 'desc'
        role_filter: Filter by player role (batsman, bowler, etc.)
        limit: Maximum number of records to return
        offset: Starting offset for pagination
        
    Returns:
        list: List of player statistics dictionaries
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validate sort parameters
        valid_sort_fields = [
            'matches_played', 'runs_scored', 'balls_faced', 'batting_average', 
            'batting_strike_rate', 'wickets_taken', 'bowling_average', 
            'bowling_strike_rate', 'bowling_economy'
        ]
        
        if sort_by not in valid_sort_fields:
            sort_by = 'batting_average'
        
        if sort_order.lower() not in ['asc', 'desc']:
            sort_order = 'desc'
        
        # Build query
        query = """
        SELECT ps.*, p.name, p.role, p.team, p.batting_type, p.bowling_type, p.tier
        FROM player_stats ps 
        JOIN players p ON ps.player_id = p.id
        JOIN user_players up ON p.id = up.player_id
        WHERE ps.user_id = ? AND up.user_id = ?
        """
        
        params = [user_id, user_id]
        
        # Add role filter if specified
        if role_filter:
            query += " AND p.role LIKE ? "
            params.append(f"%{role_filter}%")
        
        # Add sorting
        query += f" ORDER BY ps.{sort_by} {sort_order}"
        
        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        stats = cursor.fetchall()
        return [dict(row) for row in stats]
    
    except Error as e:
        logger.error(f"Error getting user player stats: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_leaderboard(stat_type='batting', stat_field=None, limit=10):
    """
    Get a leaderboard of players based on specific statistics
    
    Args:
        stat_type: 'batting' or 'bowling'
        stat_field: Specific stat to rank by, overrides stat_type if provided
        limit: Maximum number of players to include
        
    Returns:
        list: List of player statistics dictionaries for the leaderboard
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determine which field to sort by
        if stat_field:
            sort_field = stat_field
        elif stat_type == 'batting':
            sort_field = 'batting_average'
        else:  # bowling
            sort_field = 'bowling_average'
        
        # For bowling average, we want ascending (lower is better)
        sort_order = 'ASC' if sort_field in ['bowling_average', 'bowling_economy'] else 'DESC'
        
        # Add a minimum threshold to filter out players with very few matches
        min_matches = 3
        
        # Add additional filters based on stat type
        additional_filter = ""
        if stat_type == 'batting':
            additional_filter = f"AND ps.innings_batted >= {min_matches}"
        elif stat_type == 'bowling':
            additional_filter = f"AND ps.innings_bowled >= {min_matches}"
        
        query = f"""
        SELECT ps.*, p.name, p.role, p.team, p.batting_type, p.bowling_type, p.tier,
               u.name as owner_name
        FROM player_stats ps 
        JOIN players p ON ps.player_id = p.id
        JOIN users u ON ps.user_id = u.id
        WHERE ps.matches_played >= ? {additional_filter}
        ORDER BY ps.{sort_field} {sort_order}
        LIMIT ?
        """
        
        cursor.execute(query, (min_matches, limit))
        
        stats = cursor.fetchall()
        return [dict(row) for row in stats]
    
    except Error as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []
    finally:
        if conn:
            conn.close()
