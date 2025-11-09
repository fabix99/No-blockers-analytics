"""
Session State Management for Streamlit Dashboard.
Centralizes session state access for better maintainability and testing.
"""
from typing import Optional
import streamlit as st
from match_analyzer import MatchAnalyzer
from event_tracker_loader import EventTrackerLoader


class SessionStateManager:
    """Centralized session state management."""
    
    # Session state keys
    KEY_ANALYZER = 'analyzer'
    KEY_LOADER = 'loader'
    KEY_MATCH_LOADED = 'match_loaded'
    KEY_OPPONENT_NAME = 'opponent_name'
    KEY_MATCH_FILENAME = 'match_filename'
    KEY_SHOW_HELP_GUIDE = 'show_help_guide'
    
    @staticmethod
    def get_analyzer() -> Optional[MatchAnalyzer]:
        """Get MatchAnalyzer from session state.
        
        Returns:
            MatchAnalyzer instance or None if not set
        """
        return st.session_state.get(SessionStateManager.KEY_ANALYZER)
    
    @staticmethod
    def set_analyzer(analyzer: MatchAnalyzer) -> None:
        """Set MatchAnalyzer in session state.
        
        Args:
            analyzer: MatchAnalyzer instance to store
        """
        st.session_state[SessionStateManager.KEY_ANALYZER] = analyzer
    
    @staticmethod
    def get_loader() -> Optional[EventTrackerLoader]:
        """Get EventTrackerLoader from session state.
        
        Returns:
            EventTrackerLoader instance or None if not set
        """
        return st.session_state.get(SessionStateManager.KEY_LOADER)
    
    @staticmethod
    def set_loader(loader: EventTrackerLoader) -> None:
        """Set EventTrackerLoader in session state.
        
        Args:
            loader: EventTrackerLoader instance to store
        """
        st.session_state[SessionStateManager.KEY_LOADER] = loader
    
    @staticmethod
    def is_match_loaded() -> bool:
        """Check if match data is loaded.
        
        Returns:
            True if match data is loaded, False otherwise
        """
        return st.session_state.get(SessionStateManager.KEY_MATCH_LOADED, False)
    
    @staticmethod
    def set_match_loaded(value: bool = True) -> None:
        """Set match loaded status.
        
        Args:
            value: True if match is loaded, False otherwise
        """
        st.session_state[SessionStateManager.KEY_MATCH_LOADED] = value
    
    @staticmethod
    def get_opponent_name() -> str:
        """Get opponent name from session state.
        
        Returns:
            Opponent name string, empty string if not set
        """
        return st.session_state.get(SessionStateManager.KEY_OPPONENT_NAME, '')
    
    @staticmethod
    def set_opponent_name(name: str) -> None:
        """Set opponent name in session state.
        
        Args:
            name: Opponent name string
        """
        st.session_state[SessionStateManager.KEY_OPPONENT_NAME] = name
    
    @staticmethod
    def get_match_filename() -> Optional[str]:
        """Get match filename from session state.
        
        Returns:
            Match filename string or None if not set
        """
        return st.session_state.get(SessionStateManager.KEY_MATCH_FILENAME)
    
    @staticmethod
    def set_match_filename(filename: str) -> None:
        """Set match filename in session state.
        
        Args:
            filename: Match filename string
        """
        st.session_state[SessionStateManager.KEY_MATCH_FILENAME] = filename
    
    @staticmethod
    def should_show_help_guide() -> bool:
        """Check if help guide should be shown.
        
        Returns:
            True if help guide should be shown, False otherwise
        """
        return st.session_state.get(SessionStateManager.KEY_SHOW_HELP_GUIDE, False)
    
    @staticmethod
    def set_show_help_guide(value: bool) -> None:
        """Set help guide visibility.
        
        Args:
            value: True to show help guide, False to hide
        """
        st.session_state[SessionStateManager.KEY_SHOW_HELP_GUIDE] = value
    
    @staticmethod
    def clear_match_data() -> None:
        """Clear all match-related session state."""
        keys_to_keep = {
            SessionStateManager.KEY_SHOW_HELP_GUIDE,
            'show_info_attack',
            'show_info_service',
            'show_info_block',
            'show_info_sideout'
        }
        
        keys_to_remove = [
            k for k in st.session_state.keys() 
            if k not in keys_to_keep
        ]
        
        for key in keys_to_remove:
            try:
                del st.session_state[key]
            except KeyError:
                pass

