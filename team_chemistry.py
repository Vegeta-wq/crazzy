"""
Team chemistry calculation for cricket matches
This module enhances the cricket match simulation by calculating
and applying team chemistry factors based on player roles and composition.
"""

def calculate_team_chemistry(team):
    """Calculate team chemistry based on role balance and complementary skills
    Returns a factor that affects match performance"""
    # Count roles in the team
    role_counts = {}
    for player in team.players:
        role = player.role
        if role not in role_counts:
            role_counts[role] = 0
        role_counts[role] += 1
    
    # Ideal balance: 1-2 WK, 4-5 BAT, 4-5 BOWL, 1-2 AR
    # Assess how close we are to ideal
    balance_factor = 1.0
    
    # Check Wicket Keepers (ideal: 1-2)
    wk_count = role_counts.get("WK", 0)
    if wk_count == 0:
        balance_factor -= 0.1  # Penalty for no wicket keeper
    elif wk_count > 2:
        balance_factor -= 0.05 * (wk_count - 2)  # Penalty for too many
        
    # Check Batsmen (ideal: 4-5)
    bat_count = role_counts.get("BAT", 0)
    if bat_count < 4:
        balance_factor -= 0.05 * (4 - bat_count)
    elif bat_count > 5:
        balance_factor -= 0.03 * (bat_count - 5)
        
    # Check Bowlers (ideal: 4-5)
    bowl_count = role_counts.get("BOWL", 0)
    if bowl_count < 4:
        balance_factor -= 0.05 * (4 - bowl_count)
    elif bowl_count > 5:
        balance_factor -= 0.03 * (bowl_count - 5)
        
    # Check All-rounders (ideal: 1-2)
    ar_count = role_counts.get("AR", 0)
    if ar_count == 0:
        balance_factor -= 0.05  # Small penalty for no all-rounders
    elif ar_count > 2:
        balance_factor -= 0.02 * (ar_count - 2)
        
    # Balance between batting and bowling
    if abs((bat_count + ar_count) - (bowl_count + ar_count)) > 2:
        balance_factor -= 0.05  # Penalty for imbalance
        
    # Ensure factor is within reasonable range
    balance_factor = max(0.8, min(1.2, balance_factor))
    
    return balance_factor

def create_chemistry_commentary(team1_name, team1_chemistry, team2_name, team2_chemistry):
    """Generate commentary on team chemistry"""
    chemistry_info = f"\n\n🏏 Team Chemistry Analysis 🏏\n"
    chemistry_info += f"{team1_name}: {'Excellent' if team1_chemistry > 1.1 else 'Good' if team1_chemistry > 1.0 else 'Poor'} team balance (Factor: {team1_chemistry:.2f})\n"
    chemistry_info += f"{team2_name}: {'Excellent' if team2_chemistry > 1.1 else 'Good' if team2_chemistry > 1.0 else 'Poor'} team balance (Factor: {team2_chemistry:.2f})\n"
    return chemistry_info