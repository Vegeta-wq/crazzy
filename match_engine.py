#!/usr/bin/env python3
"""
Cricket match simulation engine
"""
from typing import List, Dict, Optional, Any, Callable, Tuple
import random
import logging
import time
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Player:
    """Player class representing a cricket player with attributes and stats"""
    
    def __init__(
        self,
        id: int,
        name: str,
        role: str,
        team: str,
        batting_type: str,
        bowling_type: str,
        batting_ovr: int = 0,
        bowling_ovr: int = 0,
        total_ovr: int = 0,
        position: int = 0,
        tier: str = "Bronze",
        batting_timing: int = 50,
        batting_technique: int = 50,
        batting_power: int = 50,
        bowling_pace: int = 50,
        bowling_variation: int = 50,
        bowling_accuracy: int = 50
    ):
        self.id = id
        self.name = name
        self.role = role
        self.team = team
        self.batting_type = batting_type
        self.bowling_type = bowling_type
        self.position = position
        self.tier = tier
        
        # Core attributes
        self.batting_ovr = batting_ovr
        self.bowling_ovr = bowling_ovr
        self.total_ovr = total_ovr
        
        # Detailed attributes
        self.batting_timing = batting_timing if batting_timing is not None else random.randint(30, 70)
        self.batting_technique = batting_technique if batting_technique is not None else random.randint(30, 70)
        self.batting_power = batting_power if batting_power is not None else random.randint(30, 70)
        self.bowling_pace = bowling_pace if bowling_pace is not None else random.randint(30, 70)
        self.bowling_variation = bowling_variation if bowling_variation is not None else random.randint(30, 70)
        self.bowling_accuracy = bowling_accuracy if bowling_accuracy is not None else random.randint(30, 70)
        
        # Match stats
        self.reset_match_stats()
    
    def reset_match_stats(self):
        """Reset match statistics for the player"""
        self.runs = 0
        self.balls_faced = 0
        self.wickets = 0
        self.balls_bowled = 0
        self.runs_conceded = 0
        self.is_out = False
        self.out_method: Optional[str] = None
        self.bowler_who_dismissed: Optional[str] = None
        self.fielder_who_dismissed: Optional[str] = None
        self.fours = 0
        self.sixes = 0
        self.overs_bowled = 0
        self.maidens = 0
        self.strike_rate = 0.0  # Added strike rate initialization
        
    def add_runs(self, runs: int):
        """Add runs to player's match stats"""
        self.runs += runs
        # Don't increment balls_faced here as it's already done in add_ball()
        
        # Track boundaries
        if runs == 4:
            self.fours += 1
        elif runs == 6:
            self.sixes += 1
            
        # Update strike rate
        self.strike_rate = round((self.runs / self.balls_faced * 100), 2) if self.balls_faced > 0 else 0.0
        
    def add_ball(self):
        """Add a ball faced to player's match stats"""
        self.balls_faced += 1
        # Calculate strike rate here
        self.strike_rate = round((self.runs / self.balls_faced * 100), 2) if self.balls_faced > 0 else 0.0

class Team:
    """Team class representing a cricket team with players and stats"""
    
    def __init__(self, id: int, name: str, owner_id: int, players: Optional[List[Player]] = None, 
                 description: Optional[str] = None, strategy: Optional[Dict] = None):
        """Initialize a team with basic attributes and players"""
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.description = description if description else f"{name} team"
        self.players = players if players else []
        
        # Match statistics
        self.score = 0
        self.wickets = 0
        self.overs = 0
        self.balls = 0
        
        # Team chemistry factors
        self.chemistry = 1.0
        
        # Team strategy factors (default to balanced)
        self.strategy = strategy or {
            "name": "Balanced",
            "batting_aggression": 1.0,
            "bowling_aggression": 1.0,
            "batting_focus": "balanced",
            "bowling_focus": "balanced", 
            "field_placement": "standard"
        }
        
    def get_batting_order(self) -> List[Player]:
        """Get batting order for the team based on position set in team"""
        # Primarily use position if available, then fall back to roles and stats
        ordered_players = sorted(
            self.players, 
            key=lambda p: (
                p.position if p.position is not None and p.position > 0 else 999,
                0 if p.role.lower() == "batsman" else (1 if p.role.lower() == "all-rounder" else 2),
                -p.batting_ovr
            )
        )
        return ordered_players
    
    def get_bowling_order(self) -> List[Player]:
        """Get bowling order for the team based on role and stats"""
        # Simple implementation - bowlers first, then all-rounders
        ordered_players = sorted(
            [p for p in self.players if p.role.lower() in ["bowler", "all-rounder", "all rounder"]], 
            key=lambda p: -p.bowling_ovr
        )
        return ordered_players
        
    def calculate_chemistry(self) -> float:
        """Calculate team chemistry based on players"""
        if not self.players or len(self.players) < 5:
            chemistry = 0.50  # Minimum chemistry for invalid teams
            self.chemistry = chemistry
            return chemistry
            
        # Count the roles and calculate balance
        role_counts = {
            "batsman": 0,
            "bowler": 0,
            "all-rounder": 0,
            "wicket keeper": 0
        }
        
        for player in self.players:
            role = player.role.lower().strip()
            if role in ["batsman", "batter"]:
                role_counts["batsman"] += 1
            elif role in ["bowler"]:
                role_counts["bowler"] += 1
            elif role in ["all-rounder", "all rounder", "allrounder"]:
                role_counts["all-rounder"] += 1
            elif role in ["wicket keeper", "wicketkeeper", "keeper"]:
                role_counts["wicket keeper"] += 1
                
        # Calculate chemistry based on team balance
        # Ideal balance: 4-5 batsmen, 4-5 bowlers, 1-2 all-rounders, 1 wicket keeper
        chemistry = 1.0
        
        # Penalty for too few or too many batsmen
        if role_counts["batsman"] < 3:
            chemistry -= 0.20  # Too few batsmen
        elif role_counts["batsman"] > 6:
            chemistry -= 0.15 * (role_counts["batsman"] - 6)  # Too many batsmen
            
        # Penalty for too few or too many bowlers
        if role_counts["bowler"] < 3:
            chemistry -= 0.20  # Too few bowlers
        elif role_counts["bowler"] > 6:
            chemistry -= 0.15 * (role_counts["bowler"] - 6)  # Too many bowlers
            
        # Penalty for no wicket keeper - serious disadvantage
        if role_counts["wicket keeper"] < 1:
            chemistry -= 0.30  # No wicket keeper - major penalty
        elif role_counts["wicket keeper"] > 2:
            chemistry -= 0.10 * (role_counts["wicket keeper"] - 2)  # Too many wicket keepers
            
        # All-rounders provide flexibility, modest penalty for none
        if role_counts["all-rounder"] < 1:
            chemistry -= 0.15  # No all-rounders
        elif role_counts["all-rounder"] > 3:
            chemistry -= 0.10 * (role_counts["all-rounder"] - 3)  # Too many all-rounders
            
        # Team size penalty - cricket teams should have 11 players
        total_players = sum(role_counts.values())
        if total_players != 11:
            chemistry -= 0.10 * abs(11 - total_players)
            
        # Bonus for perfect balance (4-5 batsmen, 4-5 bowlers, 1-2 all-rounders, 1 wicket keeper, 11 players)
        if (4 <= role_counts["batsman"] <= 5 and
            4 <= role_counts["bowler"] <= 5 and
            1 <= role_counts["all-rounder"] <= 2 and
            role_counts["wicket keeper"] == 1 and
            total_players == 11):
            chemistry += 0.10  # Perfect balance bonus
            
        # Ensure chemistry stays in valid range (0.5 to 1.5)
        chemistry = max(0.5, min(chemistry, 1.5))
        
        self.chemistry = chemistry  # Save to team instance
        return chemistry

