"""
Service layer for business logic and data processing.
Separates business logic from UI concerns.
"""
from typing import Optional, Dict, Any
import streamlit as st
from match_analyzer import MatchAnalyzer
from event_tracker_loader import EventTrackerLoader
import performance_tracker as pt
from config import KPI_TARGETS


class AnalyticsService:
    """Service for analytics and metrics calculations."""
    
    def __init__(self, analyzer: MatchAnalyzer, loader: Optional[EventTrackerLoader] = None):
        """Initialize AnalyticsService.
        
        Args:
            analyzer: MatchAnalyzer instance with loaded match data
            loader: Optional EventTrackerLoader for additional data
        """
        self.analyzer = analyzer
        self.loader = loader
        self._team_metrics_cache: Optional[Dict[str, Any]] = None
        self._kpis_cache: Optional[Dict[str, Any]] = None
    
    def get_team_metrics(self) -> Dict[str, Any]:
        """Get team metrics with instance-level caching.
        
        Returns:
            Dictionary of team performance metrics
        """
        if self._team_metrics_cache is None:
            self._team_metrics_cache = self.analyzer.calculate_team_metrics()
        return self._team_metrics_cache
    
    def get_kpis(self) -> Optional[Dict[str, Any]]:
        """Get KPIs from loader if available.
        
        Returns:
            Dictionary of KPIs or None if not available
        """
        if self._kpis_cache is not None:
            return self._kpis_cache
        
        if self.loader is not None:
            has_team_data = (
                (hasattr(self.loader, 'team_data') and self.loader.team_data) or
                (hasattr(self.loader, 'team_data_by_set') and self.loader.team_data_by_set)
            )
            
            if has_team_data and hasattr(pt, 'compute_team_kpis_from_loader'):
                try:
                    self._kpis_cache = pt.compute_team_kpis_from_loader(self.loader)
                    return self._kpis_cache
                except Exception as e:
                    import logging
                    logging.warning(f"Could not compute KPIs from loader: {e}")
        
        return None
    
    def get_targets(self) -> Dict[str, Dict[str, float]]:
        """Get KPI targets with labels.
        
        Returns:
            Dictionary of KPI targets with labels
        """
        targets = KPI_TARGETS.copy()
        for key in targets:
            targets[key]['label'] = f"Target: {targets[key]['optimal']:.0%}+"
        return targets
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._team_metrics_cache = None
        self._kpis_cache = None

