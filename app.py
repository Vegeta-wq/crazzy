#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flask web application for Cricket Game Bot admin panel
"""

import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from db import (
    get_all_users, find_user_by_username, get_user_coins, update_user_coins,
    list_all_players, get_player, delete_player, search_players, add_player,
    list_packs, get_pack, update_pack_status, delete_pack, health_check_db,
    is_admin
)
from health_checker import check_health
from utils import format_player_info, format_pack_info

# Set up logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Set admin IDs from environment variable
ADMIN_IDS = os.environ.get("ADMIN_IDS", "").split(",")
try:
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS if admin_id.strip()]
except ValueError:
    logger.error("Invalid ADMIN_IDS format. Please use comma-separated integers.")
    ADMIN_IDS = []

# Routes
@app.route('/')
def index():
    """Home page with basic status information"""
    # Check health status
    health_status = check_health()
    
    # Get basic stats
    stats = {
        "total_users": len(get_all_users()),
        "total_players": len(list_all_players()),
        "total_packs": len(list_packs(active_only=False)),
        "active_packs": len(list_packs(active_only=True))
    }
    
    return render_template('index.html', health=health_status, stats=stats)

@app.route('/users')
def users():
    """List all users"""
    users_list = get_all_users()
    return render_template('users.html', users=users_list)

@app.route('/users/search', methods=['GET', 'POST'])
def search_users():
    """Search for users by username"""
    if request.method == 'POST':
        search_term = request.form.get('search_term', '')
        users_list = find_user_by_username(search_term)
        return render_template('users.html', users=users_list, search_term=search_term)
    
    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/give_coins', methods=['GET', 'POST'])
def give_coins(user_id):
    """Give coins to a user"""
    if request.method == 'POST':
        amount = request.form.get('amount', '')
        try:
            amount = int(amount)
            if amount <= 0:
                flash('Amount must be a positive number', 'error')
            else:
                update_user_coins(user_id, amount)
                flash(f'Successfully gave {amount} coins to user', 'success')
                return redirect(url_for('users'))
        except ValueError:
            flash('Please enter a valid number', 'error')
    
    return render_template('give_coins.html', user_id=user_id, coins=get_user_coins(user_id))

@app.route('/players')
def players():
    """List all players"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    players_list = list_all_players(limit=per_page, offset=offset)
    total_players = len(list_all_players())
    total_pages = (total_players + per_page - 1) // per_page
    
    return render_template('players.html', 
                          players=players_list, 
                          page=page, 
                          total_pages=total_pages)

@app.route('/players/search', methods=['GET', 'POST'])
def search_player_route():
    """Search for players by name or team"""
    if request.method == 'POST':
        search_term = request.form.get('search_term', '')
        players_list = search_players(search_term)
        return render_template('players.html', players=players_list, search_term=search_term)
    
    return redirect(url_for('players'))

@app.route('/players/<int:player_id>')
def view_player(player_id):
    """View player details"""
    player = get_player(player_id)
    if player:
        player_info = format_player_info(player)
        return render_template('player_details.html', player=player, player_info=player_info)
    
    flash('Player not found', 'error')
    return redirect(url_for('players'))

@app.route('/players/<int:player_id>/delete', methods=['POST'])
def delete_player_route(player_id):
    """Delete a player"""
    result = delete_player(player_id)
    if result:
        flash('Player deleted successfully', 'success')
    else:
        flash('Failed to delete player', 'error')
    
    return redirect(url_for('players'))

@app.route('/packs')
def packs():
    """List all packs"""
    show_all = request.args.get('show_all', '0') == '1'
    packs_list = list_packs(active_only=not show_all)
    
    return render_template('packs.html', packs=packs_list, show_all=show_all)

@app.route('/packs/<int:pack_id>')
def view_pack(pack_id):
    """View pack details"""
    pack = get_pack(pack_id)
    if pack:
        pack_info = format_pack_info(pack)
        return render_template('pack_details.html', pack=pack, pack_info=pack_info)
    
    flash('Pack not found', 'error')
    return redirect(url_for('packs'))

@app.route('/packs/<int:pack_id>/toggle', methods=['POST'])
def toggle_pack(pack_id):
    """Toggle pack active status"""
    pack = get_pack(pack_id)
    if pack:
        new_status = not pack['is_active']
        update_pack_status(pack_id, new_status)
        status_text = 'activated' if new_status else 'deactivated'
        flash(f'Pack {status_text} successfully', 'success')
    else:
        flash('Pack not found', 'error')
    
    return redirect(url_for('packs'))

@app.route('/packs/<int:pack_id>/delete', methods=['POST'])
def delete_pack_route(pack_id):
    """Delete a pack"""
    result = delete_pack(pack_id)
    if result:
        flash('Pack deleted successfully', 'success')
    else:
        flash('Failed to delete pack', 'error')
    
    return redirect(url_for('packs'))

@app.route('/health')
def health():
    """Check health status"""
    health_status = check_health()
    return jsonify(health_status)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error_code=500, error_message='Server error'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)