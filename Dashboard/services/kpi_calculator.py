"""
Centralized KPI Calculator Service.

Consolidates all KPI calculation logic to avoid duplication across modules.
"""
from typing import Dict, Any, Optional
import pandas as pd
import logging

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
    
    def calculate_player_attack_kill_pct(self, player_name: str) -> float:
        """Calculate attack kill percentage for a specific player."""
        if self.analyzer is None or self.analyzer.match_data is None:
            return 0.0
        
        df = self.analyzer.match_data
        player_df = df[df['player'] == player_name]
        attacks = player_df[player_df['action'] == 'attack']
        kills = len(attacks[attacks['outcome'] == 'kill'])
        total = len(attacks)
        return (kills / total) if total > 0 else 0.0
    
    def calculate_player_reception_quality(self, player_name: str) -> float:
        """Calculate reception quality for a specific player."""
        if self.analyzer is None or self.analyzer.match_data is None:
            return 0.0
        
        df = self.analyzer.match_data
        player_df = df[df['player'] == player_name]
        receives = player_df[player_df['action'] == 'receive']
        good = len(receives[receives['outcome'].isin(['good', 'perfect'])])
        total = len(receives)
        return (good / total) if total > 0 else 0.0
    
    def calculate_player_serve_in_rate(self, player_name: str) -> float:
        """Calculate serve in-rate for a specific player."""
        if self.analyzer is None or self.analyzer.match_data is None:
            return 0.0
        
        df = self.analyzer.match_data
        player_df = df[df['player'] == player_name]
        serves = player_df[player_df['action'] == 'serve']
        in_play = len(serves[serves['outcome'].isin(['ace', 'good'])])
        total = len(serves)
        return (in_play / total) if total > 0 else 0.0
    
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
    # HELPER METHODS
    # ========================================
    
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

