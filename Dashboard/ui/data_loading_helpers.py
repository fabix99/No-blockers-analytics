"""
Helper functions for loading match data.
Extracted from load_match_data() for better organization.
"""
from typing import Tuple, Optional
import streamlit as st
import pandas as pd
import os
import tempfile
import uuid
from datetime import datetime
import logging

from services.session_manager import SessionStateManager
from utils import validate_uploaded_file, save_uploaded_file_securely, cleanup_temp_file
from match_analyzer import MatchAnalyzer
from event_tracker_loader import EventTrackerLoader

logger = logging.getLogger(__name__)


def _extract_opponent_name(filename: str) -> str:
    """Extract opponent name from filename.
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        Extracted opponent name or cleaned filename
    """
    opponent_name = None
    if ' vs ' in filename.lower() or ' vs. ' in filename.lower():
        parts = filename.lower().split(' vs ')
        if len(parts) > 1:
            opponent_name = parts[1].replace('.xlsx', '').replace('.xls', '').strip().title()
    elif filename.startswith('vs '):
        opponent_name = filename.replace('vs ', '').replace('.xlsx', '').replace('.xls', '').strip().title()
    else:
        # Try to extract from filename (remove extension and common prefixes)
        opponent_name = filename.replace('.xlsx', '').replace('.xls', '').replace('Match_', '').replace('match_', '').strip()
    
    return opponent_name


def _create_progress_tracker() -> Tuple[st.progress, st.empty]:
    """Create progress bar and status text for loading.
    
    Returns:
        Tuple of (progress_bar, status_text)
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    return progress_bar, status_text


def _display_validation_errors(errors: list, error_type: str = "Validation") -> None:
    """Display validation errors in a user-friendly format.
    
    Args:
        errors: List of error messages
        error_type: Type of errors being displayed
    """
    st.error(f"❌ {error_type} failed. Please review the errors below:")
    
    # Group errors by type
    error_groups = {}
    for error in errors:
        err_type = error.split(':')[0] if ':' in error else 'General'
        if err_type not in error_groups:
            error_groups[err_type] = []
        error_groups[err_type].append(error)
    
    # Display grouped errors
    with st.expander("📋 View Validation Errors", expanded=True):
        for err_type, error_list in error_groups.items():
            st.markdown(f"**{err_type}** ({len(error_list)} error(s))")
            for error in error_list[:5]:  # Show first 5 of each type
                st.error(f"  • {error}")
            if len(error_list) > 5:
                st.info(f"  ... and {len(error_list) - 5} more {err_type.lower()} errors")
    
    # Download error report
    error_report = "\n".join([f"{i+1}. {e}" for i, e in enumerate(errors)])
    st.download_button(
        label="📥 Download Error Report",
        data=error_report,
        file_name=f"validation_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        help="Download a detailed error report for fixing issues"
    )
    
    # Suggestions for fixing
    st.info("💡 **Tips for fixing errors:**\n"
           "- Ensure all required columns are present\n"
           "- Check that all values match the expected format\n"
           "- Verify that 'Point Won' values are 'yes' or 'no'\n"
           "- Check that all action types are valid\n"
           "- Ensure outcome values match the action type")


def _load_event_tracker_format(temp_file_path: str, progress_bar: st.progress, status_text: st.empty) -> Tuple[Optional[MatchAnalyzer], Optional[EventTrackerLoader], Optional[str]]:
    """Load match data from event tracker format.
    
    Args:
        temp_file_path: Path to temporary Excel file
        progress_bar: Streamlit progress bar
        status_text: Streamlit status text element
        
    Returns:
        Tuple of (analyzer, loader, temp_converted_path) or (None, None, None) on failure
    """
    try:
        status_text.text("📊 Loading event tracker data...")
        progress_bar.progress(20)
        
        status_text.text("📥 Processing individual events...")
        progress_bar.progress(40)
        
        loader = EventTrackerLoader(temp_file_path)
        
        status_text.text("✅ Validating data...")
        progress_bar.progress(60)
        
        # Check for validation errors
        validation_errors = loader.get_validation_errors()
        validation_warnings = loader.get_validation_warnings()
        
        if validation_errors:
            progress_bar.empty()
            status_text.empty()
            _display_validation_errors(validation_errors, "Data validation")
            return None, None, None
        
        if validation_warnings:
            for warning in validation_warnings:
                st.warning(f"⚠️ {warning}")
        
        status_text.text("🔄 Processing team events...")
        progress_bar.progress(70)
        
        df = loader.get_match_dataframe()
        
        status_text.text("📈 Creating match analyzer...")
        progress_bar.progress(80)
        
        # Create a temporary Excel file for MatchAnalyzer compatibility
        temp_converted_path = os.path.join(tempfile.gettempdir(), f"match_converted_{uuid.uuid4().hex}.xlsx")
        with pd.ExcelWriter(temp_converted_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Raw_Data', index=False)
        
        status_text.text("📊 Calculating metrics...")
        progress_bar.progress(90)
        
        analyzer = MatchAnalyzer(temp_converted_path)
        
        if analyzer.match_data is not None and len(analyzer.match_data) > 0:
            status_text.text("✅ Finalizing...")
            progress_bar.progress(95)
            
            # Additional validation - pass validate_match_data as parameter to avoid circular import
            # Note: validate_match_data is passed from the calling function
            # For now, we'll skip this validation in the helper to avoid circular imports
            # The validation is done in load_match_data after getting the analyzer
            pass  # Validation moved to load_match_data to avoid circular import
            
            progress_bar.progress(100)
            status_text.text("✅ Complete!")
            
            return analyzer, loader, temp_converted_path
        else:
            raise Exception("No data found in file after loading")
            
    except Exception as e:
        logger.warning(f"Event tracker loader failed: {e}")
        raise