class CricketMatch:
    """Cricket match simulation engine"""
    
    def __init__(
        self,
        team1: Team,
        team2: Team,
        total_overs: int = 20,
        chat_id: Optional[int] = None,
        send_message_func: Optional[Callable[[Dict], None]] = None,
        update_scorecard_func: Optional[Callable[[Dict], None]] = None,
        match_end_func: Optional[Callable[[Dict], None]] = None,
        match_type: str = "friendly",
        match_id: Optional[str] = None
    ):
        self.team1 = team1
        self.team2 = team2
        self.total_overs = total_overs
        self.chat_id = chat_id
        
        # Match properties
        self.match_type = match_type
        self.match_id = match_id
        
        # Callback functions for UI updates
        self.send_message_func = send_message_func
        self.update_scorecard_func = update_scorecard_func
        self.match_end_func = match_end_func
        
        # Initialize match state
        self.reset_match_stats()
        
    def reset_match_stats(self):
        """Reset match statistics"""
        # Reset team stats
        self.team1.score = 0
        self.team1.wickets = 0
        self.team1.overs = 0
        self.team1.balls = 0
        
        self.team2.score = 0
        self.team2.wickets = 0
        self.team2.overs = 0
        self.team2.balls = 0
        
        # Reset player stats
        for player in self.team1.players + self.team2.players:
            player.reset_match_stats()
            
        # Match state
        self.current_innings = 0
        self.team1_score = 0
        self.team1_wickets = 0
        self.team1_overs = 0
        self.team1_balls = 0
        
        self.team2_score = 0
        self.team2_wickets = 0
        self.team2_overs = 0
        self.team2_balls = 0
        
        self.current_batsmen = []
        self.current_bowler = None
        self.target_score = None
        self.over_start_runs = 0  # Track runs at start of over for maiden detection
        self.batting_team = None
        self.bowling_team = None
        
        # Track partnerships and fall of wickets
        self.current_partnership = 0
        self.partnership_balls = 0
        self.fall_of_wickets = []  # List of dictionaries with score, over, player_out, bowler
        
    def set_callbacks(
        self,
        send_message_func: Optional[Callable[[Dict], None]] = None,
        update_scorecard_func: Optional[Callable[[Dict], None]] = None,
        match_end_func: Optional[Callable[[Dict], None]] = None
    ):
        """Set callback functions for UI updates"""
        self.send_message_func = send_message_func
        self.update_scorecard_func = update_scorecard_func
        self.match_end_func = match_end_func
    
    def setup_innings(self, batting_team: Team, bowling_team: Team, innings_number: int):
        """Setup an innings with batting and bowling teams"""
        self.current_innings = innings_number
        
        # Set batting and bowling teams
        self.batting_team = batting_team
        self.bowling_team = bowling_team
        
        # Set current batsmen (first two in the batting order)
        batting_order = batting_team.get_batting_order()
        if len(batting_order) >= 2:
            self.current_batsmen = batting_order[:2]
        else:
            self.current_batsmen = batting_order
            
        # Set current bowler (first in the bowling order)
        bowling_order = bowling_team.get_bowling_order()
        if bowling_order:
            self.current_bowler = bowling_order[0]
        else:
            self.current_bowler = None
            
    def get_current_over(self) -> int:
        """Get the current over number (0-indexed)
        
        Returns:
            int: Current over number
        """
        if self.batting_team is not None:
            return self.batting_team.overs if hasattr(self.batting_team, 'overs') else 0
        else:
            return 0
            
    def get_match_phase(self, over_number: int) -> str:
        """Determine the match phase based on the current over
        
        Args:
            over_number: Current over number (0-indexed)
            
        Returns:
            str: 'powerplay', 'middle_overs', or 'death_overs'
        """
        # Implement T20-style phases
        if over_number < 6:
            return 'powerplay'
        elif over_number >= (self.total_overs - 4):
            return 'death_overs'
        else:
            return 'middle_overs'
    
    def simulate_ball(self) -> Dict:
        """Simulate a single ball in the match with realistic outcomes"""
        # Check if we have valid batsmen and bowler
        if not self.current_batsmen or not self.current_bowler:
            return {"event": "error", "message": "No batsmen or bowler available"}
            
        # Get current batsman and bowler
        batsman = self.current_batsmen[0] if self.current_batsmen else None
        bowler = self.current_bowler
        
        if not batsman or not bowler:
            return {"event": "error", "message": "Invalid batsman or bowler"}
        
        # Calculate outcome probabilities based on player attributes
        batting_skill = (batsman.batting_timing + batsman.batting_technique + batsman.batting_power) / 3
        bowling_skill = (bowler.bowling_pace + bowler.bowling_variation + bowler.bowling_accuracy) / 3
        
        # Apply team chemistry factors
        # Make sure teams have chemistry calculated
        batting_team_chemistry = 1.0
        bowling_team_chemistry = 1.0
        
        if self.batting_team is not None and hasattr(self.batting_team, 'chemistry'):
            batting_team_chemistry = self.batting_team.chemistry
        
        if self.bowling_team is not None and hasattr(self.bowling_team, 'chemistry'):
            bowling_team_chemistry = self.bowling_team.chemistry
            
        # Determine the match phase based on current over
        current_over = self.get_current_over()
        match_phase = self.get_match_phase(current_over)
        
        # Add batsman confidence and fatigue factors
        # Confidence increases with runs scored, fatigue increases with balls faced
        batsman_confidence = min(1.5, 1.0 + (batsman.runs / max(1, batsman.balls_faced)) * 0.1)
        batsman_fatigue = max(0.7, 1.0 - (batsman.balls_faced * 0.005))  # Decreases as balls faced increases
        
        # Add bowler fatigue based on consecutive overs bowled
        bowler_consecutive_overs = getattr(bowler, 'consecutive_overs', 0)
        bowler_fatigue = max(0.8, 1.0 - (bowler_consecutive_overs * 0.05))
        
        # Apply team strategy factors
        batting_aggression = 1.0
        bowling_aggression = 1.0
        
        if self.batting_team is not None and hasattr(self.batting_team, 'strategy'):
            batting_aggression = self.batting_team.strategy.get('batting_aggression', 1.0)
        
        if self.bowling_team is not None and hasattr(self.bowling_team, 'strategy'):
            bowling_aggression = self.bowling_team.strategy.get('bowling_aggression', 1.0)
        
        # Apply chemistry, confidence, fatigue and strategy effects to skills
        batting_skill *= batting_team_chemistry * batting_aggression * batsman_confidence * batsman_fatigue
        bowling_skill *= bowling_team_chemistry * bowling_aggression * bowler_fatigue
        
        # Batting skill has positive impact on runs, bowling skill reduces it
        # Skill difference affects outcome probabilities
        skill_diff = batting_skill - bowling_skill
        
        # Get team strategy effects
        batting_focus = "balanced"
        bowling_focus = "balanced"
        
        if self.batting_team is not None and hasattr(self.batting_team, 'strategy'):
            batting_focus = self.batting_team.strategy.get('batting_focus', 'balanced')
        
        if self.bowling_team is not None and hasattr(self.bowling_team, 'strategy'):
            bowling_focus = self.bowling_team.strategy.get('bowling_focus', 'balanced')
        
        # Base probabilities (will be adjusted by skill difference, strategy, and match phase)
        dot_prob = 0.40 - (skill_diff * 0.003)  # Lower dot probability as batting skill increases
        runs_1_prob = 0.25  # Singles are most common
        runs_2_prob = 0.12  # Doubles less common than singles
        runs_3_prob = 0.03  # Triples are rare
        runs_1_3_prob = runs_1_prob + runs_2_prob + runs_3_prob  # Combine for compatibility with existing code
        boundary_4_prob = 0.10 + (skill_diff * 0.002)  # Higher boundary probability as batting skill increases
        boundary_6_prob = 0.05 + (skill_diff * 0.002)  # Higher six probability as batting skill increases
        wicket_prob = 0.05 - (skill_diff * 0.001)  # Lower wicket probability as batting skill increases
        
        # Apply match phase adjustments
        if match_phase == 'powerplay':
            # More boundaries in powerplay due to field restrictions
            dot_prob -= 0.05
            boundary_4_prob += 0.08
            boundary_6_prob += 0.02
            # Wickets also more likely in powerplay as batsmen take risks
            wicket_prob += 0.01
        elif match_phase == 'middle_overs':
            # More singles and doubles, fewer boundaries
            runs_1_prob += 0.05
            runs_2_prob += 0.02
            boundary_4_prob -= 0.03
            boundary_6_prob -= 0.02
            runs_1_3_prob = runs_1_prob + runs_2_prob + runs_3_prob  # Recalculate after changes
        elif match_phase == 'death_overs':
            # More boundaries and wickets in death overs
            dot_prob -= 0.10
            runs_1_prob -= 0.05
            boundary_4_prob += 0.05
            boundary_6_prob += 0.08
            wicket_prob += 0.02
            runs_1_3_prob = runs_1_prob + runs_2_prob + runs_3_prob  # Recalculate after changes
        
        # Apply strategy focus adjustments
        if batting_focus == "attacking":
            # More likely to go for boundaries, less likely to block
            dot_prob -= 0.10
            runs_1_3_prob -= 0.05
            boundary_4_prob += 0.08
            boundary_6_prob += 0.07
            # Higher risk of wickets
            wicket_prob += 0.03
        elif batting_focus == "defensive":
            # More likely to block, less likely to go for boundaries
            dot_prob += 0.10
            runs_1_3_prob += 0.05
            boundary_4_prob -= 0.05
            boundary_6_prob -= 0.05
            # Lower risk of wickets
            wicket_prob -= 0.02
            
        if bowling_focus == "wicket-taking":
            # More likely to get wickets, but also more boundaries
            wicket_prob += 0.05
            dot_prob -= 0.03
            boundary_4_prob += 0.02
            boundary_6_prob += 0.01
        elif bowling_focus == "economy":
            # Less likely to concede boundaries, but also fewer wickets
            wicket_prob -= 0.02
            dot_prob += 0.08
            boundary_4_prob -= 0.04
            boundary_6_prob -= 0.02
        
        # Ensure probabilities are in valid ranges (0-1)
        dot_prob = max(0.20, min(0.60, dot_prob))
        runs_1_3_prob = max(0.25, min(0.50, runs_1_3_prob))
        boundary_4_prob = max(0.05, min(0.20, boundary_4_prob)) 
        boundary_6_prob = max(0.01, min(0.15, boundary_6_prob))
        wicket_prob = max(0.02, min(0.15, wicket_prob))
        
        # Normalize probabilities to ensure they sum to 1.0
        total_prob = dot_prob + runs_1_3_prob + boundary_4_prob + boundary_6_prob + wicket_prob
        dot_prob /= total_prob
        runs_1_3_prob /= total_prob
        boundary_4_prob /= total_prob
        boundary_6_prob /= total_prob
        wicket_prob /= total_prob
        
        # Cumulative probabilities for easier random selection
        cum_prob_dot = dot_prob
        cum_prob_1_3 = cum_prob_dot + runs_1_3_prob
        cum_prob_4 = cum_prob_1_3 + boundary_4_prob
        cum_prob_6 = cum_prob_4 + boundary_6_prob
        
        # Generate random outcome
        outcome_roll = random.random()
        
        # Always increment balls faced for every delivery
        batsman.add_ball()
        
        # Process the outcome
        if outcome_roll < cum_prob_dot:
            # Dot ball (0 runs)
            return {
                "event": "dot",
                "batsman": batsman.name,
                "bowler": bowler.name,
                "commentary": self.generate_dot_ball_commentary(batsman.name, bowler.name)
            }
        elif outcome_roll < cum_prob_1_3:
            # 1-3 runs with weighted probabilities (singles most common, triples rare)
            # Calculate relative proportions of each run type
            total_runs_prob = runs_1_prob + runs_2_prob + runs_3_prob
            run_1_weight = runs_1_prob / total_runs_prob if total_runs_prob > 0 else 0.7
            run_2_weight = runs_2_prob / total_runs_prob if total_runs_prob > 0 else 0.25
            run_3_weight = runs_3_prob / total_runs_prob if total_runs_prob > 0 else 0.05
            
            # Use weighted choice
            runs = random.choices([1, 2, 3], weights=[run_1_weight, run_2_weight, run_3_weight])[0]
            batsman.add_runs(runs)
            
            return {
                "event": "runs",
                "runs": runs,
                "batsman": batsman.name,
                "bowler": bowler.name,
                "commentary": self.generate_runs_commentary(batsman.name, runs)
            }
        elif outcome_roll < cum_prob_4:
            # Boundary (4 runs)
            batsman.add_runs(4)
            
            return {
                "event": "boundary_4",
                "runs": 4,
                "batsman": batsman.name,
                "bowler": bowler.name,
                "commentary": self.generate_boundary_commentary(batsman.name, 4)
            }
        elif outcome_roll < cum_prob_6:
            # Six (6 runs)
            batsman.add_runs(6)
            
            return {
                "event": "boundary_6",
                "runs": 6,
                "batsman": batsman.name,
                "bowler": bowler.name,
                "commentary": self.generate_boundary_commentary(batsman.name, 6)
            }
        else:
            # Wicket
            # Determine dismissal type based on bowler's skills
            dismissal_types = ["bowled", "caught", "lbw", "stumped", "caught_behind"]
            
            # Bowlers with good accuracy more likely to get bowled/lbw
            # Bowlers with good variation more likely to get caught
            if bowler.bowling_accuracy > 70:
                dismissal_weights = [0.4, 0.2, 0.3, 0.05, 0.05]
            elif bowler.bowling_variation > 70:
                dismissal_weights = [0.2, 0.4, 0.1, 0.15, 0.15]
            else:
                dismissal_weights = [0.3, 0.3, 0.2, 0.1, 0.1]
                
            dismissal_type = random.choices(dismissal_types, weights=dismissal_weights)[0]
            
            # Mark batsman as out
            batsman.is_out = True
            
            # Set dismissal information
            batsman.out_method = dismissal_type
            batsman.bowler_who_dismissed = bowler.name
            
            # Generate fielder name for catches
            fielder_name = None
            if dismissal_type in ["caught", "caught_behind", "stumped"] and self.bowling_team is not None:
                # Use a random other player from bowling team as fielder
                fielders = []
                if hasattr(self.bowling_team, 'players') and self.bowling_team.players:
                    fielders = [p for p in self.bowling_team.players if p.id != bowler.id]
                
                if fielders:
                    fielder = random.choice(fielders)
                    fielder_name = fielder.name
                    # Set the fielder who dismissed the batsman
                    batsman.fielder_who_dismissed = fielder_name
            
            return {
                "event": "wicket",
                "batsman_out": batsman.name,
                "bowler": bowler.name,
                "fielder": fielder_name,
                "dismissal_type": dismissal_type,
                "commentary": self.generate_wicket_commentary(batsman.name, bowler.name, dismissal_type, fielder_name)
            }
            
    def generate_dot_ball_commentary(self, batsman: str, bowler: str) -> str:
        """Generate commentary for a dot ball"""
        commentaries = [
            f"{batsman} defends solidly.",
            f"{batsman} watches the ball carefully and lets it go.",
            f"Good line from {bowler}, no run.",
            f"{batsman} plays and misses! That was close!",
            f"Appeal for LBW but the umpire shakes his head. No run.",
            f"{batsman} blocks it back to {bowler}.",
            f"Dot ball as {batsman} can't find a gap in the field.",
            f"Good fielding prevents any run scoring there.",
            f"{batsman} was looking for a single but decides against it.",
            f"That's beaten the bat! No run."
        ]
        return random.choice(commentaries)
        
    def generate_runs_commentary(self, batsman: str, runs: int) -> str:
        """Generate commentary for runs scored"""
        if runs == 1:
            commentaries = [
                f"{batsman} takes a quick single.",
                f"Just a single as {batsman} works it to the leg side.",
                f"One run added to the total.",
                f"{batsman} pushes it into the gap for a single.",
                f"Quick running between the wickets for a single."
            ]
        elif runs == 2:
            commentaries = [
                f"{batsman} finds the gap and takes two runs.",
                f"Good running between the wickets as they complete two.",
                f"{batsman} plays it fine and they run two.",
                f"Two runs added as {batsman} places it well.",
                f"{batsman} drives it through the covers for a couple."
            ]
        else:  # 3 runs
            commentaries = [
                f"Three runs as {batsman} hits it into the deep.",
                f"They're running hard and they'll take three!",
                f"{batsman} times it well and they complete three runs.",
                f"Good placement from {batsman} and that's three runs.",
                f"The fielder just stops it inside the boundary, three taken."
            ]
        return random.choice(commentaries)
        
    def generate_boundary_commentary(self, batsman: str, runs: int) -> str:
        """Generate commentary for boundary (4 or 6)"""
        if runs == 4:
            commentaries = [
                f"FOUR! {batsman} finds the boundary with a beautiful shot.",
                f"That's a cracking shot from {batsman}! FOUR runs!",
                f"Elegant drive from {batsman} and that races away for FOUR!",
                f"FOUR! {batsman} times that to perfection.",
                f"The fielder has no chance as {batsman} hits that for FOUR!"
            ]
        else:  # 6 runs
            commentaries = [
                f"SIX! {batsman} has hit that out of the park!",
                f"What a shot! {batsman} launches that for a massive SIX!",
                f"SIX! That's a huge hit from {batsman}!",
                f"{batsman} makes it look effortless as that sails for SIX!",
                f"That's disappeared into the crowd! SIX runs for {batsman}!"
            ]
        return random.choice(commentaries)
        
    def generate_wicket_commentary(self, batsman: str, bowler: str, dismissal_type: str, fielder: Optional[str] = None) -> str:
        """Generate commentary for wicket event"""
        if dismissal_type == "bowled":
            commentaries = [
                f"BOWLED! {batsman} is clean bowled by {bowler}!",
                f"The stumps are shattered! {batsman} is bowled by {bowler}!",
                f"What a delivery from {bowler}! {batsman} is bowled!",
                f"{batsman} misses and the ball crashes into the stumps!",
                f"That's BOWLED! Great ball from {bowler}!"
            ]
        elif dismissal_type == "caught" and fielder:
            commentaries = [
                f"CAUGHT! {batsman} hits it in the air and {fielder} takes the catch!",
                f"{batsman} mistimes it and {fielder} makes no mistake with the catch!",
                f"What a catch by {fielder}! {batsman} has to go!",
                f"{fielder} takes a good catch to dismiss {batsman}!",
                f"CAUGHT! {batsman} is out, caught by {fielder} off the bowling of {bowler}!"
            ]
        elif dismissal_type == "caught" and not fielder:
            commentaries = [
                f"CAUGHT! {batsman} hits it in the air and is caught in the field!",
                f"{batsman} mistimes it and is caught!",
                f"What a catch in the field! {batsman} has to go!",
                f"A good catch to dismiss {batsman}!",
                f"CAUGHT! {batsman} is out, caught off the bowling of {bowler}!"
            ]
        elif dismissal_type == "lbw":
            commentaries = [
                f"LBW! {batsman} is trapped in front by {bowler}!",
                f"The umpire raises the finger! {batsman} is out LBW!",
                f"That looked plumb! {batsman} is given out LBW to {bowler}!",
                f"Appeal for LBW and the umpire agrees! {batsman} has to go!",
                f"BIG appeal and {batsman} is given out LBW!"
            ]
        elif dismissal_type == "stumped" and fielder:
            commentaries = [
                f"STUMPED! {batsman} is out of his crease and {fielder} whips off the bails!",
                f"Quick work by {fielder} and {batsman} is stumped!",
                f"{batsman} loses his balance and {fielder} stumps him!",
                f"Lightning fast hands from {fielder} to stump {batsman}!",
                f"STUMPED! {batsman} is caught short of his ground!"
            ]
        elif dismissal_type == "stumped" and not fielder:
            commentaries = [
                f"STUMPED! {batsman} is out of his crease and the keeper whips off the bails!",
                f"Quick work by the wicket keeper and {batsman} is stumped!",
                f"{batsman} loses his balance and is stumped!",
                f"Lightning fast hands from the keeper to stump {batsman}!",
                f"STUMPED! {batsman} is caught short of his ground!"
            ]
        elif dismissal_type == "caught_behind" and fielder:
            commentaries = [
                f"CAUGHT BEHIND! {batsman} edges it and {fielder} takes a good catch!",
                f"There's a thin edge and {fielder} takes the catch behind the stumps!",
                f"{batsman} nicks it and {fielder} makes no mistake!",
                f"The keeper {fielder} takes a brilliant catch to dismiss {batsman}!",
                f"CAUGHT BEHIND! {batsman} is out, caught by {fielder} off {bowler}!"
            ]
        elif dismissal_type == "caught_behind" and not fielder:
            commentaries = [
                f"CAUGHT BEHIND! {batsman} edges it and the keeper takes a good catch!",
                f"There's a thin edge and the catch is taken behind the stumps!",
                f"{batsman} nicks it and the keeper makes no mistake!",
                f"The keeper takes a brilliant catch to dismiss {batsman}!",
                f"CAUGHT BEHIND! {batsman} is out off {bowler}!"
            ]
        else:
            # Generic wicket commentary
            commentaries = [
                f"WICKET! {batsman} is out!",
                f"{batsman} has to go! Great bowling from {bowler}!",
                f"That's the end of {batsman}'s innings!",
                f"WICKET! {bowler} gets the crucial breakthrough!",
                f"{batsman} is dismissed! The bowling team celebrates!"
            ]
        return random.choice(commentaries)
        
    def determine_winner(self) -> Optional[Team]:
        """Determine which team won the match"""
        if self.team1_score > self.team2_score:
            return self.team1
        elif self.team2_score > self.team1_score:
            return self.team2
        else:
            # It's a tie
            return None
    
    def get_match_result(self) -> Tuple[str, Dict]:
        """Get the result of the match"""
        if self.team1_score > self.team2_score:
            result_type = "team1_win"
            margin = self.team1_score - self.team2_score
            result = {
                "winner": self.team1.name,
                "winner_id": self.team1.id,
                "winner_owner_id": self.team1.owner_id,
                "margin_type": "runs",
                "margin": margin,
                "team1_score": self.team1_score,
                "team1_wickets": self.team1_wickets,
                "team1_overs": f"{self.team1_overs}.{self.team1_balls % 6}",
                "team2_score": self.team2_score,
                "team2_wickets": self.team2_wickets,
                "team2_overs": f"{self.team2_overs}.{self.team2_balls % 6}",
                "match_type": self.match_type,
                "match_id": self.match_id
            }
        elif self.team2_score > self.team1_score:
            result_type = "team2_win_wickets"
            margin = 10 - self.team2_wickets
            result = {
                "winner": self.team2.name,
                "winner_id": self.team2.id,
                "winner_owner_id": self.team2.owner_id,
                "margin_type": "wickets",
                "margin": margin,
                "team1_score": self.team1_score,
                "team1_wickets": self.team1_wickets,
                "team1_overs": f"{self.team1_overs}.{self.team1_balls % 6}",
                "team2_score": self.team2_score,
                "team2_wickets": self.team2_wickets,
                "team2_overs": f"{self.team2_overs}.{self.team2_balls % 6}",
                "match_type": self.match_type,
                "match_id": self.match_id
            }
        else:
            result_type = "tie"
            result = {
                "winner": "Tie",
                "winner_id": None,
                "winner_owner_id": None,
                "margin_type": "tie",
                "margin": 0,
                "team1_score": self.team1_score,
                "team1_wickets": self.team1_wickets,
                "team1_overs": f"{self.team1_overs}.{self.team1_balls % 6}",
                "team2_score": self.team2_score,
                "team2_wickets": self.team2_wickets,
                "team2_overs": f"{self.team2_overs}.{self.team2_balls % 6}",
                "match_type": self.match_type,
                "match_id": self.match_id
            }
            
        return result_type, result
            
    def complete_match(self) -> Dict:
        """Complete the match and return the result"""
        result_type, result_dict = self.get_match_result()
        
        # For the test, we need to add a result_type field to the dict
        result_dict["result_type"] = result_type
        
        # Add coin rewards based on match outcome
        import random
        
        # Define reward ranges
        winner_coins = random.randint(1000, 1500)
        loser_coins = random.randint(500, 600)
        tie_coins = random.randint(700, 1000)
        
        if result_type == "team1_win":
            result_dict["team1_reward"] = winner_coins
            result_dict["team2_reward"] = loser_coins
        elif result_type in ["team2_win_wickets", "team2_win_runs"]:
            result_dict["team1_reward"] = loser_coins
            result_dict["team2_reward"] = winner_coins
        else:  # tie
            result_dict["team1_reward"] = tie_coins
            result_dict["team2_reward"] = tie_coins
        
        # If callbacks are set, call them
        if self.match_end_func:
            self.match_end_func(result_dict)
            
        return result_dict
        
    def simulate_match(self, delay_between_balls: int = 2, return_results: bool = False) -> Optional[Dict]:
        """Simulate a full cricket match with realistic ball-by-ball play
        
        Args:
            delay_between_balls: Time delay between balls in seconds (for live commentary)
            return_results: If True, just returns match results without simulation
            
        Returns:
            Optional Dict with match results if return_results is True
        """
        if return_results:
            return self.complete_match()
            
        # Reset match stats
        self.reset_match_stats()
        
        # First innings - Team 1 batting, Team 2 bowling
        self.setup_innings(self.team1, self.team2, 1)
        
        # Send match start message
        if self.send_message_func:
            self.send_message_func({
                "event": "match_start",
                "team1": self.team1.name,
                "team2": self.team2.name,
                "overs": self.total_overs,
                "commentary": f"Welcome to the match between {self.team1.name} and {self.team2.name}! " +
                             f"{self.team1.name} will bat first."
            })
        
        # Simulate first innings
        self._simulate_innings(delay_between_balls)
        
        # Save team 1 score - add safety check
        self.team1_score = self.batting_team.score if self.batting_team else 0
        self.team1_wickets = self.batting_team.wickets if self.batting_team else 0
        self.team1_overs = self.batting_team.overs if self.batting_team else 0
        self.team1_balls = self.batting_team.balls if self.batting_team else 0
        
        # Send innings break message
        if self.send_message_func:
            self.send_message_func({
                "event": "innings_break",
                "team": self.team1.name,
                "score": self.team1_score,
                "wickets": self.team1_wickets,
                "overs": f"{self.team1_overs}.{self.team1_balls % 6}",
                "commentary": f"End of {self.team1.name}'s innings! They scored {self.team1_score}/{self.team1_wickets} " +
                             f"in {self.team1_overs}.{self.team1_balls % 6} overs."
            })
            
        # Second innings - Team 2 batting, Team 1 bowling
        self.setup_innings(self.team2, self.team1, 2)
        
        # Target for the second innings
        target = self.team1_score + 1
        self.target_score = target
        
        # Send second innings message
        if self.send_message_func:
            self.send_message_func({
                "event": "innings_start",
                "team": self.team2.name,
                "target": target,
                "commentary": f"{self.team2.name} needs {target} runs from {self.total_overs} overs to win."
            })
        
        # Simulate second innings with target
        self._simulate_innings(delay_between_balls, target)
        
        # Save team 2 score - add safety check
        self.team2_score = self.batting_team.score if self.batting_team else 0
        self.team2_wickets = self.batting_team.wickets if self.batting_team else 0
        self.team2_overs = self.batting_team.overs if self.batting_team else 0
        self.team2_balls = self.batting_team.balls if self.batting_team else 0
        
        # Get match result
        result_type, result_dict = self.get_match_result()
        
        # Send match end message
        if self.match_end_func:
            result_dict["result_type"] = result_type
            self.match_end_func(result_dict)
            
        return result_dict
        
    def _simulate_innings(self, delay_between_balls: int = 2, target: Optional[int] = None) -> None:
        """Simulate a full innings ball by ball
        
        Args:
            delay_between_balls: Time delay between balls in seconds
            target: Target score for chasing team (None for first innings)
        """
        # Check if we have valid teams and players
        if not self.batting_team or not self.bowling_team:
            if self.send_message_func:
                self.send_message_func({"event": "error", "message": "Invalid teams for innings"})
            return
            
        # Make sure we have enough players
        if len(self.batting_team.players) < 2 or len(self.bowling_team.players) < 1:
            if self.send_message_func:
                self.send_message_func({"event": "error", "message": "Not enough players for the match"})
            return
        
        # Initialize current batsmen and bowler
        if not self.current_batsmen or len(self.current_batsmen) < 2:
            self.current_batsmen = [self.batting_team.players[0], self.batting_team.players[1]]
            
        if not self.current_bowler:
            # Choose a bowler (prefer players with bowling_type)
            bowlers = [p for p in self.bowling_team.players if p.role in ["Bowler", "All-rounder"]]
            if not bowlers:
                bowlers = self.bowling_team.players  # Use any player if no bowlers
                
            self.current_bowler = bowlers[0]
        
        # Scorecard update at start of innings
        if self.update_scorecard_func:
            self.update_scorecard_func(self._get_scorecard())
        
        # Simulate balls until innings is complete
        all_out = False
        target_reached = False
        
        for over in range(self.total_overs):
            # Update overs count
            self.batting_team.overs = over
            
            # Choose a bowler for this over (different from previous)
            bowlers = [p for p in self.bowling_team.players 
                      if p.role in ["Bowler", "All-rounder"] and p.id != self.current_bowler.id]
            if not bowlers:
                bowlers = [p for p in self.bowling_team.players if p.id != self.current_bowler.id]
                
            if bowlers:
                self.current_bowler = random.choice(bowlers)
            
            # Track runs at start of over for maiden detection
            self.over_start_runs = self.current_bowler.runs_conceded
                
            # Announce new over with improved formatting
            if self.send_message_func:
                # Store the current bowler's name at the start of the over for consistency
                current_over_bowler_name = self.current_bowler.name
                
                self.send_message_func({
                    "event": "over_start",
                    "over": over + 1,
                    "bowler": current_over_bowler_name,
                    "commentary": f"🏏 OVER {over + 1} BEGINS 🏏\n\n{current_over_bowler_name} will bowl this over."
                })
            
            # Simulate 6 balls in the over
            for ball in range(6):
                # Update balls count
                self.batting_team.balls = over * 6 + ball
                
                # Simulate the ball
                ball_result = self.simulate_ball()
                
                # Process ball result
                if ball_result["event"] == "error":
                    if self.send_message_func:
                        self.send_message_func(ball_result)
                    continue
                
                # Note: batsman's balls_faced is updated in the simulate_ball method
                # No need to update it here to avoid double counting
                
                # Always update partnership balls count
                self.partnership_balls += 1
                
                # For dot balls, update bowler stats
                if ball_result["event"] == "dot":
                    self.current_bowler.balls_bowled += 1
                    
                # Send ball result as message
                if self.send_message_func:
                    # Add score information to message
                    ball_result["score"] = f"{self.batting_team.score}/{self.batting_team.wickets}"
                    ball_result["overs"] = f"{over}.{ball}"
                    
                    # If target exists, add remaining runs and balls
                    if target:
                        ball_result["target"] = target
                        ball_result["needed"] = target - self.batting_team.score
                        ball_result["balls_left"] = (self.total_overs * 6) - (over * 6 + ball + 1)
                        
                    self.send_message_func(ball_result)
                
                # Update batsmen if it's a run event
                if ball_result["event"] in ["runs"]:
                    # If odd runs, swap batsmen
                    if ball_result["runs"] % 2 == 1:
                        self.current_batsmen[0], self.current_batsmen[1] = self.current_batsmen[1], self.current_batsmen[0]
                        
                    # Update team score
                    self.batting_team.score += ball_result["runs"]
                    
                    # Update partnership stats
                    self.current_partnership += ball_result["runs"]
                    
                    # Update bowler stats
                    self.current_bowler.runs_conceded += ball_result["runs"]
                    self.current_bowler.balls_bowled += 1
                
                # Update score for boundaries
                elif ball_result["event"] in ["boundary_4", "boundary_6"]:
                    self.batting_team.score += ball_result["runs"]
                    
                    # Update partnership stats
                    self.current_partnership += ball_result["runs"]
                    
                    # Update bowler stats
                    self.current_bowler.runs_conceded += ball_result["runs"]
                    self.current_bowler.balls_bowled += 1
                
                # Handle wicket
                elif ball_result["event"] == "wicket":
                    # Update wickets count
                    self.batting_team.wickets += 1
                    
                    # Update bowler stats
                    self.current_bowler.wickets += 1
                    self.current_bowler.balls_bowled += 1
                    
                    # Record fall of wickets
                    self.fall_of_wickets.append({
                        "score": self.batting_team.score,
                        "wicket": self.batting_team.wickets,
                        "overs": f"{over}.{ball}",
                        "player_out": ball_result["batsman_out"],
                        "bowler": self.current_bowler.name,
                        "dismissal_type": ball_result["dismissal_type"],
                        "partnership": self.current_partnership,
                        "partnership_balls": self.partnership_balls
                    })
                    
                    # Check if all out
                    if self.batting_team.wickets >= 10:
                        all_out = True
                        if self.send_message_func:
                            self.send_message_func({
                                "event": "all_out",
                                "team": self.batting_team.name,
                                "score": self.batting_team.score,
                                "overs": f"{over}.{ball}",
                                "commentary": f"{self.batting_team.name} is all out for {self.batting_team.score} " +
                                             f"in {over}.{ball} overs!"
                            })
                        break
                        
                    # Bring in next batsman
                    batting_order = self.batting_team.get_batting_order()
                    # Find batsmen who haven't batted yet by filtering out current and out batsmen
                    available_batsmen = [p for p in batting_order 
                                        if not p.is_out and p not in self.current_batsmen]
                    
                    if available_batsmen:
                        # Get next batsman based on batting order
                        new_batsman = available_batsmen[0]
                        
                        # First get the out batsman
                        out_batsman = next(b for b in self.current_batsmen if b.name == ball_result["batsman_out"])
                        # Ensure they are marked as out
                        out_batsman.is_out = True
                        # Get their index
                        out_batsman_idx = self.current_batsmen.index(out_batsman)
                        # Replace out batsman with new batsman
                        self.current_batsmen[out_batsman_idx] = new_batsman
                        
                        # Announce next batsman
                        if self.send_message_func:
                            self.send_message_func({
                                "event": "new_batsman",
                                "batsman": new_batsman.name,
                                "position": batting_order.index(new_batsman) + 1,
                                "commentary": f"🏏 {new_batsman.name} comes in to bat at position #{batting_order.index(new_batsman) + 1}"
                            })
                    else:
                        # No more batsmen
                        all_out = True
                        if self.send_message_func:
                            self.send_message_func({
                                "event": "all_out",
                                "team": self.batting_team.name,
                                "score": self.batting_team.score,
                                "overs": f"{over}.{ball}",
                                "commentary": f"{self.batting_team.name} is all out for {self.batting_team.score} " +
                                             f"in {over}.{ball} overs!"
                            })
                        break
                    
                    # Reset partnership stats for next pair
                    self.current_partnership = 0
                    self.partnership_balls = 0
                
                # Check if target reached (for second innings)
                if target and self.batting_team.score >= target:
                    target_reached = True
                    if self.send_message_func:
                        self.send_message_func({
                            "event": "target_reached",
                            "team": self.batting_team.name,
                            "score": self.batting_team.score,
                            "wickets": self.batting_team.wickets,
                            "overs": f"{over}.{ball + 1}",
                            "commentary": f"{self.batting_team.name} has reached the target of {target} runs " +
                                         f"with {10 - self.batting_team.wickets} wickets and " +
                                         f"{(self.total_overs * 6) - (over * 6 + ball + 1)} balls remaining!"
                        })
                    break
                    
                # Delay between balls (if live commentary)
                if delay_between_balls > 0:
                    time.sleep(delay_between_balls)
                    
            # Update over stats for the bowler
            self.current_bowler.overs_bowled += 1
            
            # Check for maiden over (no runs conceded in the over)
            # We need to track runs at start of over and compare with current runs
            over_runs = self.current_bowler.runs_conceded - self.over_start_runs
            if over_runs == 0:  # Means no runs conceded in this over
                self.current_bowler.maidens += 1
            
            # Update scorecard after the over
            if self.update_scorecard_func:
                # To prevent Telegram FloodWait errors, reduce scorecard frequency
                # Send detailed scorecard every 3 overs (for overs divisible by 4)
                if (over + 1) % 3 == 0:  # over + 1 because we're 0-indexed
                    self.update_scorecard_func(self._get_scorecard(detailed=True))
                # Send normal scorecard every 2 overs for overs not divisible by 4
                elif (over + 1) % 2 == 0:
                    self.update_scorecard_func(self._get_scorecard(detailed=False))
                # Don't send scorecard for odd numbered overs to reduce message frequency
                
            # Check if innings is over
            if all_out or target_reached:
                break
                
            # Swap batsmen at end of over
            self.current_batsmen[0], self.current_batsmen[1] = self.current_batsmen[1], self.current_batsmen[0]
            
        # Innings complete
        return
        
    def _get_scorecard(self, detailed=False) -> Dict:
        """Get the current scorecard as a dictionary
        
        Args:
            detailed: If True, returns a detailed scorecard with more information
        """
        # Check if teams exist
        if not self.batting_team or not self.bowling_team:
            return {
                "batting_team": "Unknown",
                "bowling_team": "Unknown",
                "score": 0,
                "wickets": 0,
                "overs": "0.0",
                "required_run_rate": 0,
                "current_run_rate": 0,
                "target": None,
                "batsmen": [],
                "bowlers": [],
                "current_batsmen": [],
                "current_bowler": {},
                "detailed": detailed
            }
            
        # Get detailed batting stats for all players
        batting_stats = [
            {
                "name": p.name,
                "runs": p.runs,
                "balls": p.balls_faced,  # This is properly tracked when a ball is faced
                "fours": getattr(p, "fours", 0),
                "sixes": getattr(p, "sixes", 0),
                "strike_rate": p.strike_rate,  # Use pre-calculated strike rate
                "is_out": p.is_out,
                "out_method": p.out_method,
                "bowler_who_dismissed": p.bowler_who_dismissed,
                "fielder_who_dismissed": getattr(p, "fielder_who_dismissed", None),
                "is_batting": p in self.current_batsmen and not p.is_out
            } for p in self.batting_team.players if p.balls_faced > 0 or (p in self.current_batsmen and not p.is_out)
        ]
        
        # Get detailed bowling stats for all players
        bowling_stats = [
            {
                "name": p.name,
                "overs": p.overs_bowled,
                "maidens": p.maidens,
                "runs": p.runs_conceded,
                "wickets": p.wickets,
                "economy": round((p.runs_conceded / max(1, p.balls_bowled) * 6), 2),
                "is_bowling": p == self.current_bowler
            } for p in self.bowling_team.players if p.balls_bowled > 0 or p == self.current_bowler
        ]
        
        return {
            "batting_team": self.batting_team.name,
            "bowling_team": self.bowling_team.name,
            "score": self.batting_team.score,
            "wickets": self.batting_team.wickets,
            "overs": f"{self.batting_team.overs}.{self.batting_team.balls % 6}",
            "required_run_rate": round(((self.target_score - self.batting_team.score) / 
                              max(1, ((self.total_overs * 6) - (self.batting_team.overs * 6 + self.batting_team.balls % 6)) / 6)), 2) 
                              if hasattr(self, 'target_score') and self.target_score else 0,
            "current_run_rate": round((self.batting_team.score / 
                                max(1, (self.batting_team.overs * 6 + self.batting_team.balls % 6) / 6)), 2),
            "target": self.target_score if hasattr(self, 'target_score') else None,
            "batsmen": batting_stats,
            "bowlers": bowling_stats,
            "current_batsmen": [
                {
                    "name": b.name,
                    "runs": b.runs,
                    "balls": b.balls_faced,  # Make sure this is updating correctly
                    "fours": getattr(b, "fours", 0),
                    "sixes": getattr(b, "sixes", 0),
                    "strike_rate": b.strike_rate  # Use pre-calculated strike rate
                } for b in self.current_batsmen if b and not b.is_out
            ],
            "current_bowler": {
                "name": self.current_bowler.name if self.current_bowler else "None",
                "overs": self.current_bowler.overs_bowled if self.current_bowler else 0,
                "maidens": self.current_bowler.maidens if self.current_bowler else 0,
                "wickets": self.current_bowler.wickets if self.current_bowler else 0,
                "runs": self.current_bowler.runs_conceded if self.current_bowler else 0,
                "economy": round((self.current_bowler.runs_conceded / max(1, self.current_bowler.balls_bowled) * 6), 2) if self.current_bowler else 0
            } if self.current_bowler else {},
            "current_partnership": {
                "runs": self.current_partnership,
                "balls": self.partnership_balls,
                "run_rate": round((self.current_partnership / max(1, self.partnership_balls) * 6), 2)
            },
            "fall_of_wickets": self.fall_of_wickets,
            "detailed": detailed
        }

# Standalone function for backward compatibility
def simulate_match(chat_id: int, team1: Team, team2: Team, total_overs: int = 5, 
                 send_message: Optional[Callable[[Dict], None]] = None, 
                 update_scorecard: Optional[Callable[[Dict], None]] = None, 
                 match_end: Optional[Callable[[Dict], None]] = None) -> Dict:
    """Simulates a cricket match between two teams."""
    match = CricketMatch(
        chat_id=chat_id,
        team1=team1,
        team2=team2,
        total_overs=total_overs,
        send_message_func=send_message,
        update_scorecard_func=update_scorecard,
        match_end_func=match_end
    )
    
    # Actually simulate the match, don't just return results
    result = match.simulate_match(delay_between_balls=0, return_results=False)
    if result is None:
        # Fallback in case the match simulation fails
        return {
            "result_type": "error",
            "error": "Match simulation failed",
            "team1": team1.name,
            "team2": team2.name
        }
    return result
