"""
Centralized KPI Calculator Service.

Consolidates all KPI calculation logic to avoid duplication across modules.
ALL formulas must be defined here - no calculations should exist in UI modules.
"""
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import logging
from utils.helpers import filter_good_receptions, filter_good_digs, calculate_total_points_from_loader

logger = logging.getLogger(__name__)


class KPICalculator:
    """Centralized KPI calculation service."""
    
    def __init__(self, analyzer=None, loader=None):
        """Initialize with optional analyzer and loader.
        
        Args:
            analyzer: MatchAnalyzer instance
            loader: EventTrackerLoader instance
        """
        self.analyzer = analyzer
        self.loader = loader
        self._cache: Dict[str, Any] = {}
    
    def clear_cache(self) -> None:
        """Clear the calculation cache."""
        self._cache = {}
    
    # ========================================
    # TEAM KPI CALCULATIONS
    # ========================================
    
    def calculate_serve_in_rate(self) -> float:
        """Calculate serve in-rate: (Aces + Good) / Total Serves."""
        cache_key = 'serve_in_rate'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try loader first (more accurate)
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            try:
                totals = self._get_totals_from_loader()
                aces = totals.get('service_aces', 0)
                good = totals.get('service_good', 0)
                total = totals.get('serve_attempts', 0)
                
                if total > 0:
                    result = (aces + good) / total
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Could not calculate serve_in_rate from loader: {e}")
        
        # Fallback to analyzer
        if self.analyzer and self.analyzer.match_data is not None:
            df = self.analyzer.match_data
            serves = df[df['action'] == 'serve']
            in_play = len(serves[serves['outcome'].isin(['ace', 'good'])])
            total = len(serves)
            result = (in_play / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_attack_kill_pct(self) -> float:
        """Calculate attack kill percentage: Kills / Total Attacks."""
        cache_key = 'attack_kill_pct'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try loader first
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            try:
                totals = self._get_totals_from_loader()
                kills = totals.get('attack_kills', 0)
                total = totals.get('attack_attempts', 0)
                
                if total > 0:
                    result = kills / total
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Could not calculate attack_kill_pct from loader: {e}")
        
        # Fallback to analyzer
        if self.analyzer and self.analyzer.match_data is not None:
            df = self.analyzer.match_data
            attacks = df[df['action'] == 'attack']
            kills = len(attacks[attacks['outcome'] == 'kill'])
            total = len(attacks)
            result = (kills / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_dig_rate(self) -> float:
        """Calculate dig rate: Good Digs / Total Digs."""
        cache_key = 'dig_rate'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Digs are aggregated, must use loader
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            try:
                total_good = 0.0
                total_digs = 0.0
                for set_num in self.loader.player_data_by_set.keys():
                    for player in self.loader.player_data_by_set[set_num].keys():
                        stats = self.loader.player_data_by_set[set_num][player].get('stats', {})
                        total_good += float(stats.get('Dig_Good', 0) or 0)
                        total_digs += float(stats.get('Dig_Total', 0) or 0)
                
                if total_digs > 0:
                    result = total_good / total_digs
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Could not calculate dig_rate from loader: {e}")
        
        # Fallback to analyzer (usually returns 0 as digs aren't action rows)
        if self.analyzer and self.analyzer.match_data is not None:
            df = self.analyzer.match_data
            digs = df[df['action'] == 'dig']
            good = len(digs[digs['outcome'].isin(['good', 'perfect'])])
            total = len(digs)
            result = (good / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_reception_quality(self) -> float:
        """Calculate reception quality: Good Receptions / Total Receptions."""
        cache_key = 'reception_quality'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try loader first
        if self.loader and hasattr(self.loader, 'reception_data_by_rotation'):
            try:
                total_good = 0.0
                total_rec = 0.0
                for set_num in self.loader.reception_data_by_rotation.keys():
                    for rot_num in self.loader.reception_data_by_rotation[set_num].keys():
                        rot_data = self.loader.reception_data_by_rotation[set_num][rot_num]
                        total_good += float(rot_data.get('good', 0) or 0)
                        total_rec += float(rot_data.get('total', 0) or 0)
                
                if total_rec > 0:
                    result = total_good / total_rec
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Could not calculate reception_quality from loader: {e}")
        
        # Fallback to analyzer
        if self.analyzer and self.analyzer.match_data is not None:
            df = self.analyzer.match_data
            receives = df[df['action'] == 'receive']
            good = len(receives[receives['outcome'].isin(['good', 'perfect'])])
            total = len(receives)
            result = (good / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_block_kill_pct(self) -> float:
        """Calculate block kill percentage: Block Kills / Total Blocks."""
        cache_key = 'block_kill_pct'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try loader first
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            try:
                total_kills = 0.0
                total_blocks = 0.0
                for set_num in self.loader.player_data_by_set.keys():
                    for player in self.loader.player_data_by_set[set_num].keys():
                        stats = self.loader.player_data_by_set[set_num][player].get('stats', {})
                        total_kills += float(stats.get('Block_Kills', 0) or 0)
                        total_blocks += float(stats.get('Block_Total', 0) or 0)
                
                if total_blocks > 0:
                    result = total_kills / total_blocks
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Could not calculate block_kill_pct from loader: {e}")
        
        # Fallback to analyzer
        if self.analyzer and self.analyzer.match_data is not None:
            df = self.analyzer.match_data
            blocks = df[df['action'] == 'block']
            kills = len(blocks[blocks['outcome'] == 'kill'])
            total = len(blocks)
            result = (kills / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_block_pct(self) -> float:
        """Calculate block percentage: (Block kills + Block no kill) / total block attempts.
        
        Consistent with Team Overview _calculate_block_pct.
        """
        cache_key = 'block_pct'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Always count from analyzer first for accurate block_no_kill count
        if self.analyzer and self.analyzer.match_data is not None:
            blocks = self.analyzer.match_data[self.analyzer.match_data['action'] == 'block']
            kills = len(blocks[blocks['outcome'] == 'kill'])
            no_kill = len(blocks[blocks['outcome'] == 'block_no_kill'])
            total = len(blocks)
            
            if total > 0:
                result = (kills + no_kill) / total
                self._cache[cache_key] = result
                return result
        
        # Fallback: try to use loader totals if analyzer has no data
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            try:
                total_kills = 0.0
                total_attempts = 0.0
                total_touches = 0.0
                for set_num in self.loader.player_data_by_set.keys():
                    for player in self.loader.player_data_by_set[set_num].keys():
                        stats = self.loader.player_data_by_set[set_num][player].get('stats', {})
                        total_kills += float(stats.get('Block_Kills', 0) or 0)
                        total_attempts += float(stats.get('Block_Total', 0) or 0)
                        # Block touches includes block_no_kill
                        total_touches += float(stats.get('Block_Touches', 0) or 0)
                
                if total_attempts > 0:
                    # Use block_touches as approximation for block_no_kill
                    result = (total_kills + total_touches) / total_attempts
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Could not calculate block_pct from loader: {e}")
        
        return 0.0
    
    def calculate_attack_error_pct(self, kpis: Optional[Dict[str, Any]] = None) -> float:
        """Calculate attack error percentage: All attack errors / total attack attempts."""
        cache_key = 'attack_error_pct'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try kpis totals first
        if kpis and 'totals' in kpis:
            attack_errors = kpis['totals'].get('attack_errors', 0)
            attack_attempts = kpis['totals'].get('attack_attempts', 0)
            if attack_attempts > 0:
                result = attack_errors / attack_attempts
                self._cache[cache_key] = result
                return result
        
        # Fallback to analyzer - all error types: blocked, out, net
        if self.analyzer and self.analyzer.match_data is not None:
            attacks = self.analyzer.match_data[self.analyzer.match_data['action'] == 'attack']
            errors = len(attacks[attacks['outcome'].isin(['blocked', 'out', 'net'])])
            total = len(attacks)
            result = (errors / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_reception_error_pct(self, kpis: Optional[Dict[str, Any]] = None) -> float:
        """Calculate reception error percentage: Reception errors / total receptions."""
        cache_key = 'reception_error_pct'
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try kpis totals first
        if kpis and 'totals' in kpis:
            rec_errors = kpis['totals'].get('reception_errors', 0)
            rec_total = kpis['totals'].get('reception_total', 0)
            if rec_total > 0:
                result = rec_errors / rec_total
                self._cache[cache_key] = result
                return result
        
        # Fallback to analyzer
        if self.analyzer and self.analyzer.match_data is not None:
            receives = self.analyzer.match_data[self.analyzer.match_data['action'] == 'receive']
            errors = len(receives[receives['outcome'] == 'error'])
            total = len(receives)
            result = (errors / total) if total > 0 else 0.0
            self._cache[cache_key] = result
            return result
        
        return 0.0
    
    def calculate_points_in_lead_pct(self) -> float:
        """Calculate percentage of total points where the team was in the lead.
        
        IMPORTANT: This resets per set - scores are compared within each set only.
        """
        if self.loader is None or not hasattr(self.loader, 'team_events') or self.loader.team_events is None:
            return 0.0
        
        try:
            team_events = self.loader.team_events
            if 'Our_Score' not in team_events.columns or 'Opponent_Score' not in team_events.columns:
                return 0.0
            
            if 'Set' not in team_events.columns:
                return 0.0
            
            points_in_lead = 0
            total_points = 0
            sets = sorted(team_events['Set'].unique())
            
            for set_num in sets:
                set_data = team_events[team_events['Set'] == set_num].sort_values('Point')
                for _, row in set_data.iterrows():
                    try:
                        our_score = float(row.get('Our_Score', 0)) if pd.notna(row.get('Our_Score')) else 0
                        opp_score = float(row.get('Opponent_Score', 0)) if pd.notna(row.get('Opponent_Score')) else 0
                    except (ValueError, TypeError):
                        continue
                    total_points += 1
                    if our_score > opp_score:
                        points_in_lead += 1
            
            return (points_in_lead / total_points) if total_points > 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating points in lead: {e}", exc_info=True)
            return 0.0
    
    def calculate_points_in_lead_count(self) -> int:
        """Calculate count of points where the team was in the lead (resets per set)."""
        if self.loader is None or not hasattr(self.loader, 'team_events') or self.loader.team_events is None:
            return 0
        
        try:
            team_events = self.loader.team_events
            if 'Our_Score' not in team_events.columns or 'Opponent_Score' not in team_events.columns:
                return 0
            if 'Set' not in team_events.columns:
                return 0
            
            points_in_lead = 0
            sets = sorted(team_events['Set'].unique())
            
            for set_num in sets:
                set_data = team_events[team_events['Set'] == set_num].sort_values('Point')
                for _, row in set_data.iterrows():
                    try:
                        our_score = float(row.get('Our_Score', 0)) if pd.notna(row.get('Our_Score')) else 0
                        opp_score = float(row.get('Opponent_Score', 0)) if pd.notna(row.get('Opponent_Score')) else 0
                    except (ValueError, TypeError):
                        continue
                    if our_score > opp_score:
                        points_in_lead += 1
            
            return points_in_lead
        except Exception:
            return 0
    
    def calculate_total_points_count(self) -> int:
        """Calculate total number of points played."""
        if self.loader is None or not hasattr(self.loader, 'team_events') or self.loader.team_events is None:
            return 0
        try:
            return len(self.loader.team_events)
        except Exception:
            return 0
    
    def calculate_avg_actions(self) -> float:
        """Calculate average actions per point."""
        total_points = calculate_total_points_from_loader(self.loader)
        if total_points <= 0:
            return 0.0
        
        # Count total actions from aggregated data if available
        total_actions = 0.0
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            for set_num in self.loader.player_data_by_set.keys():
                for player in self.loader.player_data_by_set[set_num].keys():
                    stats = self.loader.player_data_by_set[set_num][player].get('stats', {})
                    total_actions += (
                        float(stats.get('Attack_Total', 0) or 0) +
                        float(stats.get('Service_Total', 0) or 0) +
                        float(stats.get('Block_Total', 0) or 0) +
                        float(stats.get('Sets_Total', 0) or 0) +
                        float(stats.get('Dig_Total', 0) or 0)
                    )
            # Add reception actions
            if hasattr(self.loader, 'reception_data_by_rotation'):
                for set_num in self.loader.reception_data_by_rotation.keys():
                    for rot_num in self.loader.reception_data_by_rotation[set_num].keys():
                        rot_data = self.loader.reception_data_by_rotation[set_num][rot_num]
                        total_actions += float(rot_data.get('total', 0) or 0)
        else:
            # Fallback: count from analyzer
            if self.analyzer and self.analyzer.match_data is not None:
                total_actions = len(self.analyzer.match_data)
        
        return (total_actions / total_points) if total_points > 0 else 0.0
    
    def calculate_all_team_kpis(self) -> Dict[str, float]:
        """Calculate all team KPIs at once.
        
        Returns:
            Dictionary with all team KPI values
        """
        return {
            'serve_in_rate': self.calculate_serve_in_rate(),
            'attack_kill_pct': self.calculate_attack_kill_pct(),
            'dig_rate': self.calculate_dig_rate(),
            'reception_quality': self.calculate_reception_quality(),
            'block_kill_pct': self.calculate_block_kill_pct(),
        }
    
    # ========================================
    # PLAYER KPI CALCULATIONS
    # ========================================
    
    def calculate_player_attack_kill_pct(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate attack kill percentage for a specific player.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Count from action rows first (consistent with Team Overview)
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            attacks = player_df[player_df['action'] == 'attack']
            kills_count = len(attacks[attacks['outcome'] == 'kill'])
            attempts_count = len(attacks)
            
            if attempts_count > 0:
                value = kills_count / attempts_count
                if return_totals:
                    return {'value': value, 'numerator': kills_count, 'denominator': attempts_count}
                return value
        
        # Fallback to loader aggregated data
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_attempts = 0
            total_kills = 0
            # Find matching player name (handle variations in spacing/casing)
            for set_num in self.loader.player_data_by_set.keys():
                # Try exact match first
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_attempts += int(stats.get('Attack_Total', 0) or 0)
                    total_kills += int(stats.get('Attack_Kills', 0) or 0)
                else:
                    # Try case-insensitive match
                    player_name_lower = player_name.strip().lower()
                    for loader_player_name in self.loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_lower:
                            stats = self.loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_attempts += int(stats.get('Attack_Total', 0) or 0)
                            total_kills += int(stats.get('Attack_Kills', 0) or 0)
                            break
            
            if total_attempts > 0:
                value = total_kills / total_attempts
                if return_totals:
                    return {'value': value, 'numerator': total_kills, 'denominator': total_attempts}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_reception_quality(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate reception quality for a specific player.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Try loader aggregated data first (more accurate)
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_rec_good = 0
            total_rec_total = 0
            for set_num in self.loader.player_data_by_set.keys():
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_rec_good += int(stats.get('Reception_Good', 0) or 0)
                    total_rec_total += int(stats.get('Reception_Total', 0) or 0)
            
            if total_rec_total > 0:
                value = total_rec_good / total_rec_total
                if return_totals:
                    return {'value': value, 'numerator': total_rec_good, 'denominator': total_rec_total}
                return value
        
        # Fallback to action rows
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            receives = player_df[player_df['action'] == 'receive']
            good_receives = filter_good_receptions(receives)
            good_count = len(good_receives)
            total_count = len(receives)
            
            if total_count > 0:
                value = good_count / total_count
                if return_totals:
                    return {'value': value, 'numerator': good_count, 'denominator': total_count}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_block_kill_pct(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate block kill percentage for a specific player.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Count from action rows first
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            blocks = player_df[player_df['action'] == 'block']
            kills_count = len(blocks[blocks['outcome'] == 'kill'])
            attempts_count = len(blocks)
            
            if attempts_count > 0:
                value = kills_count / attempts_count
                if return_totals:
                    return {'value': value, 'numerator': kills_count, 'denominator': attempts_count}
                return value
        
        # Fallback to loader aggregated data
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_attempts = 0
            total_kills = 0
            for set_num in self.loader.player_data_by_set.keys():
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_attempts += int(stats.get('Block_Total', 0) or 0)
                    total_kills += int(stats.get('Block_Kills', 0) or 0)
            
            if total_attempts > 0:
                value = total_kills / total_attempts
                if return_totals:
                    return {'value': value, 'numerator': total_kills, 'denominator': total_attempts}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_setting_quality(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate setting quality for a specific player: Good sets / total sets.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Count from action rows first (more accurate)
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            sets = player_df[player_df['action'] == 'set']
            total_sets_count = len(sets)
            
            if total_sets_count > 0:
                # Good sets = exceptional + good (both count as good)
                good_sets_count = len(sets[sets['outcome'].isin(['exceptional', 'good'])])
                value = good_sets_count / total_sets_count
                if return_totals:
                    return {'value': value, 'numerator': good_sets_count, 'denominator': total_sets_count}
                return value
        
        # Fallback to loader aggregated data
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_sets = 0
            total_exceptional = 0
            total_good = 0
            for set_num in self.loader.player_data_by_set.keys():
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_sets += int(stats.get('Sets_Total', 0) or 0)
                    total_exceptional += int(stats.get('Sets_Exceptional', 0) or 0)
                    total_good += int(stats.get('Sets_Good', 0) or 0)
            
            if total_sets > 0:
                good_sets = total_exceptional + total_good
                value = good_sets / total_sets
                if return_totals:
                    return {'value': value, 'numerator': good_sets, 'denominator': total_sets}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_serve_in_rate(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate serve in-rate for a specific player.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Count from action rows first
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            serves = player_df[player_df['action'] == 'serve']
            aces_count = len(serves[serves['outcome'] == 'ace'])
            good_count = len(serves[serves['outcome'] == 'good'])
            in_play_count = aces_count + good_count
            attempts_count = len(serves)
            
            if attempts_count > 0:
                value = in_play_count / attempts_count
                if return_totals:
                    return {'value': value, 'numerator': in_play_count, 'denominator': attempts_count}
                return value
        
        # Fallback to loader aggregated data
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_attempts = 0
            total_aces = 0
            total_good = 0
            for set_num in self.loader.player_data_by_set.keys():
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_attempts += int(stats.get('Service_Total', 0) or 0)
                    total_aces += int(stats.get('Service_Aces', 0) or 0)
                    total_good += int(stats.get('Service_Good', 0) or 0)
            
            if total_attempts > 0:
                value = (total_aces + total_good) / total_attempts
                if return_totals:
                    return {'value': value, 'numerator': total_aces + total_good, 'denominator': total_attempts}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_block_pct(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate block percentage for a specific player: (Block kills + Block no kill) / total attempts.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Count from action rows first (consistent with Team Overview)
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            blocks = player_df[player_df['action'] == 'block']
            kills_count = len(blocks[blocks['outcome'] == 'kill'])
            no_kill_count = len(blocks[blocks['outcome'] == 'block_no_kill'])
            attempts_count = len(blocks)
            
            if attempts_count > 0:
                value = (kills_count + no_kill_count) / attempts_count
                if return_totals:
                    return {'value': value, 'numerator': kills_count + no_kill_count, 'denominator': attempts_count}
                return value
        
        # Fallback to loader aggregated data
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_attempts = 0
            total_kills = 0
            total_touches = 0
            player_name_lower = player_name.strip().lower()
            for set_num in self.loader.player_data_by_set.keys():
                # Try exact match first
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_attempts += int(stats.get('Block_Total', 0) or 0)
                    total_kills += int(stats.get('Block_Kills', 0) or 0)
                    total_touches += int(stats.get('Block_Touches', 0) or 0)
                else:
                    # Try case-insensitive match
                    for loader_player_name in self.loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_lower:
                            stats = self.loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_attempts += int(stats.get('Block_Total', 0) or 0)
                            total_kills += int(stats.get('Block_Kills', 0) or 0)
                            total_touches += int(stats.get('Block_Touches', 0) or 0)
                            break
            
            if total_attempts > 0:
                # Use block_touches as approximation for block_no_kill
                value = (total_kills + total_touches) / total_attempts
                if return_totals:
                    return {'value': value, 'numerator': total_kills + total_touches, 'denominator': total_attempts}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_dig_rate(self, player_name: str, return_totals: bool = False) -> Any:
        """Calculate dig rate for a specific player: Good digs / total digs.
        
        Args:
            player_name: Name of the player
            return_totals: If True, return dict with 'value', 'numerator', 'denominator'
            
        Returns:
            float if return_totals=False, dict if return_totals=True
        """
        # Try action rows first (more accurate for individual outcomes)
        player_df = self._get_player_df(player_name)
        if not player_df.empty:
            digs = player_df[player_df['action'] == 'dig']
            good_count = len(digs[digs['outcome'].isin(['good', 'perfect'])])
            attempts_count = len(digs)
            
            if attempts_count > 0:
                value = good_count / attempts_count
                if return_totals:
                    return {'value': value, 'numerator': good_count, 'denominator': attempts_count}
                return value
        
        # Fallback to loader aggregated data with case-insensitive matching
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            total_good = 0
            total_digs = 0
            player_name_normalized = player_name.strip().lower()
            for set_num in self.loader.player_data_by_set.keys():
                # Try exact match first
                if player_name in self.loader.player_data_by_set[set_num]:
                    stats = self.loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_good += int(stats.get('Dig_Good', 0) or 0)
                    total_digs += int(stats.get('Dig_Total', 0) or 0)
                else:
                    # Try case-insensitive match
                    for loader_player_name in self.loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_normalized:
                            stats = self.loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_good += int(stats.get('Dig_Good', 0) or 0)
                            total_digs += int(stats.get('Dig_Total', 0) or 0)
                            break
            
            if total_digs > 0:
                value = total_good / total_digs
                if return_totals:
                    return {'value': value, 'numerator': total_good, 'denominator': total_digs}
                return value
        
        if return_totals:
            return {'value': 0.0, 'numerator': 0, 'denominator': 0}
        return 0.0
    
    def calculate_player_kpis(self, player_name: str) -> Dict[str, float]:
        """Calculate all KPIs for a specific player.
        
        Args:
            player_name: Name of the player
            
        Returns:
            Dictionary with all player KPI values
        """
        return {
            'attack_kill_pct': self.calculate_player_attack_kill_pct(player_name),
            'reception_quality': self.calculate_player_reception_quality(player_name),
            'serve_in_rate': self.calculate_player_serve_in_rate(player_name),
        }
    
    # ========================================
    # HELPER CALCULATION METHODS (for raw totals)
    # These take raw counts and calculate percentages/formulas
    # Used for set-by-set, rotation-by-rotation breakdowns
    # ========================================
    
    @staticmethod
    def calculate_attack_kill_pct_from_totals(attack_kills: int, attack_attempts: int) -> float:
        """Calculate attack kill % from raw totals."""
        return (attack_kills / attack_attempts) if attack_attempts > 0 else 0.0
    
    @staticmethod
    def calculate_attack_error_rate_from_totals(attack_errors: int, attack_attempts: int) -> float:
        """Calculate attack error rate from raw totals."""
        return (attack_errors / attack_attempts) if attack_attempts > 0 else 0.0
    
    @staticmethod
    def calculate_serve_in_rate_from_totals(service_aces: int, service_good: int, service_attempts: int) -> float:
        """Calculate serve in-rate from raw totals."""
        return ((service_aces + service_good) / service_attempts) if service_attempts > 0 else 0.0
    
    @staticmethod
    def calculate_serve_error_rate_from_totals(service_errors: int, service_attempts: int) -> float:
        """Calculate serve error rate from raw totals."""
        return (service_errors / service_attempts) if service_attempts > 0 else 0.0
    
    @staticmethod
    def calculate_block_kill_pct_from_totals(block_kills: int, block_attempts: int) -> float:
        """Calculate block kill % from raw totals."""
        return (block_kills / block_attempts) if block_attempts > 0 else 0.0
    
    @staticmethod
    def calculate_reception_quality_from_totals(reception_good: int, reception_total: int) -> float:
        """Calculate reception quality from raw totals."""
        return (reception_good / reception_total) if reception_total > 0 else 0.0
    
    @staticmethod
    def calculate_dig_rate_from_totals(dig_good: int, dig_total: int) -> float:
        """Calculate dig rate from raw totals."""
        return (dig_good / dig_total) if dig_total > 0 else 0.0
    
    @staticmethod
    def calculate_break_point_rate_from_totals(serving_points_won: int, serving_rallies: int) -> float:
        """Calculate break point rate from raw totals."""
        return (serving_points_won / serving_rallies) if serving_rallies > 0 else 0.0
    
    @staticmethod
    def calculate_side_out_efficiency_from_totals(receiving_points_won: int, receiving_rallies: int) -> float:
        """Calculate side-out efficiency from raw totals."""
        return (receiving_points_won / receiving_rallies) if receiving_rallies > 0 else 0.0
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _get_player_df(self, player_name: str) -> pd.DataFrame:
        """Get player dataframe with case-insensitive, whitespace-tolerant matching.
        
        Args:
            player_name: Player name to match
            
        Returns:
            DataFrame filtered to player's rows
        """
        if self.analyzer is None or self.analyzer.match_data is None:
            return pd.DataFrame()
        
        df = self.analyzer.match_data
        if 'player' not in df.columns or df.empty:
            return pd.DataFrame()
        
        player_name_normalized = player_name.strip().lower()
        # Match case-insensitively and handle whitespace (fillna to handle None/NaN)
        player_col_normalized = df['player'].fillna('').astype(str).str.strip().str.lower()
        return df[player_col_normalized == player_name_normalized]
    
    def _get_totals_from_loader(self) -> Dict[str, float]:
        """Aggregate totals from loader player data.
        
        Returns:
            Dictionary with aggregated totals
        """
        if 'loader_totals' in self._cache:
            return self._cache['loader_totals']
        
        totals = {
            'service_aces': 0.0,
            'service_good': 0.0,
            'service_errors': 0.0,
            'serve_attempts': 0.0,
            'attack_kills': 0.0,
            'attack_attempts': 0.0,
            'block_kills': 0.0,
            'block_attempts': 0.0,
        }
        
        if self.loader and hasattr(self.loader, 'player_data_by_set'):
            for set_num in self.loader.player_data_by_set.keys():
                for player in self.loader.player_data_by_set[set_num].keys():
                    stats = self.loader.player_data_by_set[set_num][player].get('stats', {})
                    
                    totals['service_aces'] += float(stats.get('Service_Aces', 0) or 0)
                    totals['service_good'] += float(stats.get('Service_Good', 0) or 0)
                    totals['service_errors'] += float(stats.get('Service_Errors', 0) or 0)
                    totals['serve_attempts'] += float(stats.get('Service_Total', 0) or 0)
                    totals['attack_kills'] += float(stats.get('Attack_Kills', 0) or 0)
                    totals['attack_attempts'] += float(stats.get('Attack_Total', 0) or 0)
                    totals['block_kills'] += float(stats.get('Block_Kills', 0) or 0)
                    totals['block_attempts'] += float(stats.get('Block_Total', 0) or 0)
        
        self._cache['loader_totals'] = totals
        return totals


# Convenience function for quick calculations without creating an instance
def get_kpi_calculator(analyzer=None, loader=None) -> KPICalculator:
    """Factory function to create a KPICalculator instance.
    
    Args:
        analyzer: MatchAnalyzer instance
        loader: EventTrackerLoader instance
        
    Returns:
        Configured KPICalculator instance
    """
    return KPICalculator(analyzer=analyzer, loader=loader)

